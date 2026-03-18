# Autorest config

```yaml
title: DigitalOceanClient
namespace: pydo
python: true
black: true
output-folder: src/
verbose: true
version-tolerant: true
override-client-name: GeneratedClient

add-credential: true
credential-default-policy-type: BearerTokenCredentialPolicy
credential-scopes: https://api.digitalocean.com

directive:
  - from: openapi-document
    where: '$.components.parameters[*]'
    transform: >
      $["x-ms-parameter-location"] = "method";

  # Floating IP operations have been deprecated in favor of reserved IPs.
  - remove-operation: floatingIPs_get
  - remove-operation: floatingIPs_create
  - remove-operation: floatingIPs_list
  - remove-operation: floatingIPs_delete
  - remove-operation: floatingIPsAction_get
  - remove-operation: floatingIPsAction_list
  - remove-operation: floatingIPsAction_post

  - from: openapi-document
    where: '$.components.responses.unauthorized'
    transform: >
      $["x-ms-error-response"] = true;
  - from: openapi-document
    where: '$.components.responses.too_many_requests'
    transform: >
      $["x-ms-error-response"] = true;
  - from: openapi-document
    where: '$.components.responses.server_error'
    transform: >
      $["x-ms-error-response"] = true;
  - from: openapi-document
    where: '$.components.responses.unexpected_error'
    transform: >
      $["x-ms-error-response"] = true;
      
  - from: openapi-document
    where: '$..["log_line_prefix"]'
    transform: >
      $["x-ms-enum"] = {
        "name": "PostfixLogLinePrefix",
        "modelAsString": false,
        "values": [
          {
            "value": "pid=%p,user=%u,db=%d,app=%a,client=%h",
            "name": "First Option"
          },
          {
            "value": "%m [%p] %q[user=%u,db=%d,app=%a]",
            "name": "Second Option"
          },
          {
            "value": "%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h",
            "name": "Third Option"
          }
        ]
      };

  # Remove accept and content-type arguments from the app.Create method.
  - from: openapi-document
    where: '$.paths."/v2/apps".post'
    transform: >
      $["parameters"] = [];

  # Strip path-level and operation-level "servers" overrides from all paths.
  # Without this, Autorest generates a duplicate `endpoint` parameter in
  # GeneratedClient.__init__ (one per unique server URL), which is a Python
  # syntax error.  Runtime multi-base-URL routing is handled by
  # _BaseURLProxy in custom_extensions.py instead.
  - from: openapi-document
    where: '$.paths.*'
    transform: >
      delete $["servers"];
      for (const m of ["get","post","put","patch","delete","head","options"]) {
        if ($[m] && $[m].servers) { delete $[m].servers; }
      }
```
