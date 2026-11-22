# Known SDKs

Each SDK owns its public API and conformance adapter.
The adapter delegates requests to the SDK implementation.
It must not contain fixture-specific results.

`portolan-conformance` defines the behavioral profiles and test cases.
It does not build or test every SDK from this repository.
Each SDK pins a conformance revision in its own CI workflow.

## SDK status

| SDK | Read Profile v1 | Write Profile v1 | Metadata Validation Profile v1 | Local command |
|---|---|---|---|---|
| `portolan-python` | Pass | Pass through Round 3 on the development branch | Not implemented; use Rashid | `make check-conformance` |
| `portolan-java` | Pass | Pass through Round 3 on the development branch | Pass for the initial fixture matrix | `make check-conformance` |

A profile pass applies only to the cases in the pinned conformance revision.
It does not prove full Portolan catalog conformance.
Use [`rashid`](https://github.com/portolan-sdi/rashid) to validate a catalog.

## Validate portolan-python

Install the SDK development dependencies.
The Make target downloads `portolan-conformance` version `v0.2.0` with `uvx`.
Then it runs:

```bash
make check-conformance
```

The released target runs Read Profile v1 through `tests/conformance_adapter.py`.
The development branch adds `make check-conformance-write` for Write Profile v1 Round 1.
It writes `write-profile-report.json`.

The development read profile has 29 cases.
The write profile has 37 cases through Round 3.
The new read cases cover nested collection items, redirects, and strict JSON types.
Neither profile validates a catalog against the Portolan specification.
Python applications use Rashid for normative validation.
`portolan-python` does not duplicate Rashid's rules.

Override the runner or report path when required:

```bash
make check-conformance \
  CONFORMANCE=/path/to/portolan-conformance/.venv/bin/portolan-conformance \
  CONFORMANCE_REPORT=/tmp/portolan-python-read.json \
  CONFORMANCE_WRITE_REPORT=/tmp/portolan-python-write.json
```

Use `make check-conformance-all` with that override to run both profiles.

## Validate portolan-java

Install Java 17 and Maven.
The Make target downloads `portolan-conformance` version `v0.2.0` with `uvx`.
Then it runs:

```bash
make check-conformance
```

The target builds the test adapter and runs both supported profiles.
Use the individual targets to run one profile:

```bash
make check-conformance-read
make check-conformance-metadata
```

Override the runner when required:

```bash
make check-conformance \
  CONFORMANCE=/path/to/portolan-conformance/.venv/bin/portolan-conformance
```

## Add another SDK

Implement an executable adapter in the SDK repository.
Keep the adapter outside the SDK runtime dependencies.
Add a `check-conformance` target to the SDK build.
Pin a conformance revision in the SDK CI workflow.
Run each supported profile and upload its JSON report.
Add the SDK to the status table after its CI passes.
