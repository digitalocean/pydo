# AGENTS.md

`pydo` is the official Python client for the DigitalOcean API. Most of it is generated
with [AutoRest](https://github.com/Azure/autorest) from the
[DigitalOcean OpenAPI spec](https://github.com/digitalocean/openapi), with hand-written
customizations layered on top.

## Generated code: do not hand-edit

`make clean` deletes everything under `src/pydo/` except the hand-written files listed
below, and `make generate` recreates it. Edits to generated files are lost on the next
regeneration. Generated output includes:

- `src/pydo/_client.py`, `_configuration.py`, `_serialization.py`, `_vendor.py`,
  `_version.py`, `operations/_operations.py`, and their `aio/` counterparts.
- `src/pydo/resources/`, `src/pydo/types/`, `src/pydo/inference/`, written by
  `scripts/generate_inference_resources.py` and `scripts/generate_inference_types.py`.
- `docs/source/`, written by `make generate-docs`.

Where changes go instead:

- API shape (paths, parameters, schemas, descriptions): change the spec in
  `digitalocean/openapi`. The `python-client-gen` workflow then opens a
  `[bot] ... Re-Generated From digitalocean/openapi@<sha>` PR here and updates
  `DO_OPENAPI_COMMIT_SHA.txt`.
- Generator settings and spec transforms: `client_gen_config.md` (AutoRest config and directives).
- Client behavior: `_patch.py` files (AutoRest customization hook) and `custom_*.py`.
- Hand-written modules, preserved by `make clean`: `src/pydo/agents/`,
  `src/pydo/aio/agents/`, `src/pydo/gateway/`, `src/pydo/aio/gateway/`,
  `src/pydo/action_gateway/`, `src/pydo/exceptions.py`.

## Setup and commands

Requires Python 3.8+ and [Poetry](https://python-poetry.org/). CI uses Poetry 1.6.1
and tests on Python 3.8, 3.9 and 3.10.

```sh
make install                           # poetry install -E aio
make test-mocked                       # tests/mocked, no network; runs in CI
PYLINT_ARGS=--disable=fixme make lint-tests   # black --check and pylint on tests/, as CI runs it
poetry run pytest tests/agents tests/gateway  # tests for the hand-written modules
make generate                          # full regeneration; needs npm (AutoRest) and downloads the spec
```

`make test-integration` creates real resources and needs `DIGITALOCEAN_TOKEN`. Do not
run it unless asked. CI also runs markdownlint on `*.md` (config in `.markdownlint.yml`).

## Conventions

- Format with black. Generated code is reformatted by `make generate`.
- Generated operations in `operations/` take and return JSON dicts, not model classes.
- HTTP errors surface as `azure.core.exceptions.HttpResponseError`, re-exported from
  `pydo.exceptions` so callers do not import azure packages directly.
- Mocked tests use the `responses` library with the `mock_client` / `mock_aio_client`
  fixtures from `tests/mocked/conftest.py`. One `test_<resource>.py` per API area.
- Releases bump `pyproject.toml` and `src/pydo/_version.py` in a separate PR
  (see `CONTRIBUTING.md`). Do not bump the version in a feature or fix PR.

## Docs

- DigitalOcean API reference: <https://docs.digitalocean.com/reference/api/>
- PyDo docs: <https://docs.digitalocean.com/reference/pydo/>
