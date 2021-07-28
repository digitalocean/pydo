# Contributing

This guide helps developers set up a local 

## Prerequisites

* Python version: >= 3.9 (it's highly recommended to use a python version management tool)
* [poetry](https://python-poetry.org/): python packaging and dependency management

### Optional but highly recommended

We chose not to tie this repository to tooling for managing python installations. This allows developers to use their preferred tooling.

We like these:
* [pyenv](https://github.com/pyenv/pyenv): python version management
  * [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv):
  a pyenv pluging to enable pyenv to manage virtualenvs for development
  environment isolation

## Setup

1. Clone this repository. Run:
    ```sh
    git clone git@github.com:digitalocean/clientgen.git digitalocean-python-client
    cd digitalocean-python-client
    ```

1. (Optional) Ensure you have the right version of python installed using your prefered python version manager. This is what you'd run if you used `pyenv`:
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

1. Use the client
   > NOTE: following this will create real resources on the DigitalOcean
   > account.

    ```python
    from digitalocean.droplets import Droplet, DropletsAPI, exceptions
    
    
    ## create an instance of the DropletsAPI 
    droplet_api = DropletsAPI("YOUR-DIGITALOCEAN-API-TOKEN")

    ## create a new droplet on your account
    droplet, action_id = droplet_api.create_single(req)

    # WORK WITH YOUR NEW DROPLET

    # delete the droplet when you're done
    droplet_api.delete(droplet.id)
    ```