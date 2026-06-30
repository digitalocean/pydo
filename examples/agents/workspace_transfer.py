"""Upload a file to a session's sandbox workspace and download it back.

Required env:
  DIGITALOCEAN_TOKEN
  PYDO_AGENTS_ENDPOINT   stage2: https://api.s2r1.internal.digitalocean.com
  SESSION_ID             an existing, READY session id

Optional env:
  LOCAL_FILE     file to upload (default: a small generated text file)
  GUEST_PATH     destination inside /workspace (default: uploads/example.txt)
  DOWNLOAD_TO    local path to write the round-tripped copy (default: a temp file)
"""

import hashlib
import os
import sys
import tempfile

from pydo import Client
from pydo.agents import WorkspaceTransferError


def _sample_file() -> str:
    fd, path = tempfile.mkstemp(prefix="pydo-ws-", suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("hello from pydo workspace transfer\n" * 4)
    return path


def main() -> int:
    session_id = os.environ["SESSION_ID"]
    local_file = os.environ.get("LOCAL_FILE") or _sample_file()
    guest_path = os.environ.get("GUEST_PATH", "uploads/example.txt")
    download_to = os.environ.get("DOWNLOAD_TO") or tempfile.mktemp(prefix="pydo-dl-")

    client = Client(
        token=os.environ["DIGITALOCEAN_TOKEN"],
        agents_endpoint=os.environ.get("PYDO_AGENTS_ENDPOINT"),
    )
    agent = client.agents.attach(session_id)

    with open(local_file, "rb") as fh:
        original = fh.read()
    sha256 = hashlib.sha256(original).hexdigest()
    print(
        f"[session {session_id}] uploading {len(original)} bytes "
        f"({local_file}) -> /workspace/{guest_path}",
        file=sys.stderr,
    )

    up = agent.upload_file(path=guest_path, data=local_file, content_sha256=sha256)
    print(f"[uploaded] {dict(up)}", file=sys.stderr)

    download = agent.download_file(path=guest_path)
    try:
        written = download.save(download_to)
    except WorkspaceTransferError as exc:
        print(f"[integrity check FAILED] {exc}", file=sys.stderr)
        return 1

    print(
        f"[downloaded] {written} bytes -> {download_to} "
        f"(is_archive={download.is_archive}, size_hint={download.size_hint})",
        file=sys.stderr,
    )

    with open(download_to, "rb") as fh:
        roundtripped = fh.read()
    ok = roundtripped == original
    print(f"[round-trip] bytes match: {ok}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
