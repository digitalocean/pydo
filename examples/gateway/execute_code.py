"""Run Python code in the Action Gateway sandbox (action_code).

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  PYDO_GATEWAY_ENDPOINT   preview: https://actions.do-ai-test.run
  END_USER_ID
"""

import os

from pydo.action_gateway import Client

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
session = client.sessions.create(
    end_user_id=os.environ.get("END_USER_ID", "example-user"),
)

result = session.code.execute(
    "import sys\n" "print('hello from the sandbox')\n" "print(sys.version)\n",
    thought="verify the sandbox works",
)

print("exit_code:", result.get("exit_code"))
print("stdout:")
print(result.get("stdout"))
if result.get("stderr"):
    print("stderr:")
    print(result.get("stderr"))
