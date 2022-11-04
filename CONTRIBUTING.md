# Contributing to the DO Python Client

First: if you're unsure or afraid of anything, just ask or submit the issue or pull request anyways. You won't be yelled at for giving your best effort. The worst that can happen is that you'll be politely asked to change something. We appreciate all contributions!

## A Little Bit of Context

The DigitalOcean Python client is generated using [AutoRest](https://github.com/Azure/autorest). The AutoRest tool generates client libraries for accessing RESTful web services. Input to AutoRest is a spec that describes the DigitalOcean REST API using the OpenAPI 3.0 Specification format. The spec can be found [here](https://github.com/digitalocean/openapi). AutoRest allows customizations to be made on top of the generated code.

## Customizing the Client Using Patch Files

On top of generating our client, we've added a few customizations to create a better user experience. These customizations can by making changes to the `_patch.py` file. To learn more about adding customizations, please follow Autorest's documentation for it [here](https://github.com/Azure/autorest.python/blob/autorestv3/docs/customizations.md)

## Prerequisites

* Python version: >= 3.9 (it's highly recommended to use a python version management tool)
* [poetry](https://python-poetry.org/): python packaging and dependency management
* [AutoRest](https://github.com/Azure/autorest): The tool that generates the client libraries for accessing RESTful web services.

### Optional but highly recommended

We chose not to tie this repository to tooling for managing python installations. This allows developers to use their preferred tooling.

We like these:

* [pyenv](https://github.com/pyenv/pyenv): python version management
  * [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv):
  a pyenv plugin to enable pyenv to manage virtualenvs for development
  environment isolation

## Setup

1. Clone this repository. Run:

    ```sh
    git clone git@github.com:digitalocean/pydo.git
    cd pydo
    ```

1. (Optional) Ensure you have the right version of python installed using your preferred python version manager. This is what you'd run if you used `pyenv`:

    ```sh
    pyenv install 3.9.4
    ```

    This can take a few minutes.

1. Install the package dependencies

    ```sh
    poetry install
    ```

1. You can now activate your virtual environment

    ```sh
    poetry shell
    ```
