# Contributing to the DO Python Client
First: if you're unsure or afraid of anything, just ask or submit the issue or pull request anyways. You won't be yelled at for giving your best effort. The worst that can happen is that you'll be politely asked to change something. We appreciate all contributions! 

## A Little Bit of Context...

The DigitalOcean Python client is generated using [AutoRest](https://github.com/Azure/autorest). The AutoRest tool generates client libraries for accessing RESTful web services. Input to AutoRest is a spec that describes the DigitalOcean REST API using the OpenAPI 3.0 Specification format. The spec can be found [here](https://github.com/digitalocean/openapi). AutoRest allows customizations to be made on top the generated code. This allows us to mold the raw generated client to be more easier to use and more user friendly. This guide will show you 1) how to generate the client using Autorest and 2) how to add customizations on top of the generated code.


## Prerequisites

* Python version: >= 3.9 (it's highly recommended to use a python version management tool)
* [poetry](https://python-poetry.org/): python packaging and dependency management
* [AutoRest](https://github.com/Azure/autorest): The tool that generates the client libraries for accessing RESTful web services.

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
    git clone git@github.com:digitalocean/pydo.git
    cd pydo
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

## Generating the Client Using AutoRest
1. Install AutoRest using the documentation [here](https://github.com/Azure/autorest/blob/main/docs/install/readme.md)
2.TODO: Insert instructions on generating the client


 ## Customizing the Client Using Patch Files
This guide will introduce how to add customizations to the generated client.

### Key Concept: _patch.py

The `_patch.py` files at each level of the subfolders will be the entry point to customize the generated code.

For example, if you want to override a model, you will use the `_patch.py` file at the `models` level of the
generated code to override.

The main flow of the `_patch.py` file will be:

1. Import the generated object you wish to override.
2. Inherit from the generated object, and override its behavior with your desired code functionality
3. Include the name of your customized object in the `__all__` of the `_patch.py` file

If you find that your customizations for an object are not being called, please make sure that
your customized object is included in the `__all__` of your `_patch.py` file.

## Examples

- [Change Model Behavior](#change-model-behavior)
- [Change Operation Behavior](#change-operation-behavior)
- [Overload an Operation](#overload-an-operation)
- [Change Client Behavior](#change-client-behavior)
- [Add a Client Method](#add-a-client-method)

### Change Model Behavior

To override model behavior, you will work with the `_patch.py` file in the `models` folder of your generated code.

In the following example, we override the generated `Model`'s `input` parameter to accept both `str` and `datetime`,
instead of just `str`.

In this `_patch.py` file:

```
pydo
│   README.md
│
└───src
    └───pydo
        └───sdk
        └───operations
        │   _models.py # where the generated models are
        |   _patch.py # where we customize the models code
```

```python
import datetime
from typing import Union
from ._models import Model as ModelGenerated

class Model(ModelGenerated):
    """ DO Customized Code:
        Added override the generated Model's input parameter to accept both str and datetime, instead of just str
    """
  def __init__(self, input: Union[str, datetime.datetime]):
    super().__init__(
      input=input.strftime("%d-%b-%Y") if isinstance(input, datetime.datetime) else input
    )

__all__ = ["Model"]
```

> Note: Please add comments to describe the reason for the customization

### Change Operation Behavior

To change an operation, you will import the generated operation group the operation is on. Then you can inherit
from the generated operation group and modify the behavior of the operation.

In the following example, the generated operation takes in a datetime input, and returns a datetime response.
We want to also allow users to input strings, and return a string response if users inputted a string.

In this `_patch.py` file:

```
pydo
│   README.md
│
└───src
    └───pydo
        └───sdk
        └───operations
        │   _operations.py # where the generated operations are
        |   _patch.py # where we customize the operations code
```

```python
from typing import Union
import datetime
from ._operations import OperationGroup as OperationGroupGenerated

class OperationGroup(OperationGroupGenerated):
    """ DO Customized Code:
        Added to also allow users to input strings, and return a string response if users inputted a string.
    """
  def operation(self, input: Union[str, datetime.datetime]):
    response: datetime.datetime = super().operation(
        datetime.datetime.strptime(input, '%b %d %Y') if isinstance(input, str) else input
    )
    return response.strftime("%d-%b-%Y") if isinstance(input, str) else response


__all__ = ["OperationGroup"]
```
> Note: Please add comments to describe the reason for the customization


### Overload an Operation

You can also easily overload generated operations. For example, if you want users to be able to pass in the body parameter
as a positional-only single dictionary, or as splatted keyword arguments, you can inherit and override the operation on the operation group
in the `_patch.py` file in the `operations` subfolders.

In this `_patch.py` file:

```
pydo
│   README.md
│
└───src
    └───pydo
        └───sdk
        └───operations
        │   _operations.py # where the generated operations are
        |   _patch.py # where we customize the operations code
```

```python
from typing import overload, Dict, Any
from ._operations import OperationGroup as OperationGroupGenerated

class OperationGroup(OperationGroupGenerated):
    """ DO Customized Code:
        Added to allow users to be able to pass in the body parameter as a positional-only single dictionary, or as splatted keyword arguments
    """
    @overload
    def operation(self, body: Dict[str, Any], /, **kwargs: Any):
        """Pass in the body as a positional only parameter."""

    @overload
    def operation(self, *, foo: str, bar: str, **kwargs: Any):
        """Pass in the body as splatted keyword only arguments."""

    def operation(self, *args, **kwargs):
        """Base operation for the two overloads"""
        if not args:
            args.append({"foo": kwargs.pop("foo"), "bar": kwargs.pop("bar")})
        return super().operation(*args, **kwargs)

__all__ = ["OperationGroup"]
```

> Note: Please add comments to describe the reason for the customization


### Change Client Behavior

In this example, we change the default authentication policy for a client.

In this `_patch.py` file:

```
pydo
│   README.md
│
└───src
    └───pydo
        └───sdk
        │   _service_client.py # where the generated service client is
        |   _patch.py # where we customize the client code
        └───operations
        └───models
```

```python
from ._service_client import ServiceClient as ServiceClientGenerated
from azure.core.pipeline import PipelineRequest
from azure.core.pipeline.policies import SansIOHTTPPolicy

class MyAuthenticationPolicy(SansIOHTTPPolicy):
    def __init__(self, key: str):
        self.key = key

    def on_request(self, request: PipelineRequest):
        request.http_request.headers["Authorization"] = f"My key is {self.key}"
        return super().on_request(request)

class ServiceClient(ServiceClientGenerated):
    """ DO Customized Code:
        Change the default authentication policy for a client.
    """
    def __init__(self, endpoint: str, credential: str, **kwargs):
        super().__init__(
            endpoint=endpoint,
            credential=credential,
            authentication_policy=kwargs.pop("authentication_policy", MyAuthenticationPolicy(credential)),
            **kwargs
        )

__all__ = ["ServiceClient"]
```

> Note: Please add comments to describe the reason for the customization


### Add a Client Method

Similar to models and operations, you can override client behavior in a `_patch.py` file, this time
at the root of the sdk.

Here, we will be adding an alternate form of authentication on the client, class method `from_connection_string`.

In this `_patch.py` file:

```
pydo
│   README.md
│
└───src
    └───pydo
        └───sdk
        │   _service_client.py # where the generated service client is
        |   _patch.py # where we customize the client code
        └───operations
        └───models
```

```python
from typing import Any
from azure.core.credentials import AzureKeyCredential
from ._service_client import ServiceClient as ServiceClientGenerated

class ServiceClient(ServiceClientGenerated):
    """ DO Customized Code:
        Adding an alternate form of authentication on the client, class method from_connection_string.
    """
    @classmethod
    def from_connection_string(cls, connection_string: str, **kwargs: Any):
        parsed_connection_string = _parse_connection_string(connection_string) # parsing function you've defined
        return cls(
            credential=AzureKeyCredential(parsed_connection_string.pop("accesskey")),
            endpoint=parsed_connection_string.pop("endpoint")
        )

__all__ = ["ServiceClient"]
```
 
 > Note: Please add comments to describe the reason for the customization

 
 # Create a Pull Request
 Voila! Create a Pull Request and a member from our team will review it.