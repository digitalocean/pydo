"""Send input to a process: a live session, and the one-shot `stdin=` option.

    python examples/sandbox/04_stdin.py

You should see `cat` echo back the two lines you wrote, with exit code 0, then
"3" from `wc -l`.

Needs DIGITALOCEAN_ACCESS_TOKEN. Set DIGITALOCEAN_API_URL to use another API address.
"""

from pydo import Sandbox

with Sandbox.create() as sbx:
    # 1. A live session: write, close stdin so `cat` sees end of file, then wait.
    session = sbx.exec.start(["cat"])
    try:
        session.write_stdin("first line\n")
        session.write_stdin("second line\n")
        session.close_stdin()
        result = session.wait()
    finally:
        session.close()
    print("cat printed:", result.stdout.splitlines(), "exit code", result.exit_code)

    # 2. One shot: pass the whole input with stdin=.
    counted = sbx.exec("wc -l", stdin="a\nb\nc\n")
    print("wc -l      :", counted.stdout.strip())
