# External catalog smoke observations

The external smoke runner observes mutable published catalogs through an SDK
adapter. It is not a conformance profile and does not provide normative expected
results.

The sources can become unavailable, change content, declare the wrong Portolan
version, or stop conforming to a version they previously passed. A smoke result
must never redefine a fixture, the SDK contract, or the Portolan specification.

## Sources of truth

The order of authority is:

1. `portolan-spec` defines normative requirements.
2. Rashid validates one observed catalog against those requirements.
3. Portolan Conformance defines portable SDK behavior.
4. Versioned fixtures define reproducible profile expectations.
5. External catalogs provide interoperability and robustness observations only.

Agreement between SDKs proves parity, not correctness. A suspected SDK defect
requires a reproducible case and human review before the SDK changes.

## Manifest

`external-catalogs/catalogs.json` lists the initial sources. Its JSON Schema is
`external-catalogs/schema.json`.

Manifest entries contain no normative result values. The initial runner permits
only root-document operations that do not dereference catalog children:

- `document`
- `inspect`
- `links`
- `assets`

This boundary ensures that all adapters observe the same captured root bytes.
Recursive live traversal belongs in a later, separately bounded audit.

## Run an observation

Capture the remote roots and run one adapter:

```bash
portolan-conformance smoke \
  --manifest external-catalogs/catalogs.json \
  --adapter 'python tests/conformance_adapter.py' \
  --observations external-observations \
  --report external-smoke-python.json
```

Run another adapter against exactly the same bytes:

```bash
portolan-conformance smoke \
  --manifest external-catalogs/catalogs.json \
  --adapter scripts/conformance-adapter \
  --observations external-observations \
  --reuse-observations \
  --report external-smoke-java.json
```

`--reuse-observations` never contacts the source URLs. It fails with
`OBSERVATION_MISSING` when a capture is absent.

## Report semantics

Every report contains `"normative": false`. Each capture records:

- the source and final URL;
- the exact byte count and SHA-256 digest;
- the observed STAC type and identifier;
- declared Portolan schema versions;
- `normative_validation: "not_checked"`.

The runner does not depend on Rashid and does not infer normative validity from
Registry metadata. Rashid characterization can be added as a separate stage
that records its version and findings against the same captured bytes.

Remote and adapter failures remain separate. The report can contain statuses
such as `REMOTE_UNAVAILABLE`, `TIMEOUT`, `CATALOG_INVALID_JSON`, `SDK_ERROR`, or
`ADAPTER_FAILURE`.

## Scheduling

The central workflow runs weekly and can also run manually. It checks out the
published Python and Java release tags, builds their existing test adapters,
and observes the same captured files. It does not commit to or modify either SDK
repository.

The workflow uploads reports and captures as diagnostic artifacts. Its external
observations are not required checks for SDK merges or releases.
