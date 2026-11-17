.PHONY: help setup test check check-reference

UV ?= uv
REFERENCE_REPORT ?= report.json

help:
	@printf '%s\n' 'Targets: setup test check check-reference'

setup:
	$(UV) sync --extra test

test:
	$(UV) run --extra test pytest -q

check-reference:
	$(UV) run --extra test portolan-conformance run \
		--profile read \
		--adapter '$(UV) run python -m portolan_conformance.reference_adapter' \
		--report '$(REFERENCE_REPORT)'

check: test check-reference
