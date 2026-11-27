# Changelog

## Unreleased

- Add basic resource-resolution coverage for truncated JSON and unexpected media types.
- Add finite-depth traversal and fixture-root containment cases.
- Add a deterministic delayed-response primitive without defining a public SDK timeout API.

## 0.4.0 — 2026-11-27

- Add Resource Resolution Profile v1 with deterministic local HTTP cases.
- Add Compatibility Profile v1 for Portolan 0.2.0 and 0.3.0 read behavior.
- Package all new fixtures and run both profiles in the harness self-check.
- Add adversarial read cases for catalog cycles and duplicate collection IDs.

## 0.3.0 — 2026-11-23

- Add Write Profile v1.1 structural-link requirements.
- Require titles and correct media types on generated containment links.
- Add copy-on-write documentation editing and round-trip cases.
- Keep Write Profile v1 fixtures available through the immutable v0.2.0 release.

## 0.2.0 — 2026-11-21

- Add SDK Write Profile v1 Round 1 with cases W01–W15.
- Define deterministic, storage-independent PUT plans for Portolan 0.3.0 metadata.
- Distinguish direct and recursive item discovery in the Read Profile.
- Resolve relative links against the final URL after an HTTP redirect.
- Compare JSON booleans and numbers as distinct types.
- Add Round 2 edit, safe deletion, export, and round-trip cases W16–W22 and R01–R04.
- Add Round 3 hardening and fidelity cases W23–W30 and R05–R07.

## 0.1.1 — 2026-11-17

- Run repository checks in the project environment with `uv`.
- Use the full Portolan specification versions `0.2.0` and `0.3.0` in documentation and fixture tags.

## 0.1.0 — 2026-11-17

- Add SDK Read Profile v1.
- Add Metadata Validation Profile v1 for Portolan 0.2.0 and 0.3.0.
- Add versioned fixtures and machine-readable reports.
- Document known SDKs and their conformance commands.
