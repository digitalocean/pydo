# Sandbox examples

A sandbox is a small Linux machine in the DigitalOcean cloud that you create from code, run commands in, pause, snapshot and delete. `pydo.sandbox` is the Python SDK for it: it wraps the `/v2/sandboxes` API, turns failures into typed exceptions, and gives you a sandbox object with `exec`, `commands`, `files` and snapshot methods. Each example below is a few lines of customer code, and each is also a script in this folder that you can run.

Status: pre-release. The examples were checked against an internal test API, where some calls do not work yet (see [What works today](#what-works-today--known-issues)). Those scripts say so and carry on instead of crashing.

## Set up

You need Python 3.8 or newer, a DigitalOcean API token that can use sandboxes, and the address of the API you test against.

Install from this repository (a clone of `pydo`, on the `feat/sandbox-sdk` branch):

```shell
python -m venv .venv && . .venv/bin/activate
pip install -e .
```

Or install the package straight from GitHub:

```shell
pip install "pydo @ git+https://github.com/digitalocean/pydo.git@feat/sandbox-sdk"
```

Set your credentials. The SDK reads both variables, so your code does not need to pass them:

```shell
export DIGITALOCEAN_ACCESS_TOKEN=<your-token>
export DIGITALOCEAN_API_URL=<test-api-address>   # leave unset for the public API
```

Check that they work. This creates a sandbox, runs one command and deletes it:

```python
from pydo import Sandbox

with Sandbox.create() as sbx:
    print(sbx.exec("echo it works").stdout)
```

If that prints `it works`, run the examples.

## Run the examples

Run each script from the repository root, for example `python examples/sandbox/01_hello.py`.

| Script | What it does |
| --- | --- |
| [`01_hello.py`](01_hello.py) | Creates a sandbox, runs `echo` and `uname -a`, prints the output, exit code and `ok`, deletes it |
| [`02_exec_options.py`](02_exec_options.py) | `cwd`, `env`, `timeout`, argv list vs shell string, a failing command, `check=True` and `CommandError` |
| [`03_stream_output.py`](03_stream_output.py) | Streams output with an `on_stdout` callback, then reads `exec.start` events |
| [`04_stdin.py`](04_stdin.py) | Writes to `cat` through a session, then pipes text to `wc -l` with `stdin=` |
| [`05_lifecycle.py`](05_lifecycle.py) | Create, list, get, pause, resume, connect by id, get_info, is_running, delete |
| [`06_files.py`](06_files.py) | Files API, with an exec and base64 fallback when the API does not answer |
| [`07_snapshots.py`](07_snapshots.py) | Creates a snapshot, waits for it, gets it, tries to list, deletes it |
| [`08_templates.py`](08_templates.py) | Lists templates; with `TEMPLATE_IMAGE` builds one, uses it, deletes it |
| [`09_errors.py`](09_errors.py) | Catches `NotFoundError`, `InvalidRequestError`, `AuthenticationError` and the base `SandboxError` |
| [`10_parallel.py`](10_parallel.py) | Runs three sandboxes at the same time with threads |
| [`11_cleanup.py`](11_cleanup.py) | Lists your sandboxes older than `MAX_AGE_HOURS`; deletes them with `DELETE=1` |

Every script that creates something deletes it at the end, also when it fails or you press Ctrl-C.

## 1. Hello

```python
from pydo import Sandbox

with Sandbox.create() as sbx:  # template "coding-base", size "mars-2vcpu-4gb"
    result = sbx.exec("echo hello from the sandbox; uname -a")
    print(result.stdout, result.exit_code, result.ok)
```

`Sandbox.create()` returns once the sandbox is running. The `with` block deletes it on exit. `exec` runs a command and waits for it. Expect the sandbox id, your echo line, a `Linux ...` line, `exit code: 0` and `ok: True`.

Try this: pass `template=`, `size=` or `env_vars={"A": "1"}` to `create`.

## 2. Exec options

```python
r = sbx.exec("pwd && echo GREETING=$GREETING", cwd="/tmp", env={"GREETING": "hi"})
sbx.exec(["echo", "$HOME"])           # argv list: no shell, prints $HOME literally
sbx.exec("echo quick", timeout="30s")
failed = sbx.exec("exit 3")           # failed.ok is False, nothing is raised
try:
    sbx.exec("exit 4", check=True)
except CommandError as err:
    print(err.result.exit_code)
```

A string runs through `bash -lc`; a list runs as given. A non-zero exit is data, not an exception, unless you ask for `check=True`. `timeout` takes seconds or `"30s"`, `"10m"`, `"2h"`. Expect `/tmp` and `GREETING=hi`, `$HOME` unexpanded for the list form, `ok=False exit_code=3`, and the `CommandError` with exit code 4.

Try this: set `timeout=1` on `sleep 5` and see what happens.

## 3. Stream output

```python
sbx.exec("for i in 1 2 3; do echo tick $i; sleep 1; done",
         on_stdout=lambda text: print("got:", text.rstrip()))

with sbx.exec.start("echo out; echo err >&2; exit 2", keep_stdin_open=False) as session:
    for event in session:   # started, stdout, stderr, exit
        print(event.type, event.text, event.exit_code)
```

The callback runs as output arrives, so `tick 1` shows up before the command ends. A session gives you every event. With `keep_stdin_open=False` there is no `started` event; with stdin open (example 4) you get one with the exec id.

Try this: replace the loop with `apt list --installed | head` and watch it stream.

## 4. Stdin

```python
session = sbx.exec.start(["cat"])
session.write_stdin("first line\n")
session.write_stdin("second line\n")
session.close_stdin()          # cat sees end of file and exits
result = session.wait()

sbx.exec("wc -l", stdin="a\nb\nc\n")   # one-shot input
```

Use a session when you answer a running program step by step. Use `stdin=` when you have all the input up front. Expect both lines back from `cat`, then `3`.

Try this: start `python3 -i` instead of `cat` and send it a line of code.

## 5. Lifecycle

```python
sbx = Sandbox.create()
Sandbox.list()                 # iterate every page of your sandboxes
Sandbox.get(sbx.sandbox_id)    # fetch by id
sbx.pause(); sbx.resume()
Sandbox.connect(sbx.sandbox_id)  # fetch, and resume if paused
sbx.get_info(); sbx.is_running()
sbx.kill()                     # delete; also Sandbox.kill(sandbox_id)
```

Paused sandboxes keep their state but do not run commands. Expect `SANDBOX_STATE_RUNNING`, then `SANDBOX_STATE_PAUSED` with `is_running: False`, then running again, and finally a `NotFoundError` that confirms the delete.

Try this: write a file with `exec`, pause and resume, and read it back.

## 6. Files

```python
sbx.files.make_dir("/tmp/demo")
sbx.files.write("/tmp/demo/hello.txt", "hello files\n")
sbx.files.read_text("/tmp/demo/hello.txt")
sbx.files.list("/tmp/demo"); sbx.files.exists(path)
sbx.files.move(src, dst); sbx.files.remove(path)
```

On the test API every files call fails (see below). The script catches `ConflictError` and `NotFoundError`, prints "the files API is not available on this template yet", then does the job through `exec`: it writes with `echo <base64> | base64 -d > path` and reads with `cat`. It exits 0 either way.

Try this: copy the two fallback helpers into your own code until the files API works.

## 7. Snapshots

```python
snap = sbx.create_snapshot(name="example-123", ttl="1h")
snap.wait_until_ready()
Snapshot.get(snap.snapshot_id)
Snapshot.list(sandbox_id=sbx.sandbox_id)   # NotFoundError on the test API
snap.delete()
```

`create_snapshot` returns at once in the `CREATING` state; `wait_until_ready` polls until `COMPLETE`. Names are 1 to 63 lowercase letters, digits and hyphens, so the script adds a timestamp. Expect `created`, `ready`, `get`, "snapshot list is not available yet", `deleted : True`.

Try this: change `ttl` to `"24h"`, and keep the snapshot id to start a sandbox from it later.

## 8. Templates

```python
for t in Template.list():
    print(t.template_id, t.name, t.status)

template = Template.create(name="example-123", source_oci_ref="registry/repo:tag")
template.wait_until_ready()
with Sandbox.create(template=template.name) as sbx:
    sbx.exec("echo built from my image")
template.delete()
```

`Template.list` shows only your custom templates; the built-in `coding-base` is not listed. Without `TEMPLATE_IMAGE` the script lists and exits 0. With it, the script builds, uses and deletes a template, which can take a few minutes.

Try this: `TEMPLATE_IMAGE=<registry/repository:tag> python examples/sandbox/08_templates.py`

## 9. Errors

```python
try:
    Sandbox.get("00000000-0000-0000-0000-000000000000")
except NotFoundError as err:
    print(err.status, err.code, err.request_id, err.message)
except SandboxError as err:   # base class of all of them
    ...
```

Every failure is a `SandboxError` subclass chosen by HTTP status: `AuthenticationError` (401), `PermissionDeniedError` (403), `NotFoundError` (404), `ConflictError` (409), `InvalidRequestError` (400, 422), `RateLimitError` (429, see `retry_after`), `ServiceError` (5xx), `SandboxTimeoutError` (a wait ran out), `CommandError` (`check=True`). The script triggers 404 (unknown id), 422 (`size="no-such-size"`), 401 (a wrong `token=` passed to that one call, so your environment is untouched), and shows that the SDK checks some arguments itself: the snapshot name `"Bad Name"` raises `SandboxError` with status 0 before any request. `request_id` can be `None` on this API.

Try this: catch `CommandError` around `exec(..., check=True)` and print `err.result.stderr`.

## 10. Parallel

```python
def work(n):
    with Sandbox.create() as sbx:
        return sbx.exec(f"echo job {n}").stdout.strip()

with ThreadPoolExecutor(max_workers=3) as pool:
    print(list(pool.map(work, [1, 2, 3])))
```

Each thread owns its sandbox and its `with` block, so each is deleted when its job ends. Expect three lines and a total time near one sandbox. An async version is in `pydo.aio`.

Try this: raise the count to 10 and watch for `RateLimitError`.

## 11. Cleanup

```python
for sbx in Sandbox.list():
    if sbx.info.created_at < cutoff:
        sbx.kill()
```

The script lists sandboxes older than `MAX_AGE_HOURS` (default 1) and does nothing else unless you set `DELETE=1`. It sees every sandbox your token can see, so read the dry run before you delete.

Try this: `MAX_AGE_HOURS=24 python examples/sandbox/11_cleanup.py`

## What works today / known issues

Works on the test API: create, get, list, connect, pause, resume, kill; `sbx.exec(...)` with all options; `sbx.exec.run` and `sbx.exec.start` sessions (stdin, events); `sbx.commands.list/start/kill`; snapshot create, wait, get, delete; template list, create, wait, delete.

Known issues, which the examples handle:

| Area | What happens | Workaround |
| --- | --- | --- |
| `sbx.files.upload` / `download` (`write`, `read`) | `NotFoundError` (404) | Write and read through `exec` and base64 (example 6) |
| Other `sbx.files.*` calls | `ConflictError` (409): "template image does not support file system operations" | Same |
| `Snapshot.list` | `NotFoundError` (404) | Keep the snapshot ids you create |
| PTY: `exec.start(pty=...)` | `InvalidRequestError` | Use `exec` without a PTY |
| `sbx.commands` stdin | 404 | Use `sbx.exec.start` for stdin (example 4) |
| `sbx.commands.run` | Fails for commands that exit at once | Use `sbx.exec` |

## Cost and cleanup

Sandboxes bill while they exist, including paused ones. All scripts delete what they create, also on errors and Ctrl-C, because the `with` blocks and `finally` clauses run. If a run is killed hard, a sandbox can stay behind: run `python examples/sandbox/11_cleanup.py` to see your old sandboxes and `DELETE=1` to remove them.

## Environment variables

| Variable | Used by | Meaning |
| --- | --- | --- |
| `DIGITALOCEAN_ACCESS_TOKEN` | all | Your API token, `<your-token>` |
| `DIGITALOCEAN_API_URL` | all | API address, `<test-api-address>`; defaults to `https://api.digitalocean.com` |
| `TEMPLATE_IMAGE` | 08 | Container image (`registry/repository:tag`) to build a template from |
| `MAX_AGE_HOURS` | 11 | Age limit in hours (default 1) |
| `DELETE` | 11 | `1` deletes the sandboxes found; otherwise a dry run |

The scripts always delete what they create; there is no `KEEP` switch.
