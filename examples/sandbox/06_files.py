"""Work with files in the sandbox: the files API, with an exec fallback.

    python examples/sandbox/06_files.py

You should see each files call succeed. On the internal test API the files API
is not available yet: you then see a clear message, and the same job done with
`exec` and base64 (write a small file, read it back). Exit code is 0 either way.

Needs DIGITALOCEAN_ACCESS_TOKEN. Set DIGITALOCEAN_API_URL to use another API address.
"""

import base64
import shlex

from pydo import Sandbox
from pydo.sandbox import ConflictError, NotFoundError


def write_file(sbx, path, text):
    """Fallback: write a file through exec. base64 keeps quotes and newlines safe."""
    data = base64.b64encode(text.encode()).decode()
    sbx.exec(f"echo {data} | base64 -d > {shlex.quote(path)}", check=True)


def read_file(sbx, path):
    """Fallback: read a file through exec."""
    return sbx.exec(["cat", path], check=True).stdout


with Sandbox.create() as sbx:
    try:
        sbx.files.make_dir("/tmp/demo")
        sbx.files.write("/tmp/demo/hello.txt", "hello files\n")
        print("read_text:", repr(sbx.files.read_text("/tmp/demo/hello.txt")))
        print("exists   :", sbx.files.exists("/tmp/demo/hello.txt"))
        print("list     :", [e.name for e in sbx.files.list("/tmp/demo")])
        sbx.files.move("/tmp/demo/hello.txt", "/tmp/demo/moved.txt")
        sbx.files.remove("/tmp/demo/moved.txt")
        print("files API works")
    except (ConflictError, NotFoundError) as err:
        # Known on the internal test API: upload and download answer 404 and the
        # other calls answer 409 "template image does not support file system operations".
        print(
            f"the files API is not available on this template yet ({type(err).__name__}: {err.message})"
        )
        print("-- fallback: exec + base64")
        sbx.exec("mkdir -p /tmp/demo", check=True)
        write_file(sbx, "/tmp/demo/hello.txt", "hello files\n")
        print("read back:", repr(read_file(sbx, "/tmp/demo/hello.txt")))
