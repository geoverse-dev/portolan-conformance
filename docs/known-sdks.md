# Known SDKs

Each SDK owns its public API and conformance adapter.
The adapter delegates requests to the SDK implementation.
It must not contain fixture-specific results.

`portolan-conformance` defines the behavioral profiles and test cases.
It does not build or test every SDK from this repository.
Each SDK pins a conformance revision in its own CI workflow.

## SDK status

The following releases pin `portolan-conformance` `v0.3.0`.

| SDK | Release | Read Profile v1 | Write Profile v1.1 | Metadata Validation Profile v1 | Local command |
|---|---|---|---|---|---|
| [`portolan-python`](https://github.com/geoverse-dev/portolan-python) | `v1.0.0rc3` | 29/29 | 44/44 | Not implemented; use Rashid | `make check-conformance` |
| [`portolan-java`](https://github.com/geoverse-dev/portolan-java) | `v1.0.0-RC2` | 29/29 | 44/44 | 8/8 | `make check-conformance` |

A profile pass applies only to the cases in the pinned conformance revision.
It does not prove full Portolan catalog conformance.
Use [`rashid`](https://github.com/portolan-sdi/rashid) to validate a catalog.

## Validate portolan-python

Install the SDK development dependencies.
The Make target downloads `portolan-conformance` version `v0.3.0` with `uvx`.
Then it runs:

```bash
make check-conformance
```

The target runs Read Profile v1 and Write Profile v1.1 through
`tests/conformance_adapter.py`.
It writes `read-profile-report.json` and `write-profile-report.json`.

The read profile has 29 cases.
It covers nested collection items, redirects, and strict JSON types.
The write profile has 44 cases.
It covers deterministic plans, round trips, complete structural links, and
caller-managed `README.md` and `AGENTS.md` files.
Neither profile validates a catalog against the Portolan specification.
Python applications use Rashid for normative validation.
`portolan-python` does not duplicate Rashid's rules.

Use the individual targets to run one profile:

```bash
make check-conformance-read
make check-conformance-write
```

Override the runner or report path when required:

```bash
make check-conformance \
  CONFORMANCE='uv run --project ../portolan-conformance portolan-conformance' \
  CONFORMANCE_REPORT=/tmp/portolan-python-read.json \
  CONFORMANCE_WRITE_REPORT=/tmp/portolan-python-write.json
```

`make check-conformance-all` is an explicit alias for the same two-profile check.

## Validate portolan-java

Install Java 17 and Maven.
The Make target downloads `portolan-conformance` version `v0.3.0` with `uvx`.
Then it runs:

```bash
make check-conformance
```

The target builds the test adapter and runs all three supported profiles.
It writes these reports:

- `target/portolan-conformance-read.json`
- `target/portolan-conformance-metadata.json`
- `target/portolan-conformance-write.json`

Use the individual targets to run one profile:

```bash
make check-conformance-read
make check-conformance-metadata
make check-conformance-write
```

Override the runner when required:

```bash
make check-conformance \
  CONFORMANCE='uv run --project ../portolan-conformance portolan-conformance'
```

`make check-conformance-all` is an explicit alias for the same three-profile check.

## Add another SDK

Implement an executable adapter in the SDK repository.
Keep the adapter outside the SDK runtime dependencies.
Add a `check-conformance` target to the SDK build.
Pin a conformance revision in the SDK CI workflow.
Run each supported profile and upload its JSON report.
Add the SDK to the status table after its CI passes.
