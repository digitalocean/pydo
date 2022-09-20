
# The DigitalOcean Python library

`digitalocean-python-client` is the official python client library that allows
python developers to interact with and manage their DigitalOcean account
resources through a python abstraction layer on top of the raw
[DigitalOcean API HTTP Interface](https://developers.digitalocean.com/documentation/v2/). 

A top priority of this project is to ensure the client abides by the API
contract. Therefore, the client itself wraps a generated client based
on the [DigitalOcean OpenAPI Specification](https://github.com/digitalocean/openapi).


# Getting Started With the Client
## Prerequisites

* Python version: >= 3.7.2

## Installation
To install from pip:

    pip install git+https://github.com/digitalocean/digitalocean-client-python.git

or, if repo is cloned locally:

    pip install /<PATH>/<TO>/digitalocean-client-python

To install from source:

    make install

## DigitalOcean API
To support all of DigitalOcean's HTTP APIs, a generated library is available which will expose all the endpoints:  [digitalocean-api-client-python](https://github.com/digitalocean/digitalocean-client-python/tree/main/src/digitalocean).

Find below a working example for GET a ssh_key ([per this http request](https://docs.digitalocean.com/reference/api/api-reference/#operation/sshKeys_list)) and printing the ID associated with the ssh key. If you'd like to try out this quick example, you can follow [these instructions](https://docs.digitalocean.com/products/droplets/how-to/add-ssh-keys/) to add ssh keys to your DO account. 
```python
from digitalocean import Client

client = Client(token="<YOUR-API-TOKEN>")  

ssh_keys_resp = client.ssh_keys.list()
for k in ssh_keys_resp["ssh_keys"]:
    print(f"ID: {k['id']}, NAME: {k['name']}, FINGERPRINT: {k['fingerprint']}")
```

The above code snippet should output the following:
```
ID: 123456, NAME: my_test_ssh_key, FINGERPRINT: 5c:74:7e:60:28:69:34:ca:dd:74:67:c3:f3:00:7f:fe
ID: 123457, NAME: my_prod_ssh_key, FINGERPRINT: eb:76:c7:2a:d3:3e:80:5d:ef:2e:ca:86:d7:79:94:0d
```
**Consult the full list of supported DigitalOcean API endpoints in [the DigitalOcean Python Client documentation]().**

**Note**: More working examples can be found [here](https://github.com/digitalocean/digitalocean-client-python/tree/main/examples).

##### Pagination Example
Below is an example on handling pagination. One must parse the URL to find the next page.
```
        resp = self.client.ssh_keys.list(per_page=50, page=page)
        pages = resp.links.pages
            if 'next' in pages.keys():
                parsed_url = urlparse(pages['next'])
                page = parse_qs(parsed_url.query)['page'][0]
            else:
                paginated = False
```
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

Instructions on creating a DO token can be found 
[here](https://docs.digitalocean.com/reference/api/create-personal-access-token/)

Instructions on creating an SSH Key can be found
[here](https://docs.digitalocean.com/products/droplets/how-to/add-ssh-keys/)

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
    * Can be installed using something like 
      [pyenv](https://github.com/pyenv/pyenv)
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
that has `environ.get()` can be overwritten by setting the respective environment
variable.

## Client customization

Several client settings can be customized to suite the applicaiton.
The configuration options available are currently listed in the 
[generator's sdk documentation](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/core/azure-core/README.md#configurations). As this client evolves, we will include these details in our
documentation.

There are several examples in the 
[examples/customize_client_settings](examples/customize_client_settings)
directory that help illustrate how to easily customize the client
configuration.

## Docker

The included Dockerfile is a developler convenience to test the package in
isolation.

To use it, first build the image. Run: 

    docker build -t digitalocean-client-python:dev .

### Use the interactive python shell

Open the python shell:

    docker run -it --rm --name do-client-python digitalocean-client-python:dev python

The above will launch an interactive python shell and display the following:

    Skipping virtualenv creation, as specified in config file.
    Python 3.10.5 | packaged by conda-forge | (main, Jun 14 2022, 07:06:46) [GCC 10.3.0] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>>

From here you can use the client interactively:

    >>> from digitalocean import Client
    >>> c = Client("<YOUR_API_TOKEN>")
    >>> c.droplets.get()

### Run the tests

Alternatively, the tests can be run by attaching the tests as a volume and
running pytest directly.

Run: 

    docker run -it --rm --name pydo -v $PWD/tests:/tests digitalocean-client-python:dev pytest tests/mocked


### Known Issues
This selection lists the known issues of the client generator. 
##### `kubernetes.get_kubeconfig` Does not serialize response content
In the generated python client, when calling client.kubernetes.get_kubeconfig(clust_id), the deserialization logic raises an error when the response content-type is applicaiton/yaml. We need to determine if the spec/schema can be configured such that the generator results in functions that properly handle the content. We will likely need to report the issue upstream to request support for the content-type.

##### `invoices.get_pdf_by_uuid(invoice_uuid=invoice_uuid_param)` Does not return PDF
In the generated python client, when calling  `invoices.get_pdf_by_uuid`, the response returns a  Iterator[bytes] that does not format correctly into a PDF.

##### Getting documentation via cli "help(<client function>)"
Currently, calling the "help(<client function>)" includes the API documentation for the respective operation which is substantial and can be confusing in the context of this client. 


## Roadmap
This section lists short-term and long-term goals for the project.
**Note**: These are goals, not necessarily commitments. The sections are not intended to represent exclusive focus during these terms. 

Short term:
> Usability, stability, and marketing.

Short term, we are focused on improving usability and user productivity (part of this is getting the word out).
* Documentation
    * Support an automated process for creating comprehensive documentation that explains working of codes
    * Support a clean cli `help(<client function>)` documentation solution
* Release stability
    * define release strategy
    * pip release

Long term:
> Model support, expand on supporting functions 
* The client currently inputs and outputs JSON dictionaries. Adding models would unlock features such as typing and validation. 
* Add supporting functions to elevate customer experience (i.e. adding a funtion that surfaces IP address for a Droplet)
