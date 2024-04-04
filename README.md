# **PyDo**

`pydo` is the official Python client library that allows
Python developers to interact with and manage their DigitalOcean
resources through a Python abstraction layer on top of the raw
[DigitalOcean API HTTP Interface](https://developers.digitalocean.com/documentation/v2/).

A top priority of this project is to ensure the client abides by the API
contract. Therefore, the client itself wraps a generated client based
on the [DigitalOcean OpenAPI Specification](https://github.com/digitalocean/openapi) to support all of DigitalOcean's HTTP APIs.

# **Getting Started With the Client**

## Prerequisites

- Python version: >= 3.7.2

## Installation

To install from pip:

```shell
    pip install git+https://github.com/digitalocean/pydo.git
```

or, if repo is cloned locally:

```shell
    pip install /<PATH>/<TO>/pydo
```

To install from source:

```shell
make install
```

## **`pydo` Quickstart**

> A quick guide to getting started with the client.

`pydo` must be initialized with `pydo.Client()`. A DigitalOcean API Token is required. The token can be passed explicitly to `pydo.Client()`, as such:

```python
import os
from pydo import Client

client = Client(token=os.getenv("DIGITALOCEAN_TOKEN"))
```

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

**Consult the full list of supported DigitalOcean API endpoints in [PyDo's documentation](https://pydo.readthedocs.io/en/latest/).**

**Note**: More working examples can be found [here](https://github.com/digitalocean/pydo/tree/main/examples).

#### Pagination Example

Below is an example on handling pagination. One must parse the URL to find the
next page.

```python
resp = self.client.ssh_keys.list(per_page=50, page=page)
pages = resp.links.pages
if 'next' in pages.keys():
    parsed_url = urlparse(pages['next'])
    page = parse_qs(parsed_url.query)['page'][0]
else:
    paginated = False
```

#### Retries and Backoff

By default the client uses the same retry policy as the [Azure SDK for Python](https://learn.microsoft.com/en-us/python/api/azure-core/azure.core.pipeline.policies.retrypolicy?view=azure-python).
retry policy. If you'd like to modify any of these values, you can pass them as keywords to your client initialization:

```python
client = Client(token=os.getenv("DIGITALOCEAN_TOKEN"), retry_total=3)
```

or

```python
client = Client(token=os.getenv("DIGITALOCEAN_TOKEN"), retry_policy=MyRetryPolicy())
```

# **Contributing**

>Visit our [Contribuing Guide](CONTRIBUTING.md) for more information on getting
involved in developing this client.

# **Tests**

>The tests included in this repo are used to validate the generated client.
We use `pytest` to define and run the tests.

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

>This selection lists the known issues of the client generator.

#### `kubernetes.get_kubeconfig` Does not serialize response content

In the generated python client, when calling client.kubernetes.get_kubeconfig(clust_id), the deserialization logic raises an error when the response content-type is applicaiton/yaml. We need to determine if the spec/schema can be configured such that the generator results in functions that properly handle the content. We will likely need to report the issue upstream to request support for the content-type.

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

>This section lists short-term and long-term goals for the project.
**Note**: These are goals, not necessarily commitments. The sections are not intended to represent exclusive focus during these terms.

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

> Model support, expand on supporting functions

- The client currently inputs and outputs JSON dictionaries. Adding models would unlock features such as typing and validation.
- Add supporting functions to elevate customer experience (i.e. adding a funtion that surfaces IP address for a Droplet)
