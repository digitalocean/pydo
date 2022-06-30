# digitalocean-python-client

`digitalocean-python-client` is the official python client library that allows
python developers to interact with and manage their DigitalOcean account
resources through the
[DigitalOcean API](https://developers.digitalocean.com/documentation/v2/).

# Purpose

To provide a "DO simple" Python API for interacting with and managing
DigitalOcean resources.

A top priority of this project is to ensure the client abides by the API
contract. Therefore, the client itself wraps a generated client based
on the [DigitalOcean OpenAPI Specification](https://github.com/digitalocean/openapi).

# About the DigitalOcean Python Client

# Using the client
## Prerequisites

* Python version: >= 3.9

### TODO
* Automate packaging and publishing to pypi.
* Add installation instructions
* Add usage instructions

# Contributing

Visit our [Contribuing Guide](CONTRIBUTING.md) for more information on getting involved in developing this client.

## Local generation

Sometimes you want to make changes to the client configurations or customizations and test them locally. Everything you need to do this is in the Makefile. Below will provide instructions on how to generate the DO python client locally:

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
    * Can be installed using something like [pyenv](https://github.com/pyenv/pyenv) which
      can also manage python virtual environments
* [Poetry](https://python-poetry.org/docs/#installation).
    * can also be configured to manage python virtual environments

There are two types of test suites in the `tests/` directory.

### `tests/mocked/`

Tests in the `mocked` directory include:

* tests that validate the generated client has all the expected classes and methods for the respective API
  resources and operations.
* tests that excercise individual operations against mocked responses.

These tests do not act against the real API so no real resources are created.

To run mocked tests, run:

```
make test-mocked
```

### `tests/integration/`

Tests in the `integration` directory include tests that simulate specific scenarios a cusomter might use the client to
interact with the API. **_IMPORTANT:_** test tests require a valid API token and **_DO_** create real resources on the
respective DigitalOcean account.

To run integration tests, run:

```
DO_TOKEN=<valid-token> make test-integration
```