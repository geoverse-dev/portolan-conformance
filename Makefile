.PHONY: help setup test check check-reference

PYTHON ?= python
PYTEST ?= pytest
CONFORMANCE ?= portolan-conformance
REFERENCE_REPORT ?= report.json

help:
	@printf '%s\n' 'Targets: setup test check check-reference'

setup:
	$(PYTHON) -m pip install -e '.[test]'

test:
	$(PYTEST) -q

check-reference:
	$(CONFORMANCE) run \
		--profile read \
		--adapter '$(PYTHON) -m portolan_conformance.reference_adapter' \
		--report '$(REFERENCE_REPORT)'

check: test check-reference
