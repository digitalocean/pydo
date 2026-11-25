"""Stream output while a command runs, two ways.

    python examples/sandbox/03_stream_output.py

You should see "tick 1" to "tick 3" appear one second apart (callback), then the
events of a second command: stdout, stderr, exit (a `started` event with the
exec id appears when you keep stdin open, as in example 04).

Needs DIGITALOCEAN_ACCESS_TOKEN. Set DIGITALOCEAN_API_URL to use another API address.
"""

import sys

from pydo import Sandbox

with Sandbox.create() as sbx:
    # 1. Callbacks get each chunk of text as it arrives.
    print("-- on_stdout callback")
    result = sbx.exec(
        "for i in 1 2 3; do echo tick $i; sleep 1; done",
        on_stdout=lambda text: print("  got:", text.rstrip()),
        on_stderr=lambda text: print("  err:", text.rstrip(), file=sys.stderr),
    )
    print("exit code:", result.exit_code)

    # 2. A session gives you every event. Iterate it, then it is finished.
    print("-- exec.start events")
    with sbx.exec.start(
        "echo out; echo err >&2; exit 2", keep_stdin_open=False
    ) as session:
        for event in session:
            if event.type == "started":
                print("  started", event.exec_id)
            elif event.type in ("stdout", "stderr"):
                print(f"  {event.type}", repr(event.text))
            elif event.type == "exit":
                print("  exit", event.exit_code, f"({event.duration_ms} ms)")
