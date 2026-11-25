# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Files in a sandbox: ``/v2/sandboxes/{id}/files``.

Hand-written; preserved across ``make generate``. Every call goes through the
generated ``client.sandboxes`` operations, so auth, User-Agent and the API
origin match the rest of pydo. Uploads send the SHA-256 of the body for the
sandbox to check, and downloads are checked against the SHA-256 in their
integrity footer.

.. code-block:: python

    sandbox.files.write("/workspace/hello.txt", "Hello")
    print(sandbox.files.read_text("/workspace/hello.txt"))
    for entry in sandbox.files.list("/workspace"):
        print(entry.type, entry.path, entry.size)
"""

import time
from typing import Any, Callable, List, Optional, Union

from . import _files as _f
from ._files import FileEntry, MakeDirResult, WriteInfo
from ._transport import call as _call, download as _download
from .errors import SandboxError


class Files:
    """Reads, writes and manages the files of one sandbox."""

    def __init__(self, client: Any, sandbox_id: str) -> None:
        self._client = client
        self._sandbox_id = sandbox_id

    # -- transfers -------------------------------------------------------

    def write(self, path: str, data: Union[str, bytes]) -> WriteInfo:
        """Writes ``data`` to a file, up to 50 MiB. ``str`` is encoded as UTF-8.

        Missing parent directories are created and an existing file is replaced.
        The SHA-256 of the body is sent for the sandbox to check.
        """
        return self._upload(_f.require_path(path), _f.to_bytes(data), False)

    def write_archive(self, path: str, tar: bytes) -> WriteInfo:
        """Extracts a tar archive (up to 50 MiB) into the directory ``path``."""
        return self._upload(_f.require_path(path), _f.to_bytes(tar), True)

    def read(self, path: str) -> bytes:
        """Reads a file, up to 50 MiB.

        Raises :class:`SandboxError` if the download fails its integrity check.
        To read a directory, use :meth:`read_archive`.
        """
        return self._download(_f.require_path(path), False)

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Reads a file and decodes it."""
        return self.read(path).decode(encoding)

    def read_archive(self, path: str) -> bytes:
        """Reads a file or directory as a tar archive, up to 50 MiB."""
        return self._download(_f.require_path(path), True)

    # -- metadata --------------------------------------------------------

    def list(self, path: str, *, depth: Optional[int] = None) -> List[FileEntry]:
        """Lists a directory. Symlinks are listed, not followed.

        :keyword depth: How many levels to list. ``1``, the default, lists the
            directory's own entries; ``2`` adds the entries of its subdirectories.
        """
        res = _call(
            self._client.sandboxes.list_files,
            self._sandbox_id,
            path=_f.require_path(path),
            depth=_f.require_depth(depth),
        )
        return [_f.to_entry(raw) for raw in (res or {}).get("entries") or []]

    def get_info(self, path: str) -> FileEntry:
        """Describes a file, directory or symlink.

        Raises :class:`NotFoundError` when nothing is at ``path``.
        """
        res = _call(
            self._client.sandboxes.get_file_info,
            self._sandbox_id,
            path=_f.require_path(path),
        )
        return _f.to_entry((res or {}).get("entry"))

    def exists(self, path: str) -> bool:
        """True when a file, directory or symlink exists at ``path``."""
        res = _call(
            self._client.sandboxes.get_files_exists,
            self._sandbox_id,
            path=_f.require_path(path),
        )
        return bool((res or {}).get("exists"))

    def make_dir(self, path: str) -> MakeDirResult:
        """Creates a directory and any missing parents.

        ``created`` is ``False`` when the directory already existed.
        """
        res = _call(
            self._client.sandboxes.post_files_make_directory,
            self._sandbox_id,
            {"path": _f.require_path(path)},
        )
        return _f.to_make_dir(res)

    def move(self, source: str, destination: str) -> FileEntry:
        """Moves or renames a file, directory or symlink.

        Returns the entry at its new path. Missing parents of ``destination``
        are created, and a file already there is replaced.
        """
        body = {
            "source": _f.require_path(source, "source"),
            "destination": _f.require_path(destination, "destination"),
        }
        res = _call(self._client.sandboxes.post_files_move, self._sandbox_id, body)
        return _f.to_entry((res or {}).get("entry"))

    def remove(self, path: str) -> None:
        """Removes a file, or a directory with everything in it.

        A missing path is not an error.
        """
        _call(
            self._client.sandboxes.post_files_remove,
            self._sandbox_id,
            {"path": _f.require_path(path)},
        )

    # -- internals -------------------------------------------------------

    def _upload(self, path: str, data: bytes, is_archive: bool) -> WriteInfo:
        digest = _f.sha256_hex(data)
        res = _retry(
            lambda: _call(
                self._client.sandboxes.post_files_upload,
                self._sandbox_id,
                data,
                path=path,
                is_archive=is_archive or None,
                x_content_sha256=digest,
                retry_status=0,
            )
        )
        return _f.to_write_info(res)

    def _download(self, path: str, as_archive: bool) -> bytes:
        body = _retry(
            lambda: _download(
                self._client.sandboxes.get_files_download,
                self._sandbox_id,
                path=path,
                as_archive=as_archive or None,
            )
        )
        return _f.split_download(body)


def _retry(send: Callable[[], Any]) -> Any:
    """Retries a transfer the sandbox refused with ``503`` (too many at once)."""
    attempt = 0
    while True:
        try:
            return send()
        except SandboxError as err:
            delay = _f.retry_delay(attempt, err)
            if delay is None:
                raise
            attempt += 1
            time.sleep(delay)


__all__ = ["FileEntry", "Files", "MakeDirResult", "WriteInfo"]
