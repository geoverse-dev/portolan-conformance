# SDK Read Profile v1 — implementation specification

## Mission

Implement a **read-only** Portolan metadata client in `portolan-python` and `portolan-java`, plus a small **test adapter** in each SDK repository. Do not copy or depend on `portolan-cli`, do not modify `portolan-spec`, do not generate catalogs or process geospatial asset bytes. The SDK should read static STAC 1.1 catalogs following Portolan conventions. Spec: https://github.com/portolan-sdi/portolan-spec (pin a commit in integration PR). This is an SDK behavior profile, **not** a new normative Portolan standard.

## Requirements for the bot

1. Inspect the current SDK's existing API and tests. Reuse public model objects and transport abstractions where possible; do not break existing users.
2. Implement read-only opening of `file://` and `https://` STAC JSON entrypoints; optionally accept a local filesystem path as a convenience API (adapter always sends URI). Do not require `.portolan/config.yaml` or `versions.json`.
3. Support Catalog, Collection and Feature (Item), including nested catalogs, collection-level assets, item-level assets, and empty item lists.
4. Preserve raw JSON and extension fields: `stac_extensions`, namespaced metadata, `providers`, `extent`, `properties`, `alternate`, `file:size`, etc. Do not silently discard unknown fields. Preserve Unicode, JSON null and numeric types.
5. Navigate via **STAC links**, not directory scanning. Resolve relative links against the containing JSON document URI. Do not assume collection IDs equal directory names or flatten nested paths.
6. Implement traversal with cycle protection and deterministic ordering. `collections` recursively traverses `child` links through Catalogs, returns Collections, never follows `alternate` as containment; `children` returns direct child links; `items` returns direct `item` links of the selected Collection. Do not infer missing links.
7. Resolve asset hrefs against the containing document URI without downloading asset bytes. Preserve original href separately. For remote HTTPS, preserve query strings/fragments. Preserve non-HTTP absolute schemes such as `s3://` rather than rewriting them.
8. Errors: missing local/HTTP 404 -> `NOT_FOUND`; invalid JSON -> `INVALID_JSON`; malformed request -> `INVALID_REQUEST`; unsupported operation -> `UNSUPPORTED_OPERATION`; inaccessible/failed remote resource -> `READ_ERROR`. Error codes must be stable, messages optional. Avoid swallowing exceptions into empty lists.
9. Keep SDK API idiomatic for its language. The **adapter** translates it to the protocol below; do not force protocol names into the public SDK API.
10. No runtime dependency on `portolan-conformance` or `portolan-cli` inside the SDK library. Test adapter may invoke the conformance CLI as a dev/test dependency.

## Adapter protocol v1

Adapter lives in each SDK repository, is executable from a command line, reads one UTF-8 JSON request from stdin and writes one JSON response to stdout. Exit 0 for expected domain errors; nonzero for crash. No extra stdout, debug output goes to stderr. One invocation per request.

Request:

```json
{"protocol_version":"1","operation":"inspect","uri":"file:///tmp/catalog.json"}
```

Operations and **exact** result structures:

- `document`: `{ "document": object }` containing the complete decoded STAC JSON, preserving all nested properties and unknown fields. No asset data fetch.
- `inspect`: `{ "type": "Catalog|Collection|Feature", "id": string, "title": string|null, "description": string|null, "stac_version": string|null, "stac_extensions": array }`.
- `children`: `{ "entries": [{ "id": string, "uri": absolute_URI }] }` from direct `child` links. Sort by `(id, uri)`.
- `collections`: same entries schema; recursively follow `child` links through Catalog nodes and return Collection nodes; sort by `(id, uri)`; cycle-safe.
- `items`: same entries schema, direct `item` links; sort by `(id, uri)`.
- `assets`: `{ "entries": [{ "key": string, "href": string, "resolved_href": absolute_URI, "type": string|null, "roles": array, "title": string|null, "description": string|null, "extra_fields": object }] }`; sort by `key`. `extra_fields` contains all unrecognized asset fields, including extension-prefixed fields and `alternate`.
- `links`: `{ "entries": [{ "rel": string, "href": string, "resolved_href": absolute_URI, "type": string|null, "title": string|null, "extra_fields": object }] }`; sort by `(rel, href)`; preserve other link fields in `extra_fields`.

