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
* Automate packaging and publishing to pipy.
* Add installation instructions
* Add usage instructions

# Contributing

Visit our [Contribuing Guide](CONTRIBUTING.md) for more information on getting involved in developing this client.

## Local generation

Sometimes you want to make changes to the client configurations or customizations and test them locally. Everything you need to do this is in the Makefile. Below will provide instructions on how to generate the DO python client locally:

First, you'll download DO's latest Openapi 3.0 Spec using the following Make command:
```
make download-spec
```

Then, you'll actually generate the client with this Make command:
```
make autorest-python
```

To test the client you just generated, we have included a POC that creates a Droplet and Attaches a Volume to the Droplet. Before you run the script, you'll need the following exported variables: 
```
export DO_TOKEN=<INSERT-YOUR-DO-TOKEN> 
export SSH_KEY_NAME=<INSERT-YOUR-SSH_KEY_NAME>       
```

Instructions on creating a DO token can be found [here](https://docs.digitalocean.com/reference/api/create-personal-access-token/)

Instructions on creating an SSH Key can be found [here](https://docs.digitalocean.com/products/droplets/how-to/add-ssh-keys/)

You are ready to run the script. First, `cd tests` and then run the following:
> ** Running the following Python script will create billed resources in your account **
```
python3 poc_droplets_volumes_sshkeys.py
```