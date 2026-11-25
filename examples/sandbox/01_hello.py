"""Create a sandbox, run a command in it, print the result, delete the sandbox.

    python examples/sandbox/01_hello.py

You should see the sandbox id, the output of `echo` and `uname -a`, exit code 0
and ok True, then a line saying the sandbox was deleted.

Needs DIGITALOCEAN_ACCESS_TOKEN. Set DIGITALOCEAN_API_URL to use another API address.
"""

from pydo import Sandbox

# The `with` block deletes the sandbox when it ends, even on an error or Ctrl-C.
with Sandbox.create() as sbx:  # template "coding-base", size "mars-2vcpu-4gb"
    print(f"sandbox {sbx.sandbox_id} is {sbx.state}")

    result = sbx.exec("echo hello from the sandbox; uname -a")
    print("stdout   :", result.stdout.strip())
    print("exit code:", result.exit_code)
    print("ok       :", result.ok)

print("sandbox deleted")
