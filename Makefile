.PHONY: help setup test check check-reference check-reference-read check-reference-resolution check-reference-compatibility

UV ?= uv
REFERENCE_REPORT ?= report.json

help:
	@printf '%s\n' 'Targets: setup test check check-reference'

setup:
	$(UV) sync --extra test

test:
	$(UV) run --extra test pytest -q

check-reference-read:
	$(UV) run --extra test portolan-conformance run \
		--profile read \
		--adapter '$(UV) run python -m portolan_conformance.reference_adapter' \
		--report '$(REFERENCE_REPORT)'

check-reference-resolution:
	$(UV) run --extra test portolan-conformance run \
		--profile resource-resolution \
		--adapter '$(UV) run python -m portolan_conformance.reference_adapter' \
		--report 'resource-resolution-report.json'

check-reference-compatibility:
	$(UV) run --extra test portolan-conformance run \
		--profile compatibility \
		--adapter '$(UV) run python -m portolan_conformance.reference_adapter' \
		--report 'compatibility-report.json'

check-reference: check-reference-read check-reference-resolution check-reference-compatibility

check: test check-reference
