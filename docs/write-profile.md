# SDK Write Profile v1.1

This profile tests portable SDK behavior for in-memory catalog authoring.
It is a behavioral contract, not a normative Portolan validator.

Round 1 targets Portolan 0.3.0 at commit
`f758c6e5ec05e411a19a276251bbbe3b8ba53916`.
The fixture source record is in `fixtures/writing/SOURCES.json`.

## Scope

The adapter imports a language-neutral catalog graph and calls the SDK authoring API.
The SDK returns a deterministic `WritePlan` with relative POSIX keys and UTF-8 content.
New catalog plans contain PUT operations only.

The plan has no destination and performs no I/O.
The caller decides whether and where to materialize it.
The profile does not inspect or copy geospatial asset bytes.

Cases W01–W15 cover root and nested catalogs, collections, items, assets,
documentation, unknown fields, deterministic serialization, and preflight errors.

Round 2 adds W16–W22 and R01–R04. These cases cover copy-on-write edits,
document and asset changes, output prefixes, explicit managed deletions, and round trips.
DELETE operations require `prior_managed_keys`; the planner never scans a destination.

Round 3 adds W23–W30 and R05–R07. These cases cover malformed metadata,
duplicate links, JSON value fidelity, href edge cases, larger graphs, repeated planning,
serialization failures, documentation preservation, and read-profile regression.

Version 1.1 adds W31–W36 and R08. These cases require the root catalog's own
`root` link, titles on generated `child` and `item` links, the GeoJSON media type
on generated `item` links, and copy-on-write documentation editing. A generated
item link uses the managed document's explicit `link_title` when the item has no
`properties.title`.

## Adapter request

The adapter receives one JSON object on standard input:

```json
{"protocol_version":"1","operation":"plan_write","input":{"spec_version":"0.3.0","documents":[]}}
```

Each document entry contains a logical `key` and a STAC `document` object.
A nested entry also identifies its `parent_key` and structural `relation`.
Documentation entries contain caller-supplied content and an owning document key.

## Adapter response

A successful response contains an ordered operation list:

```json
{"status":"ok","result":{"profile_version":"1","spec_version":"0.3.0","operations":[{"kind":"put","key":"catalog.json","content":"{}\n"}]}}
```

Operation keys must be unique, sorted, relative POSIX paths.
JSON operation content must decode to an object.
The adapter returns stable domain error codes for expected preflight failures.

## Run the profile

```bash
portolan-conformance run \
  --profile write \
  --adapter 'python tests/conformance_adapter.py' \
  --report write-profile-report.json
```

A pass applies only to the selected cases.
Use `rashid` to determine normative Portolan catalog conformance.