Success: `{ "status": "ok", "result": object }`.
Error: `{ "status": "error", "error": { "code": "NOT_FOUND|INVALID_JSON|INVALID_REQUEST|UNSUPPORTED_OPERATION|READ_ERROR|UNSUPPORTED_PROTOCOL" } }`.

All seven operations are **mandatory** for Read Profile v1. `UNSUPPORTED` is **not** a passing substitute. A successful `inspect` does not assert the input is spec-conformant: it only reads it. Do not add validation requirements not in the profile.

**URI semantics**: use RFC 3986-style relative reference resolution; `file://` absolute URI results for local fixtures; no filesystem paths in response. Beware Java `URI.resolve` with `../`, and URL percent encoding. Preserve arrays as authored unless an operation explicitly specifies sorting. `collections` and `children` use linked targets' `id`, not link title. Avoid dereferencing `data` assets during metadata reads.

## How to integrate

1. Clone this repo and install it as a development tool, or install its pinned release.
2. Add a test adapter in the SDK repository (`tests/conformance_adapter.py` for Python, `src/test/...` or dedicated `conformance-adapter` entrypoint for Java). The Java adapter should build with Maven/Gradle and run via a deterministic command.
3. Run `portolan-conformance run --adapter '<your command>' --report report.json` from the conformance checkout; failures are nonzero.
4. Run the SDK's unit tests and ensure no new runtime dependencies on CLI or conformance.
5. CI must pin the conformance repository revision; build the SDK before running the suite; upload report as artifact.
6. Do not hardcode fixture names, case IDs or expected answers in the adapter. It must call the actual SDK APIs.

## Coverage expansion roadmap (add fixtures + expectations before claiming full coverage)

- Core: Unicode, missing optional fields, nulls, nested catalogs, single-file collection assets, multi-item collections, duplicate IDs in different subtrees, collection IDs with POSIX paths.
- Links: `self`, `root`, `parent`, `collection`, `item`, `child`, `describedby`, `agents`, `alternate`, absolute/relative URLs, `../`, URL query/fragment, percent-encoding, cycles, external links.
- Assets: roles, media types (GeoParquet, COG, PMTiles, COPC, Parquet), collection vs item, alternate schemes, namespaced extensions, arbitrary extra fields, zero-byte metadata not downloaded.
- Metadata: spatial/temporal extents, null geometry, 3D bbox, STAC and Portolan version declarations, providers, licenses, language trees, unknown extension fields.
- Errors: 404, permission denied, malformed JSON, malformed STAC shape (SDK error policy), timeouts, 500, redirects, invalid URI, cycle behavior.
- HTTP: deterministic local HTTP server with nested paths, redirects, percent-encoding, query, HTTP error codes; avoid live internet in required CI.
- Scale: deep catalog, 100+ links, repeated references, bounded concurrency, no infinite recursion.
- Official real-world catalogs: pin a `portolan-spec` commit and known valid fixtures; use Rashid externally to prevalidate fixtures, **not** as a runtime dependency and **not** as a duplicate validator.

## Acceptance criteria

- SDK opens all provided local fixtures and returns the exact protocol outputs.
- All `portolan-conformance` cases pass, including error cases.
- SDK public API supports local and HTTPS read-only metadata access without CLI state.
- Tests prove adapter delegates to SDK (no fixture-specific branching).
- SDK can be used without the conformance harness installed.
- No writing, publishing, conversion, data byte validation or schema validation is added.

## Non-goals

No catalog creation, mutation, asset conversion, checksum verification, STAC/Portolan normative validation, `rashid` reimplementation, `portolan-cli` dependency, remote catalog publishing, or SDK cross-language IPC in production.
