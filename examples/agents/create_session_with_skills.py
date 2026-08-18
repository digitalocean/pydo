"""Create a session from a manifest that includes ``spec.skills``.

A skill is an inline Agent Skill in the ``SKILL.md`` shape: ``name`` and
``description``/``instructions`` are required, ``license``/``metadata`` and
``allowedTools`` are optional. Skills are advisory scoping only, not
enforcement — ``spec.permissions`` is still the real tool-call enforcement
surface.

There is no typed ``Skill`` model in pydo — like the rest of the manifest,
``spec.skills`` is authored as plain YAML and uploaded verbatim
(``Content-Type: application/x-yaml``); harness-api owns all parsing and
validation, including rejecting a ``spec.skills`` list that would encode too
large for the sandbox's ``HARNESS_SKILLS`` env var. That error surfaces as a
normal ``azure.core.exceptions.HttpResponseError`` with a readable message —
no special handling needed on the client side.

Required env:
  DIGITALOCEAN_TOKEN
  PYDO_AGENTS_ENDPOINT  (stage2: https://api.s2r1.internal.digitalocean.com)
"""

import json
import os

from azure.core.exceptions import HttpResponseError

from pydo import Client

manifest = """\
apiVersion: agents.digitalocean.com/v1alpha1
kind: Agent
metadata:
  name: harness-demo
spec:
  skills:
    - name: release-notes
      description: Draft release notes from a diff.
      instructions: |
        Summarize the diff in Keep a Changelog format.
        Group entries under Added/Changed/Fixed.
"""

client = Client(
    token=os.environ["DIGITALOCEAN_TOKEN"],
    agents_endpoint=os.environ.get("PYDO_AGENTS_ENDPOINT"),
)

try:
    resp = client.agents.sessions.create_from_manifest(manifest)
except HttpResponseError as err:
    print(f"session create failed: {err.message}")
    raise

print(json.dumps(resp, indent=2, default=str))
