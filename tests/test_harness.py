import json
import sys
from pathlib import Path
from portolan_conformance.protocol import load_cases
from portolan_conformance.runner import compare, invoke, AdapterFailure
from portolan_conformance.cli import main

ROOT = Path(__file__).resolve().parents[1]
COMMAND = [sys.executable, "-m", "portolan_conformance.reference_adapter"]

def test_fixtures_have_unique_cases():
    assert len(load_cases(ROOT / "fixtures/cases")) >= 15

def test_reference_adapter_cases():
    for case in load_cases(ROOT / "fixtures/cases"):
        uri = case.uri.replace("${CATALOGS}", (ROOT / "fixtures/catalogs").resolve().as_uri())
        actual = invoke(COMMAND, case.operation, uri)
        expected = json.loads(json.dumps(case.expected).replace("${CATALOGS}", (ROOT / "fixtures/catalogs").resolve().as_uri()))
        assert compare(actual, expected)[0], case.id

def test_cli_report(tmp_path):
    report = tmp_path / "report.json"
    assert main(["run", "--adapter", f'"{sys.executable}" -m portolan_conformance.reference_adapter',
                 "--report", str(report)]) == 0
    assert json.loads(report.read_text())["summary"]["failed"] == 0

def test_wrong_adapter_fails():
    try:
        invoke(["/path/that/does/not/exist"], "inspect", "file:///x")
    except AdapterFailure:
        pass
    else:
        raise AssertionError("Must fail on missing adapter")

def test_array_order_is_not_normalized():
    assert not compare({"status":"ok","result":{"entries":[1,2]}},
                       {"status":"ok","result":{"entries":[2,1]}})[0]
