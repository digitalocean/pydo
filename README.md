# **PyDo**

`pydo` is the official Python client library that allows
Python developers to interact with and manage their DigitalOcean
resources through a Python abstraction layer on top of the raw
[DigitalOcean API HTTP Interface](https://developers.digitalocean.com/documentation/v2/).

A top priority of this project is to ensure the client abides by the API
contract. Therefore, the client itself wraps a generated client based
on the [DigitalOcean OpenAPI Specification](https://github.com/digitalocean/openapi) to support all of DigitalOcean's HTTP APIs.

> **🚀 New in v0.29.0 — AI & Inference support**
>
> `pydo` now ships first-class support for DigitalOcean's
> [Gradient AI Platform](https://www.digitalocean.com/products/gradient): chat
> completions (with streaming), image generation, audio, batch inference, and
> model listing — all from the same `Client`. Jump to
> [**AI & Inference**](#ai--inference) to get started.

# **Getting Started With the Client**

## Prerequisites

- Python version: >= 3.7.2

## Installation

To install from pip:

```shell
    pip install pydo
```

## **`pydo` Quickstart**

> A quick guide to getting started with the client.

`pydo` must be initialized with `pydo.Client()`. A DigitalOcean API Token is required. The token can be passed explicitly to `pydo.Client()`, as such:

```python
import os
from pydo import Client

client = Client(token=os.getenv("DIGITALOCEAN_TOKEN"))
```

> **ℹ️ `api_key=` vs `token=` — what's the difference?**
>
> They're the same thing. `token=` and `api_key=` are just two names for
> the same argument, and both work for every API in `pydo` — infrastructure
> and inference. Use whichever name reads better in your code.
>
> What matters is the **credential** you pass in, not the argument name:
>
> | What you're calling | What you need |
> | --- | --- |
> | Infrastructure APIs (`droplets`, `ssh_keys`, `kubernetes`, `volumes`, …) | A DigitalOcean API token (PAT). |
> | Inference APIs (`chat`, `images`, `models`, `audio`, `batches`, `files`, `responses`) | A PAT created with **full access** scope, **or** a Gradient **Model Access Key**. |
>
> If you only have a limited-scope PAT, infra calls will work but inference
> calls will fail with a 401. To fix it, create a new PAT with full access,
> or use a Model Access Key instead.
>
> ```python
> # All three of these work — pick the one you like:
> client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])    # full-access PAT
> client = Client(api_key=os.environ["DIGITALOCEAN_TOKEN"])  # same thing, different name
> client = Client(api_key=os.environ["MODEL_ACCESS_KEY"])    # Gradient model access key
> ```

#### Example of Using `pydo` to Access DO Resources

Find below a working example for GETting a ssh_key ([per this http request](https://docs.digitalocean.com/reference/api/api-reference/#operation/sshKeys_list)) and printing the ID associated with the ssh key. If you'd like to try out this quick example, you can follow [these instructions](https://docs.digitalocean.com/products/droplets/how-to/add-ssh-keys/) to add ssh keys to your DO account.

```python
import os
from pydo import Client

client = Client(token=os.getenv("DIGITALOCEAN_TOKEN"))

ssh_keys_resp = client.ssh_keys.list()
for k in ssh_keys_resp["ssh_keys"]:
    print(f"ID: {k['id']}, NAME: {k['name']}, FINGERPRINT: {k['fingerprint']}")
```

The above code snippet should output the following:

```shell
ID: 123456, NAME: my_test_ssh_key, FINGERPRINT: 5c:74:7e:60:28:69:34:ca:dd:74:67:c3:f3:00:7f:fe
ID: 123457, NAME: my_prod_ssh_key, FINGERPRINT: eb:76:c7:2a:d3:3e:80:5d:ef:2e:ca:86:d7:79:94:0d
```

**Consult the full list of supported DigitalOcean API endpoints in [PyDo's documentation](https://docs.digitalocean.com/reference/pydo/).**

**Note**: More working examples can be found [here](https://github.com/digitalocean/pydo/tree/main/examples).

## **AI & Inference**

> Talk to models on DigitalOcean's Gradient AI Platform with the same
> `pydo.Client`.

The snippets below use a **DigitalOcean PAT created with full access scope**
(required for inference APIs). A Gradient Model Access Key works too — see
the [credentials note](#pydo-quickstart) above.

#### Chat completions (streaming)

```python
import os
from pydo import Client

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])  # PAT with full access scope

stream = client.chat.completions.create(
    model="llama3.3-70b-instruct",
    messages=[{"role": "user", "content": "Tell me some fun facts about sharks"}],
    max_tokens=512,
    stream=True,
)

for chunk in stream:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    piece = delta.get("reasoning_content") or delta.get("content")
    if piece:
        print(piece, end="", flush=True)
print()
```

#### Image generation

```python
import os, base64
from pydo import Client

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])  # PAT with full access scope

result = client.images.generate(
    model="openai-gpt-image-1",
    prompt="A friendly cartoon shark typing on a laptop at a sunny beach",
    n=1,
)

with open("output.png", "wb") as f:
    f.write(base64.b64decode(result.data[0].b64_json))

print("Image saved as output.png")
```

#### List available models

```python
import os
from pydo import Client

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])  # PAT with full access scope

models = client.models.list()
for model in models["data"]:
    print(model["id"])
```

Runnable versions of the three snippets above live in
[`examples/inference/`](examples/inference/):

- [`chat_completion_stream.py`](examples/inference/chat_completion_stream.py)
- [`image_generation.py`](examples/inference/image_generation.py)
- [`list_models.py`](examples/inference/list_models.py)

For more (audio, batches, agents, async streaming responses, file uploads,
etc.), see the `inference_*.py` scripts in [`examples/`](examples/).

#### Pagination Example

Below is an example on handling pagination. One must parse the URL to find the
next page.

```python
import os
from pydo import Client
from urllib.parse import urlparse, parse_qs

client = Client(token=os.getenv("DIGITALOCEAN_TOKEN"))

paginated = True
page = 1

while paginated:
    resp = client.ssh_keys.list(per_page=50, page=page)

    for k in resp["ssh_keys"]:
        print(f"ID: {k['id']}, NAME: {k['name']}, FINGERPRINT: {k['fingerprint']}")

    pages = resp.get("links", {}).get("pages", {})
    if "next" in pages:
        parsed_url = urlparse(pages["next"])
        page = int(parse_qs(parsed_url.query)["page"][0])
    else:
        paginated = False
```

#### Async Usage

For async, import from `pydo.aio` instead of `pydo`. The surface is identical
— same constructor, same operation groups — just `await` the calls. Use
`async with` so the underlying transport closes cleanly.

```python
import asyncio, os
from pydo.aio import Client

async def main():
    async with Client(api_key=os.environ["DIGITALOCEAN_TOKEN"]) as client:
        resp = await client.chat.completions.create(
            model="llama3.3-70b-instruct",
            messages=[{"role": "user", "content": "Hello!"}],
        )
        print(resp)

asyncio.run(main())
```

#### Retries and Backoff

By default the client uses the same retry policy as the [Azure SDK for Python](https://learn.microsoft.com/en-us/python/api/azure-core/azure.core.pipeline.policies.retrypolicy?view=azure-python)
retry policy. If you'd like to modify any of these values, you can pass them as
keywords to your client initialization:

```python
client = Client(token=os.getenv("DIGITALOCEAN_TOKEN"), retry_total=3)
```

or

```python
client = Client(token=os.getenv("DIGITALOCEAN_TOKEN"), retry_policy=MyRetryPolicy())
```

# **Contributing**

> Visit our [Contribuing Guide](CONTRIBUTING.md) for more information on
> getting involved in developing this client.

# **Tests**

> The tests included in this repo are used to validate the generated client.
> We use `pytest` to define and run the tests.

**_Requirements_**

- Python 3.7+
  - Can be installed using something like
    [pyenv](https://github.com/pyenv/pyenv)
    - used to manage different installed versions of python.
    - can also manage python virtual environments (with a plugin)
  - [Poetry](https://python-poetry.org/docs/#installation).
    - can also be configured to manage python virtual environments.

There are two types of test suites in the `tests/` directory.

#### Mocked Tests: `tests/mocked/`

Tests in the `mocked` directory include:

- tests that validate the generated client has all the expected classes and
  methods for the respective API resources and operations.
- tests that exercise individual operations against mocked responses.

These tests do not act against the real API so no real resources are created.

To run mocked tests, run:

```shell
make test-mocked
```

#### Integration Tests: `tests/integration/`

Tests in the `integration` directory include tests that simulate specific
scenarios a customer might use the client for to interact with the API.
**_IMPORTANT:_** these tests require a valid API token and **_DO_** create real
resources on the respective DigitalOcean account.

To run integration tests, run:

```shell
DIGITALOCEAN_TOKEN=... make test-integration
```

#### Test Customizations

Some test values can be customized so integration tests can exercise different
scenarios. For example, test use a default region to create resources. All the
default values are managed in the
[tests/integration/defaults.py](tests/integration/defaults.py) file. Any value
that has `environ.get()` can be overwritten by setting the respective environment
variable.

#### Tests with Docker

The included Dockerfile is a developler convenience to test the package in
isolation.

To use it, first build the image. Run:

```shell
docker build -t pydo:dev .
```

##### Use the interactive python shell

Open the python shell:

```shell
docker run -it --rm --name pydo pydo:dev python
```

The above will launch an interactive python shell and display the following:

```shell
Skipping virtualenv creation, as specified in config file.
Python 3.10.5 | packaged by conda-forge | (main, Jun 14 2022, 07:06:46) [GCC 10.3.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>>
```

From here you can use the client interactively:

```shell
>>> from pydo import Client
>>> c = Client(DIGITALOCEAN_TOKEN)
>>> c.droplets.list()
```

Alternatively, the tests can be run by attaching the tests as a volume and
running pytest directly.

Run:

```shell
docker run -it --rm --name pydo -v $PWD/tests:/tests pydo:dev pytest tests/mocked
```

# **Known Issues**

> This selection lists the known issues of the client generator.

#### `kubernetes.create_cluster` does not accept `registry_enabled` parameter

The `registry_enabled` field in Kubernetes cluster responses is read-only and cannot be set during cluster creation. To enable container registry integration with a Kubernetes cluster, you must use the `add_registry` operation after creating the cluster.

**Correct approach:**

```python
# Create cluster
cluster = client.kubernetes.create_cluster({
    'name': 'my-cluster',
    'region': 'nyc3',
    'version': '1.32',
    'node_pools': [{
        'size': 's-1vcpu-2gb',
        'count': 2,
        'name': 'worker-pool'
    }]
})

cluster_id = cluster['kubernetes_cluster']['id']

# Enable registry integration
client.kubernetes.add_registry({'cluster_uuids': [cluster_id]})

# Verify registry is enabled
updated_cluster = client.kubernetes.get_cluster(cluster_id)
assert updated_cluster['kubernetes_cluster']['registry_enabled'] is True
```

See [issue #433](https://github.com/digitalocean/pydo/issues/433) for more details.

#### `kubernetes.get_kubeconfig` Does not serialize response content

In the generated Python client, calling client.kubernetes.get_kubeconfig(cluster_id) raises a deserialization error when the response content-type is application/yaml. This occurs because the generator does not correctly handle YAML responses. We should investigate whether the OpenAPI spec or generator configuration can be adjusted to support this content-type. If not, the issue should be reported upstream to improve YAML support in client generation.

Workaround (with std lib httplib):

```python
from http.client import HTTPSConnection

conn = HTTPSConnection('api.digitalocean.com')
conn.request(
    'GET',
    f'/v2/kubernetes/clusters/{cluster_id}/kubeconfig',
    headers={'Authorization': f'Bearer {os.environ["DIGITALOCEAN_TOKEN"]}'}
)
response = conn.getresponse()

if response.getcode() > 400:
    msg = 'Unable to get kubeconfig'
    raise RuntimeError(msg)

kube_config =  response.read().decode('utf-8')
conn.close()
```

#### `invoices.get_pdf_by_uuid(invoice_uuid=invoice_uuid_param)` Does not return PDF

In the generated python client, when calling `invoices.get_pdf_by_uuid`, the response returns a Iterator[bytes] that does not format correctly into a PDF.

#### Getting documentation via cli "help(<client function>)"

Currently, calling the "help(<client function>)" includes the API documentation for the respective operation which is substantial and can be confusing in the context of this client.

#### projects.delete(project_id=project_id) expects a request body

This is a backend issue with the API endpoint. The API endpoint expects the header `content-type: application/json` to be set. If you do not set it you will receive a 415. Since the endpoint doesn't require a request or response body, it is an unnecessary header. For this to work in Pydo, ensure `application/json` header is passed in, as such:

```python
    custom_headers = {"Content-Type": "application/json"}
    delete_resp = client.projects.delete(
        headers=custom_headers, project_id=project_id
    )
```

# **Roadmap**

> This section lists short-term and long-term goals for the project.
> **Note**: These are goals, not necessarily commitments. The sections are not intended to represent exclusive focus during these terms.

Short term:

> Usability, stability, and marketing.

Short term, we are focused on improving usability and user productivity (part of this is getting the word out).

- Documentation
  - Support an automated process for creating comprehensive documentation that explains working of codes
  - Support a clean cli `help(<client function>)` documentation solution
- Release stability
  - define release strategy
  - pip release

Long term:

> Model support, expand on supporting functions, deepen AI/Inference coverage

- The client currently inputs and outputs JSON dictionaries. Adding models would unlock features such as typing and validation.
- Add supporting functions to elevate customer experience (i.e. adding a funtion that surfaces IP address for a Droplet)
- **AI & Inference**: continue expanding coverage of the
  [Gradient AI Platform](https://www.digitalocean.com/products/gradient)
  alongside the infrastructure APIs — keeping chat, images, audio, batches,
  responses, agents, and model management feature-complete and idiomatic
  from the same `pydo.Client`. `pydo` is an
  infrastructure **and** AI SDK; both surfaces are first-class going forward.
