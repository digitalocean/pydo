"""Catch the typed errors of the SDK.

    python examples/sandbox/09_errors.py

You should see three API errors caught by type (not found, invalid request,
authentication) with status, code and request id (the request id may be None),
a name check done by the SDK itself, then the base class `SandboxError`.

Needs DIGITALOCEAN_ACCESS_TOKEN. Set DIGITALOCEAN_API_URL to use another API address.
"""

from pydo import Sandbox
from pydo.sandbox import (
    AuthenticationError,
    InvalidRequestError,
    NotFoundError,
    SandboxError,
)


def show(label, err):
    print(
        f"{label}: {type(err).__name__} status={err.status} code={err.code} request_id={err.request_id}"
    )
    print(f"    {err.message}")


# 404: no such sandbox.
try:
    Sandbox.get("00000000-0000-0000-0000-000000000000")
except NotFoundError as err:
    show("not found    ", err)

# 422: the API rejects the request. "no-such-size" is not a size.
try:
    Sandbox.create(size="no-such-size")
except InvalidRequestError as err:
    show("invalid      ", err)

# Some checks run in the SDK before any request is sent. A bad snapshot name
# ("Bad Name": capital letter and space) raises a plain SandboxError, status 0.
with Sandbox.create() as sbx:
    try:
        sbx.create_snapshot(name="Bad Name")
    except SandboxError as err:
        show("bad name     ", err)

# 401: pass a wrong token explicitly. Your real token and environment are not touched.
try:
    Sandbox.get("00000000-0000-0000-0000-000000000000", token="not-a-real-token")
except AuthenticationError as err:
    show("auth         ", err)

# SandboxError is the base class of every error above.
try:
    Sandbox.get("00000000-0000-0000-0000-000000000000")
except SandboxError as err:
    print("base class   :", type(err).__name__, "is a SandboxError, status", err.status)
