.. digitalocean documentation master file, created by
   sphinx-quickstart on Fri Sep 30 15:26:48 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

#########################################
:mod:`digitalocean` --- DigitalOcean Python library
#########################################

.. module:: digitalocean

:mod:`digitalocean` is a Python client library for DigitalOceans's `HTTP API
<https://docs.digitalocean.com/reference/api/api-reference/>`_.

Installation
============

Install from PyPI::

    pip install digitalocean


Initialization
==============

:mod:`digitalocean` must be initialized with :meth:`digitalocean.client`. A
DigitalOcean API Token is required. The token can be passed explicitly to :meth:`digitalocean.client` or defined as environment variables
``DIGITALOCEAN_TOKEN``.

Here's an example of initializing the DigitalOcean Python Client::

   from digitalocean import Client

   client = Client(token="<DIGITALOCEAN_TOKEN>")  

.. autofunction:: digitalocean.Client

Example
===========
Find below a working example for GET a ssh_key (per this http request) and printing the ID associated with the ssh key. If you'd like to try out this quick example, you can follow these instructions to add ssh keys to your DO account::

   from digitalocean import Client

   client = Client(token="<YOUR-API-TOKEN>")  

   ssh_keys_resp = client.ssh_keys.list()
   for k in ssh_keys_resp["ssh_keys"]:
      print(f"ID: {k['id']}, NAME: {k['name']}, FINGERPRINT: {k['fingerprint']}")

The above code snippet should output the following::

   ID: 123456, NAME: my_test_ssh_key, FINGERPRINT: 5c:74:7e:60:28:69:34:ca:dd:74:67:c3:f3:00:7f:fe
   ID: 123457, NAME: my_prod_ssh_key, FINGERPRINT: eb:76:c7:2a:d3:3e:80:5d:ef:2e:ca:86:d7:79:94:0d

You can find a more thorough example of using the DigitalOcean Python client `here
<https://github.com/digitalocean/digitalocean-client-python/blob/main/examples/poc_droplets_volumes_sshkeys.py>`_.
The example walks through the process of creating a droplet with a specified ssh key, creating a volume, and then attaching the volume to the droplet. 

Pagination
~~~~~~~~~~~
Below is an example on handling pagination. One must parse the URL to find the next page::

   resp = self.client.ssh_keys.list(per_page=50, page=page)
   pages = resp.links.pages
      if 'next' in pages.keys():
            parsed_url = urlparse(pages['next'])
            page = parse_qs(parsed_url.query)['page'][0]
      else:
            paginated = False


digitalocean.Client Usage
===========

.. automodule:: digitalocean.operations
   :members:
   :undoc-members:
   :show-inheritance: