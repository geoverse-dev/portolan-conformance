# Metadata Validation Profile v1

## Purpose

This profile defines common metadata validation behavior for native Portolan SDKs.
It covers Portolan 0.2.0 and 0.3.0.

The profile does not define new Portolan requirements.
The [Portolan specification](https://github.com/portolan-sdi/portolan-spec) remains normative.
`rashid` remains the complete validator for metadata, data bytes, and hosting.

The initial fixture matrix is not complete rule coverage.
A passing report only covers the cases in this repository revision.

## Scope

An implementation reads the linked STAC metadata tree and applies version-specific metadata rules.
It does not read geospatial asset bytes or probe live hosting behavior.

The profile includes these validation scopes:

- JSON structure.
- STAC 1.1 metadata structure.
- Portolan metadata requirements.
- Portolan containment and link structure.

The profile excludes asset byte checks, HTTP range checks, CORS checks, and format inspection.

## Adapter operation

The adapter protocol adds the `validate_metadata` operation.
It uses the same one-request-per-process transport as the Read Profile.

Request:

```json
{"protocol_version":"1","operation":"validate_metadata","uri":"file:///tmp/catalog.json"}
```

A successful validation returns this exact structure:

```json
{
  "status": "ok",
  "result": {
    "profile_version": "1",
    "spec_version": "0.3.0",
    "valid": false,
    "errors": ["PTL-AST-002"],
    "warnings": []
  }
}
```

`spec_version` is `0.2.0`, `0.3.0`, or `null` when no profile is declared.
`valid` is true exactly when `errors` is empty.

`errors` and `warnings` contain `rashid` rule IDs where a matching rule exists.
Each array is sorted and contains no duplicate value.
The adapter discards messages, paths, and duplicate findings from the SDK result.

An unsupported declared Portolan version returns this domain error:

```json
{"status":"error","error":{"code":"UNSUPPORTED_PROFILE"}}
```

Read errors use the error codes from the Read Profile adapter protocol.

## Version behavior

The implementation selects rules from the root catalog's Portolan schema URI.
It must not apply 0.3.0 rules to a 0.2.0 catalog.

The fixtures include one explicit version difference.
Portolan 0.2.0 requires an absolute asset HREF to use HTTPS.
Portolan 0.3.0 permits another scheme when the asset has an HTTPS alternate.
The 0.3.0 form still produces the `PTL-AST-002` warning.

A missing declaration produces `PTL-CNF-001` and a null `spec_version`.
An unknown version produces `UNSUPPORTED_PROFILE`.

## SDK integration

The adapter must delegate to the SDK's public validation API.
It must not contain fixture names or expected answers.

A Java SDK can expose detailed findings from `inspect()` and let `openStrict()` reject errors.
Its adapter maps those findings into the normalized arrays.
Future TypeScript and Rust SDKs can use idiomatic result types and apply the same mapping.

Run the profile with this command:

```bash
portolan-conformance run \
  --profile metadata-validation \
  --adapter './path/to/sdk-adapter' \
  --report metadata-validation-report.json
```

## Fixture provenance

[`fixtures/validation/SOURCES.json`](../fixtures/validation/SOURCES.json) pins the specification and validator references.
The positive 0.2.0 and 0.3.0 fixtures pass the schema and metadata checks in `rashid` 0.4.0.
The version-difference fixtures isolate behavior that changed between the two schemas.

Add a positive and a negative fixture before claiming coverage for another rule.
Use one primary failure per negative fixture when possible.
