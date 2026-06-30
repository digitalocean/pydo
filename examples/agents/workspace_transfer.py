"""Upload a file to a session's sandbox workspace and download it back.

Hosted-agents sessions expose a ``/workspace`` sandbox. These two custom REST
endpoints stream arbitrary bytes in and out of it:

  * ``client.agents.sessions.workspace_upload(...)``    POST .../workspace/upload
  * ``client.agents.sessions.workspace_download(...)``  GET  .../workspace/download

This script does a full round trip against an *existing* session:

  1. Upload a local file to ``GUEST_PATH`` inside the workspace. The optional
     ``X-Content-Sha256`` header is sent so the guest can verify the upload.
  2. Download it back. The download is chunked and the SHA-256 digest arrives as
     an HTTP *trailer* after the body, so the SDK reads the whole body first,
     then verifies it. Note: CPython's HTTP stack discards chunked trailers, so
     the X-Content-Sha256 trailer is usually unreadable from Python — the SDK
     falls back to the server's size hint (X-Workspace-Size-Bytes) to detect
     truncation and warns that the checksum could not be confirmed. A real
     mismatch (trailer or size) raises ``WorkspaceTransferError``; pass
     require_checksum=True for strict mode on a trailer-capable transport.
  3. Confirm the bytes survived the round trip.

The high-level handle also offers ``agent.upload_file(...)`` /
``agent.download_file(...)`` which bind the session id for you; the equivalent
low-level calls are shown in comments.

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
    """Create a small throwaway file to upload when LOCAL_FILE is unset."""
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

    # --- upload -----------------------------------------------------------
    # `data` accepts bytes, a filesystem path, or a readable binary stream.
    # Passing content_sha256 lets the guest verify what it received.
    up = agent.upload_file(path=guest_path, data=local_file, content_sha256=sha256)
    # low-level equivalent:
    #   client.agents.sessions.workspace_upload(
    #       session_id, path=guest_path, data=local_file, content_sha256=sha256)
    print(f"[uploaded] {dict(up)}", file=sys.stderr)

    # --- download ---------------------------------------------------------
    # The returned object streams the body; .save()/.read() consume it fully
    # and then verify integrity (trailer if readable, else the size hint). On a
    # detected corruption/truncation a partial file written by .save() is
    # removed and WorkspaceTransferError is raised, so you never keep a corrupt
    # download. (A "could not verify trailer" warning is expected on CPython.)
    download = agent.download_file(path=guest_path)
    # low-level equivalent:
    #   download = client.agents.sessions.workspace_download(
    #       session_id, path=guest_path)
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

    # --- verify the round trip -------------------------------------------
    with open(download_to, "rb") as fh:
        roundtripped = fh.read()
    ok = roundtripped == original
    print(f"[round-trip] bytes match: {ok}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
