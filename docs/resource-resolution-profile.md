# Resource Resolution Profile v1

This profile checks how an SDK retrieves metadata and resolves linked documents.
It does not validate Portolan metadata or fetch asset bytes.

The harness starts a local HTTP server for every run. The server provides stable redirects and error responses. Required CI does not use public services.

## Contract

The profile uses the existing Read Profile v1 adapter operations. It adds no public SDK API.

An implementation must:

- read a document through HTTP;
- resolve relative links against the final document URL after redirects;
- preserve query strings and fragments in resolved links;
- read percent-encoded paths and Unicode metadata;
- return `NOT_FOUND` for HTTP 404;
- return `READ_ERROR` for HTTP 403 and HTTP 500;
- return `INVALID_JSON` for malformed JSON.
- return `INVALID_JSON` for a truncated JSON response;
- read valid JSON when the server reports `text/plain`;
- traverse a finite chain of eight linked catalogs;
- keep the fixture HTTP root isolated from encoded parent-path requests.

Run the profile with:

```bash
portolan-conformance run \
  --profile resource-resolution \
  --adapter '<SDK adapter command>' \
  --report resource-resolution-report.json
```

## Limits

Version 1 provides basic coverage for delayed responses, truncated JSON, media types,
finite depth, and fixture-server containment. It does not require a shared SDK timeout
option, a universal depth limit, strict media-type rejection, or a filesystem sandbox.
Those behaviors need explicit cross-language API decisions.
