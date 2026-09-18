.. PyDo documentation master file.
.. For a guide on reStructuredText, see: https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html

###################################
Welcome to PyDo's Documentation!
###################################

.. module:: pydo

**PyDo** is the official Python client library for the `DigitalOcean API v2 <https://docs.digitalocean.com/reference/api/api-reference/>`_. It allows you to manage your DigitalOcean resources, like Droplets, Volumes, and SSH Keys, directly from your Python code.

This documentation will guide you through installation, authentication, and basic usage of the library.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api_reference

.. note::

   This project is actively developed. We encourage you to open an `issue on GitHub <https://github.com/digitalocean/pydo/issues>`_ if you encounter any problems or have suggestions for improvement!

***************
Getting Started
***************

First, let's get the library installed and configured.

Installation
============

PyDo requires Python 3.7 or newer. You can install it from PyPI using pip:

.. code-block:: bash

    pip install pydo

Authentication
==============

To use the DigitalOcean API, you need a personal access token.

1.  **Generate a Token**: You can generate a token from the `Applications & API page <https://cloud.digitalocean.com/account/api/tokens>`_ in the DigitalOcean control panel.
2.  **Set the Token**: You must initialize the ``Client`` with your token. The recommended way is to set it as an environment variable:

    .. code-block:: bash

        export DIGITALOCEAN_TOKEN="your_api_token_here"

    The client will automatically detect and use this variable.

    Alternatively, you can pass the token directly when creating the client instance. **Be careful not to expose this token in your source code.**

    .. code-block:: python

        from pydo import Client

        # Initialize by reading the environment variable (recommended)
        client = Client()

        # Or, initialize by passing the token directly
        # client = Client(token="your_api_token_here")

.. autofunction:: pydo.Client

***********************
Quickstart: List SSH Keys
***********************

Here is a complete example to list all the SSH keys in your DigitalOcean account.

.. code-block:: python

    import os
    from pydo import Client

    # Assumes your token is set as an environment variable
    # DIGITALOCEAN_TOKEN
    client = Client()

    try:
        ssh_keys_resp = client.ssh_keys.list()
        print("Successfully fetched SSH keys:")
        for key in ssh_keys_resp["ssh_keys"]:
            print(f"- ID: {key['id']}, Name: {key['name']}")
            # Example output:
            # - ID: 123456, Name: my_test_ssh_key

    except Exception as e:
        print(f"An error occurred: {e}")

For a more comprehensive example that demonstrates creating Droplets and managing Volumes, see our `end-to-end example script <https://github.com/digitalocean/pydo/blob/main/examples/poc_droplets_volumes_sshkeys.py>`_.

*************
Core Concepts
*************

Handling Pagination
===================

API requests that return a list of items are paginated. By default, 25 items are returned per page. You can check the ``links`` attribute in the response to see if there are more pages.

Here's how to iterate through all pages of your SSH keys:

.. code-block:: python

    from urllib.parse import urlparse, parse_qs

    def get_all_ssh_keys(client: Client):
        all_keys = []
        page = 1
        paginated = True

        while paginated:
            resp = client.ssh_keys.list(per_page=50, page=page)
            all_keys.extend(resp["ssh_keys"])

            # Check if a 'next' page URL exists in the response links
            if 'next' in resp["links"]["pages"]:
                next_url = resp["links"]["pages"]['next']
                # Extract the page number from the URL for the next request
                page = parse_qs(urlparse(next_url).query)['page'][0]
            else:
                paginated = False

        return all_keys

    # Usage:
    # client = Client()
    # all_my_keys = get_all_ssh_keys(client)
    # print(f"Found {len(all_my_keys)} total keys.")


*************
API Reference
*************

For a detailed list of all available operations and their parameters, please see the auto-generated API reference.

.. This will be a separate page, e.g., `api_reference.rst`
.. automodule:: pydo.operations
   :members:
   :undoc-members:
   :show-inheritance:
