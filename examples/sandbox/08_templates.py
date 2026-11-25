"""List your templates; optionally build one from a container image.

    python examples/sandbox/08_templates.py
    TEMPLATE_IMAGE=registry.example.com/team/image:tag python examples/sandbox/08_templates.py

You should see your custom templates (the built-in `coding-base` is not listed).
With TEMPLATE_IMAGE set, the script builds a template, runs one command in a
sandbox made from it, then deletes the sandbox and the template.

Needs DIGITALOCEAN_ACCESS_TOKEN. Set DIGITALOCEAN_API_URL to use another API address.
"""

import os
import time

from pydo import Sandbox
from pydo.sandbox import Template

templates = list(Template.list())
print(f"{len(templates)} custom template(s)")
for t in templates:
    print(" ", t.template_id, t.name, t.status)

image = os.environ.get("TEMPLATE_IMAGE")
if not image:
    print(
        "\nTo build a template, set TEMPLATE_IMAGE=<registry/repository:tag> and run again."
    )
else:
    template = Template.create(name=f"example-{int(time.time())}", source_oci_ref=image)
    try:
        print("\nbuilding", template.template_id, template.status)
        template.wait_until_ready()  # a build can take a few minutes
        print("ready   :", template.status)
        with Sandbox.create(template=template.name) as sbx:
            print("from it :", sbx.exec("echo built from my image").stdout.strip())
    finally:
        print("template deleted:", template.delete())
        template.close()
