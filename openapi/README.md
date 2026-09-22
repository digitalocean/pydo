# Action Gateway OpenAPI patch

`action-gateway-toolbelts.patch` adds the public Toolbelts API used to generate
the synchronous and asynchronous `client.toolbelts` operations.

The patch is based on the OpenAPI revision recorded in
`DO_OPENAPI_COMMIT_SHA.txt`. To regenerate the SDK:

```shell
git -C /path/to/openapi checkout "$(cat DO_OPENAPI_COMMIT_SHA.txt)"
git -C /path/to/openapi apply "$PWD/openapi/action-gateway-toolbelts.patch"
make -C /path/to/openapi bundle \
  BUNDLE_PATH="$PWD/DigitalOcean-public.v2.yaml"
SPEC_FILE="$PWD/DigitalOcean-public.v2.yaml" make generate
```

Submit the same source changes to the DigitalOcean OpenAPI repository. Once
they are published and `DO_OPENAPI_COMMIT_SHA.txt` advances to include them,
remove this transitional patch.
