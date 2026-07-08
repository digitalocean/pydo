"""Run Python code in the Action Gateway sandbox (action.code).

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  PYDO_GATEWAY_ENDPOINT   preview: https://actions.do-ai-test.run
"""

import os

from pydo import Client

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])

result = client.gateway.code.execute(
    "import sys\n" "print('hello from the sandbox')\n" "print(sys.version)\n",
    thought="verify the sandbox works",
)

print("exit_code:", result.get("exit_code"))
print("stdout:")
print(result.get("stdout"))
if result.get("stderr"):
    print("stderr:")
    print(result.get("stderr"))
