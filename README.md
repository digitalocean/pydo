
# The DigitalOcean Python library

`digitalocean-python-client` is the official python client library that allows
python developers to interact with and manage their DigitalOcean account
resources through the
[DigitalOcean API](https://developers.digitalocean.com/documentation/v2/). 

A top priority of this project is to ensure the client abides by the API
contract. Therefore, the client itself wraps a generated client based
on the [DigitalOcean OpenAPI Specification](https://github.com/digitalocean/openapi).


# Getting Started With the Client
## Prerequisites

* Python version: >= 3.9

## Installation (placeholder- not official yet)
To install from pip:

    pip install digitalocean-python

To install from source: (todo)

    python setup.py install

## DigitalOcean API
To support all DigitalOcean's HTTP APIs, a generated library is available which will expose all the endpoints:  [digitalocean-api-client-python](https://github.com/digitalocean/digitalocean-client-python/tree/main/src/digitalocean).

Find below a working example for GET a ssh_key ([per this http request](https://docs.digitalocean.com/reference/api/api-reference/#operation/sshKeys_list)) and printing the ID associated with the ssh key. If you'd like to try out this quick example, you can follow [these instructions](https://docs.digitalocean.com/products/droplets/how-to/add-ssh-keys/) to add ssh keys to your DO account. 
```python
import os
from digitalocean import DigitalOceanClient
# would be nice to not need this 
from azure.core.exceptions import HttpResponseError

api_key = <YOUR DO TOKEN>
ssh_key_fingerprint = <YOUR SSH KEY FINGERPRINT>

class SSHKeyIDGetter:
    def __init__(self, *args, **kwargs):
        if api_key == "":
            raise Exception("No DigitalOcean API token provided")
        client = DigitalOceanClient(token=api_key)  
        self.client = client
    
    def main(self):
        if ssh_key_fingerprint == "":
            raise Exception("SSH_KEY_FINGERPRINT not set")
        resp = self.get_ssh_key_id(ssh_key_fingerprint)
        print("SSH Key ID is {0}".format(resp["ssh_key"]["id"]))


    def get_ssh_key_id(self, ssh_key_fingerprint):
        print("GETting ssh key with fingerprint {0}...".format(ssh_key_fingerprint))
        try: 
            ssh_key_resp = self.client.ssh_keys.get(ssh_key_identifier=ssh_key_fingerprint)
            return ssh_key_resp
        except HttpResponseError as err:
            self.throw("Error: {0} {1}: {2}".format(err.status_code, err.reason, err.error.message))

        raise Exception("no ssh key found")


if __name__ == '__main__':
    dc = SSHKeyIDGetter()
    dc.main()
```

More working examples can be found [here](https://github.com/digitalocean/digitalocean-client-python/tree/main/examples).


# Contributing

Visit our [Contribuing Guide](CONTRIBUTING.md) for more information on getting involved in developing this client.

## Local generation

You may want to make changes to the client configurations or customizations and test them locally. Everything you need to do this is in the Makefile. Below will provide instructions on how to generate the DO python client locally:

The following command will will download the latest published spec and generatethe client:
```
make generate
```

To overwrite that behavior and use a local spec file, run the following instead:
```
SPEC_FILE=path/to/local/spec make generate
```

To test the client you just generated, we have included a POC that creates a Droplet and Attaches a Volume to the Droplet. Before you run the script, you'll need the following exported variables: 
```
export DO_TOKEN=<INSERT-YOUR-DO-TOKEN> 
export SSH_KEY_NAME=<INSERT-YOUR-SSH_KEY_NAME>       
```

Instructions on creating a DO token can be
found [here](https://docs.digitalocean.com/reference/api/create-personal-access-token/)

Instructions on creating an SSH Key can be
found [here](https://docs.digitalocean.com/products/droplets/how-to/add-ssh-keys/)

You are ready to run the script. Run the following:
> ** Running the following Python script will create billed resources in your account **

```
python3 examples/poc_droplets_volumes_sshkeys.py
```

## Running tests

The tests included in this repo are used to validate the generated client.
We use `pytest` to define and run the tests.

**_Requirements_**

* Python 3.9+
    * Can be installed using something like [pyenv](https://github.com/pyenv/pyenv)
        * used to manage different installed versions of python.
        * can also manage python virtual environments (with a plugin)
    * [Poetry](https://python-poetry.org/docs/#installation).
        * can also be configured to manage python virtual environments.

There are two types of test suites in the `tests/` directory.

### `tests/mocked/`

Tests in the `mocked` directory include:

* tests that validate the generated client has all the expected classes and
methods for the respective API resources and operations.
* tests that excercise individual operations against mocked responses.

These tests do not act against the real API so no real resources are created.

To run mocked tests, run:

```
make test-mocked
```

### `tests/integration/`

Tests in the `integration` directory include tests that simulate specific
scenarios a cusomter might use the client to interact with the API.
**_IMPORTANT:_** test tests require a valid API token and **_DO_** create real
resources on the respective DigitalOcean account.

To run integration tests, run:

```
DO_TOKEN=<valid-token> make test-integration
```

#### Customizations

Some test values can be customized so integration tests can exercise different
scenarios. For example, test use a default region to create resources. All the
default values are managed in the
[tests/integration/defaults.py](tests/integration/defaults.py) file. Any value
that has `environ.get(` can be overwritten by setting the respective environment
variable.