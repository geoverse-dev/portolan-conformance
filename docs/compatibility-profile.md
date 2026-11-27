# Compatibility Profile v1

This profile protects stable read behavior across Portolan specification versions.
It does not perform normative validation.

## Contract

The profile uses the existing `inspect` and `document` operations. An SDK must:

- read Portolan 0.2.0 metadata;
- read Portolan 0.3.0 metadata;
- preserve the declared profile in the raw document;
- preserve unknown fields and their JSON types;
- keep permissive reading for a missing or unknown profile.

Normative rejection belongs to the Metadata Validation Profile. A permissive `open()` operation and a strict validation operation have separate contracts.

Run the profile with:

```bash
portolan-conformance run \
  --profile compatibility \
  --adapter '<SDK adapter command>' \
  --report compatibility-report.json
```

## Limits

Version 1 does not compare strict validation results. It also does not define an adapter capability declaration. Those changes require a versioned protocol decision.
