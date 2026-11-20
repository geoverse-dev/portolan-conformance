# portolan-conformance

Behavioral contracts for native Portolan SDKs in Python and Java.

This repository is **not** a Portolan validator and **does not depend on portolan-cli**.
The normative specification is external: https://github.com/portolan-sdi/portolan-spec.
`rashid` is the external catalog validator; it is not a runtime dependency here.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
pytest -q
portolan-conformance run --adapter 'python -m portolan_conformance.reference_adapter' --report report.json
```

With `uv` installed, run all repository checks without activating an environment:

```bash
make check
```

The included `reference_adapter` is a **harness self-test only** and is not an SDK or normative oracle. It supports local fixtures only. Actual SDK adapters belong in their own SDK repositories.

## Adapter contract

One process per request; a single UTF-8 JSON object on stdin and a single JSON object on stdout; diagnostic logs on stderr; exit code 0 for handled domain errors. Example request:

```json
{"protocol_version":"1","operation":"inspect","uri":"file:///tmp/catalog.json"}
```

Success: `{"status":"ok","result":{...}}`. Domain error: `{"status":"error","error":{"code":"NOT_FOUND"}}`.

All operations and field schemas are defined in [SDK Read Profile v1](docs/sdk-implementation-spec.md). Array ordering rules are explicit; no undocumented normalization.

The [Metadata Validation Profile](docs/metadata-validation-profile.md) defines a separate metadata-only contract.
It covers version-specific Portolan 0.2.0 and 0.3.0 behavior.

[Known SDKs](docs/known-sdks.md) lists current implementations and their conformance commands.

## Scope and limitations

The shipped cases cover a useful **metadata-only baseline**, not every possible spec variant. Some fixtures intentionally reference nonexistent data files: this is fine for SDK reading behavior but does not make the fixtures valid published Portolan datasets. The fixture adapter does not fetch assets. Expand the matrix with version-pinned, validator-checked real catalogs and local HTTP tests before calling the SDKs fully conformant.

Do not claim `PASS` on the baseline proves complete Portolan spec compliance. The report concerns only the selected SDK behavior cases.
