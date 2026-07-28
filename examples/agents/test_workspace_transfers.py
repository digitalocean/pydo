"""Live E2E tests for staged workspace transfers.

Requires a READY session. Generates fixtures if missing, then round-trips
each file through upload → download → SHA-256 compare.

Required env:
  DIGITALOCEAN_TOKEN
  SESSION_ID
  PYDO_AGENTS_ENDPOINT   (stage2 / harness OHS base URL)

Optional env:
  FIXTURE_DIR     default: examples/agents/testdata
  SIZES           comma sizes for auto-generate (default: 1KiB,1MiB,40MiB)
  SKIP_GENERATE   if "1", do not auto-generate fixtures
  SKIP_ARCHIVE    if "1", skip the tar/is_archive case
  SKIP_LARGE      if "1", skip fixtures larger than 5 MiB
  POLL_INTERVAL   seconds (default: 1)
  GUEST_PREFIX    workspace path prefix (default: uploads/pydo-transfer-test)

Usage:
  export DIGITALOCEAN_TOKEN=...
  export SESSION_ID=...
  export PYDO_AGENTS_ENDPOINT=https://api.s2r1.internal.digitalocean.com
  python examples/agents/generate_transfer_fixtures.py
  python examples/agents/test_workspace_transfers.py
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from pydo import Client
from pydo.agents import WorkspaceTransferError

HERE = Path(__file__).resolve().parent
DEFAULT_FIXTURE_DIR = HERE / "testdata"


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _ensure_fixtures(fixture_dir: Path) -> None:
    if os.environ.get("SKIP_GENERATE") == "1":
        return
    needed = ["hello.txt", "sample.tar", "MANIFEST.tsv"]
    if all((fixture_dir / name).exists() for name in needed):
        return
    print(f"[fixtures] generating under {fixture_dir}", file=sys.stderr)
    cmd = [
        sys.executable,
        str(HERE / "generate_transfer_fixtures.py"),
        "--out",
        str(fixture_dir),
    ]
    sizes = os.environ.get("SIZES")
    if sizes:
        cmd.extend(["--sizes", sizes])
    subprocess.check_call(cmd)


def _iter_cases(fixture_dir: Path):
    skip_large = os.environ.get("SKIP_LARGE") == "1"
    skip_archive = os.environ.get("SKIP_ARCHIVE") == "1"
    limit = 5 * 1024 * 1024

    # Prefer MANIFEST.tsv when present.
    manifest = fixture_dir / "MANIFEST.tsv"
    if manifest.exists():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            name, size_s, digest = parts[0], parts[1], parts[2]
            is_archive = any(p == "is_archive=true" for p in parts[3:])
            path = fixture_dir / name
            if not path.exists():
                print(f"[skip] missing {path}", file=sys.stderr)
                continue
            size = int(size_s)
            if skip_large and size > limit:
                print(f"[skip] large {path.name} ({size} bytes)", file=sys.stderr)
                continue
            if is_archive and skip_archive:
                print(f"[skip] archive {path.name}", file=sys.stderr)
                continue
            yield path, digest, is_archive
        return

    # Fallback: every file in the directory.
    for path in sorted(fixture_dir.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.name == "MANIFEST.tsv":
            continue
        size = path.stat().st_size
        if skip_large and size > limit:
            continue
        is_archive = path.suffix == ".tar"
        if is_archive and skip_archive:
            continue
        yield path, _sha256_file(path), is_archive


def _round_trip(agent, local: Path, digest: str, *, guest_path: str, is_archive: bool, poll_interval: float) -> None:
    size = local.stat().st_size
    print(
        f"\n=== {local.name} ({size} bytes, archive={is_archive}) -> {guest_path} ===",
        file=sys.stderr,
    )
    t0 = time.monotonic()
    up = agent.upload_file(
        path=guest_path,
        data=str(local),
        is_archive=is_archive,
        content_sha256=digest,
        poll_interval=poll_interval,
    )
    print(
        f"[upload] status={getattr(up, 'status', None)} "
        f"bytes_written={getattr(up, 'bytes_written', None)} "
        f"transfer_id={getattr(up, 'transfer_id', None)} "
        f"elapsed={time.monotonic() - t0:.1f}s",
        file=sys.stderr,
    )

    # For archive uploads the guest path is an extract root; download as archive
    # of that path so we can still verify something came back.
    download_path = guest_path
    as_archive = is_archive
    t1 = time.monotonic()
    download = agent.download_file(
        path=download_path,
        as_archive=as_archive,
        poll_interval=poll_interval,
    )
    fd, tmp_name = tempfile.mkstemp(prefix="pydo-xfer-", suffix=".bin")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        written = download.save(str(tmp))
        print(
            f"[download] written={written} size_hint={download.size_hint} "
            f"expected_sha256={download.expected_sha256} "
            f"elapsed={time.monotonic() - t1:.1f}s",
            file=sys.stderr,
        )
        got = _sha256_file(tmp)
        if is_archive:
            # Extracted tree re-tarred by the server will not match the original
            # tar bytes; only check that we got a non-empty payload and (when
            # present) that the server digest matches what we downloaded.
            if written <= 0:
                raise AssertionError("archive download returned 0 bytes")
            if download.expected_sha256 and got != download.expected_sha256.lower():
                raise AssertionError(
                    f"downloaded archive sha mismatch: {got} != {download.expected_sha256}"
                )
            print("[ok] archive download non-empty + digest check", file=sys.stderr)
        else:
            if got != digest.lower():
                raise AssertionError(
                    f"round-trip sha mismatch: got {got} expected {digest}"
                )
            if written != size:
                raise AssertionError(f"size mismatch: got {written} expected {size}")
            print("[ok] bytes + sha256 match", file=sys.stderr)
    except WorkspaceTransferError:
        raise
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def _low_level_smoke(sessions, session_id: str, local: Path, digest: str, poll_interval: float) -> None:
    """Exercise the 5 transfer endpoints explicitly on a small file."""
    guest = "uploads/pydo-lowlevel-smoke.bin"
    size = local.stat().st_size
    print(f"\n=== low-level API smoke ({local.name}) ===", file=sys.stderr)

    created = sessions.create_transfer(
        session_id,
        direction="upload",
        path=guest,
        size_bytes=size,
        sha256=digest,
    )
    transfer_id = created.transfer_id
    part_size = int(created.part_size)
    print(
        f"[create] transfer_id={transfer_id} part_size={part_size} status={created.status}",
        file=sys.stderr,
    )

    offset = 0
    part_number = 1
    part_numbers = []
    chunks = []
    with local.open("rb") as fh:
        while offset < size:
            chunk = fh.read(min(part_size, size - offset))
            chunks.append(chunk)
            part_numbers.append(part_number)
            offset += len(chunk)
            part_number += 1

    batch = sessions.create_part_upload_urls(
        session_id, transfer_id, part_numbers=part_numbers
    )
    url_by_n = {
        int(entry.part_number): entry.upload_url for entry in batch.part_urls
    }
    from pydo.agents.custom_sessions import _http_put_bytes

    for n, chunk in zip(part_numbers, chunks):
        _http_put_bytes(url_by_n[n], chunk)
        print(f"[part {n}] uploaded {len(chunk)} bytes", file=sys.stderr)

    committed = sessions.commit_upload(session_id, transfer_id, sha256=digest)
    print(f"[commit] status={committed.status}", file=sys.stderr)
    done = sessions.wait_transfer(session_id, transfer_id, poll_interval=poll_interval)
    print(
        f"[wait] status={done.status} bytes_written={getattr(done, 'bytes_written', None)}",
        file=sys.stderr,
    )

    # Cancel on a finished transfer: idempotent when supported; stage2 may still
    # return 501 until sandboxsvc exposes cancel.
    try:
        cancelled = sessions.cancel_transfer(
            session_id, transfer_id, reason="smoke_done"
        )
        print(
            f"[cancel] aborted={cancelled.aborted} status={cancelled.status}",
            file=sys.stderr,
        )
    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        if "501" in message or "not yet exposed" in message.lower():
            print(f"[cancel] skipped (not supported yet): {message}", file=sys.stderr)
        else:
            raise
    print("[ok] low-level smoke", file=sys.stderr)


def main() -> int:
    session_id = os.environ["SESSION_ID"]
    fixture_dir = Path(os.environ.get("FIXTURE_DIR", DEFAULT_FIXTURE_DIR))
    poll_interval = float(os.environ.get("POLL_INTERVAL", "1"))
    guest_prefix = os.environ.get("GUEST_PREFIX", "uploads/pydo-transfer-test")

    _ensure_fixtures(fixture_dir)
    if not fixture_dir.exists():
        print(f"no fixtures at {fixture_dir}; run generate_transfer_fixtures.py", file=sys.stderr)
        return 2

    client = Client(
        token=os.environ["DIGITALOCEAN_TOKEN"],
        agents_endpoint=os.environ.get("PYDO_AGENTS_ENDPOINT"),
    )
    agent = client.agents.attach(session_id)
    print(f"[session] {session_id}", file=sys.stderr)
    print(f"[endpoint] {client.agents.base_url}", file=sys.stderr)
    print(f"[fixtures] {fixture_dir}", file=sys.stderr)

    failures = []
    cases = list(_iter_cases(fixture_dir))
    if not cases:
        print("no test cases found", file=sys.stderr)
        return 2

    # Low-level smoke on the smallest non-archive fixture.
    small = next((c for c in cases if not c[2]), None)
    if small is not None:
        try:
            _low_level_smoke(
                client.agents.sessions,
                session_id,
                small[0],
                small[1],
                poll_interval,
            )
        except Exception as exc:  # noqa: BLE001 — report and continue high-level cases
            print(f"[FAIL] low-level smoke: {exc}", file=sys.stderr)
            failures.append("low-level-smoke")

    for local, digest, is_archive in cases:
        guest = f"{guest_prefix}/{local.name}"
        if is_archive:
            guest = f"{guest_prefix}/extracted-{local.stem}"
        try:
            _round_trip(
                agent,
                local,
                digest,
                guest_path=guest,
                is_archive=is_archive,
                poll_interval=poll_interval,
            )
        except Exception as exc:  # noqa: BLE001 — collect failures across cases
            print(f"[FAIL] {local.name}: {exc}", file=sys.stderr)
            failures.append(local.name)

    print(file=sys.stderr)
    if failures:
        print(f"FAILED ({len(failures)}): {', '.join(failures)}", file=sys.stderr)
        return 1
    print(f"PASSED ({len(cases)} high-level cases)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
