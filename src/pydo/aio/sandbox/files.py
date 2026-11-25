# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async files in a sandbox: ``/v2/sandboxes/{id}/files``.

Hand-written; preserved across ``make generate``. The async twin of
:mod:`pydo.sandbox.files`: same names, with ``await``.

.. code-block:: python

    await sandbox.files.write("/workspace/hello.txt", "Hello")
    print(await sandbox.files.read_text("/workspace/hello.txt"))
"""

import asyncio
from typing import Any, Awaitable, Callable, List, Optional, Union

from pydo.sandbox import _files as _f
from pydo.sandbox._files import FileEntry, MakeDirResult, WriteInfo
from pydo.sandbox.errors import SandboxError

from ._transport import call as _call, download as _download


class Files:
    """Reads, writes and manages the files of one sandbox."""

    def __init__(self, client: Any, sandbox_id: str) -> None:
        self._client = client
        self._sandbox_id = sandbox_id

    # -- transfers -------------------------------------------------------

    async def write(self, path: str, data: Union[str, bytes]) -> WriteInfo:
        """Writes ``data`` to a file, up to 50 MiB. ``str`` is encoded as UTF-8.

        Missing parent directories are created and an existing file is replaced.
        The SHA-256 of the body is sent for the sandbox to check.
        """
        return await self._upload(_f.require_path(path), _f.to_bytes(data), False)

    async def write_archive(self, path: str, tar: bytes) -> WriteInfo:
        """Extracts a tar archive (up to 50 MiB) into the directory ``path``."""
        return await self._upload(_f.require_path(path), _f.to_bytes(tar), True)

    async def read(self, path: str) -> bytes:
        """Reads a file, up to 50 MiB.

        Raises :class:`SandboxError` if the download fails its integrity check.
        To read a directory, use :meth:`read_archive`.
        """
        return await self._download(_f.require_path(path), False)

    async def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Reads a file and decodes it."""
        return (await self.read(path)).decode(encoding)

    async def read_archive(self, path: str) -> bytes:
        """Reads a file or directory as a tar archive, up to 50 MiB."""
        return await self._download(_f.require_path(path), True)

    # -- metadata --------------------------------------------------------

    async def list(self, path: str, *, depth: Optional[int] = None) -> List[FileEntry]:
        """Lists a directory. Symlinks are listed, not followed.

        :keyword depth: How many levels to list. ``1``, the default, lists the
            directory's own entries; ``2`` adds the entries of its subdirectories.
        """
        res = await _call(
            self._client.sandboxes.list_files,
            self._sandbox_id,
            path=_f.require_path(path),
            depth=_f.require_depth(depth),
        )
        return [_f.to_entry(raw) for raw in (res or {}).get("entries") or []]

    async def get_info(self, path: str) -> FileEntry:
        """Describes a file, directory or symlink.

        Raises :class:`NotFoundError` when nothing is at ``path``.
        """
        res = await _call(
            self._client.sandboxes.get_file_info,
            self._sandbox_id,
            path=_f.require_path(path),
        )
        return _f.to_entry((res or {}).get("entry"))

    async def exists(self, path: str) -> bool:
        """True when a file, directory or symlink exists at ``path``."""
        res = await _call(
            self._client.sandboxes.get_files_exists,
            self._sandbox_id,
            path=_f.require_path(path),
        )
        return bool((res or {}).get("exists"))

    async def make_dir(self, path: str) -> MakeDirResult:
        """Creates a directory and any missing parents.

        ``created`` is ``False`` when the directory already existed.
        """
        res = await _call(
            self._client.sandboxes.post_files_make_directory,
            self._sandbox_id,
            {"path": _f.require_path(path)},
        )
        return _f.to_make_dir(res)

    async def move(self, source: str, destination: str) -> FileEntry:
        """Moves or renames a file, directory or symlink.

        Returns the entry at its new path. Missing parents of ``destination``
        are created, and a file already there is replaced.
        """
        body = {
            "source": _f.require_path(source, "source"),
            "destination": _f.require_path(destination, "destination"),
        }
        res = await _call(
            self._client.sandboxes.post_files_move, self._sandbox_id, body
        )
        return _f.to_entry((res or {}).get("entry"))

    async def remove(self, path: str) -> None:
        """Removes a file, or a directory with everything in it.

        A missing path is not an error.
        """
        await _call(
            self._client.sandboxes.post_files_remove,
            self._sandbox_id,
            {"path": _f.require_path(path)},
        )

    # -- internals -------------------------------------------------------

    async def _upload(self, path: str, data: bytes, is_archive: bool) -> WriteInfo:
        digest = _f.sha256_hex(data)
        res = await _retry(
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

    async def _download(self, path: str, as_archive: bool) -> bytes:
        body = await _retry(
            lambda: _download(
                self._client.sandboxes.get_files_download,
                self._sandbox_id,
                path=path,
                as_archive=as_archive or None,
            )
        )
        return _f.split_download(body)


async def _retry(send: Callable[[], Awaitable[Any]]) -> Any:
    """Retries a transfer the sandbox refused with ``503`` (too many at once)."""
    attempt = 0
    while True:
        try:
            return await send()
        except SandboxError as err:
            delay = _f.retry_delay(attempt, err)
            if delay is None:
                raise
            attempt += 1
            await asyncio.sleep(delay)


__all__ = ["FileEntry", "Files", "MakeDirResult", "WriteInfo"]
