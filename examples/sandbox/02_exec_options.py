"""Options of `sbx.exec`: cwd, env, timeout, argv vs shell, failures, check=True.

    python examples/sandbox/02_exec_options.py

You should see the working directory, an env var, a timeout, a failing command
that returns ok False without raising, and a CommandError caught with its result.

Needs DIGITALOCEAN_ACCESS_TOKEN. Set DIGITALOCEAN_API_URL to use another API address.
"""

from pydo import Sandbox
from pydo.sandbox import CommandError

with Sandbox.create() as sbx:
    # cwd and env apply to this one command.
    r = sbx.exec("pwd && echo GREETING=$GREETING", cwd="/tmp", env={"GREETING": "hi"})
    print("cwd + env       :", r.stdout.split())

    # A string runs in a shell. A list is an argv: no shell, so no $VARS or pipes.
    print("shell string    :", sbx.exec("echo $HOME").stdout.strip())
    print("argv list       :", sbx.exec(["echo", "$HOME"]).stdout.strip())

    # timeout takes seconds or a string like "30s", "10m", "2h".
    print("with timeout    :", sbx.exec("echo quick", timeout="30s").stdout.strip())

    # A non-zero exit is returned, not raised.
    failed = sbx.exec("echo oops >&2; exit 3")
    print(
        "failing command :",
        f"ok={failed.ok} exit_code={failed.exit_code} stderr={failed.stderr.strip()!r}",
    )

    # check=True raises CommandError, which carries the result.
    try:
        sbx.exec("echo about to fail; exit 4", check=True)
    except CommandError as err:
        print(
            "CommandError    :",
            f"exit_code={err.result.exit_code} stdout={err.result.stdout.strip()!r}",
        )
