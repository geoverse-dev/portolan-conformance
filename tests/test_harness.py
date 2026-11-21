import json
import sys
from pathlib import Path

import pytest

from portolan_conformance.cli import main
from portolan_conformance.fixture_server import fixture_http_server
from portolan_conformance.protocol import (
    METADATA_VALIDATION_OPERATION,
    WRITE_OPERATION,
    load_cases,
    validate_write_response,
)
from portolan_conformance.runner import AdapterFailure, compare, invoke

ROOT = Path(__file__).resolve().parents[1]
COMMAND = [sys.executable, "-m", "portolan_conformance.reference_adapter"]


def test_fixtures_have_unique_cases():
    assert len(load_cases(ROOT / "fixtures/cases")) >= 15


def test_reference_adapter_cases():
    catalogs = ROOT / "fixtures/catalogs"
    with fixture_http_server(catalogs) as http_catalogs:
        for case in load_cases(ROOT / "fixtures/cases"):
            uri = case.uri.replace(
                "${CATALOGS}", catalogs.resolve().as_uri()
            ).replace("${HTTP_CATALOGS}", http_catalogs)
            actual = invoke(COMMAND, case.operation, uri)
            expected = json.loads(
                json.dumps(case.expected)
                .replace("${CATALOGS}", catalogs.resolve().as_uri())
                .replace("${HTTP_CATALOGS}", http_catalogs)
            )
            assert compare(actual, expected)[0], case.id


def test_cli_report(tmp_path):
    report = tmp_path / "report.json"
    assert (
        main(
            [
                "run",
                "--adapter",
                f'"{sys.executable}" -m portolan_conformance.reference_adapter',
                "--report",
                str(report),
            ]
        )
        == 0
    )
    assert json.loads(report.read_text())["summary"]["failed"] == 0


def test_wrong_adapter_fails():
    try:
        invoke(["/path/that/does/not/exist"], "inspect", "file:///x")
    except AdapterFailure:
        pass
    else:
        raise AssertionError("Must fail on missing adapter")


def test_array_order_is_not_normalized():
    assert not compare(
        {"status": "ok", "result": {"entries": [1, 2]}},
        {"status": "ok", "result": {"entries": [2, 1]}},
    )[0]


def test_json_boolean_and_number_are_not_equal():
    assert not compare(
        {"status": "ok", "result": {"document": {"value": True}}},
        {"status": "ok", "result": {"document": {"value": 1}}},
    )[0]


def test_nested_item_fixture_exposes_direct_and_recursive_operations():
    cases = {case.id: case for case in load_cases(ROOT / "fixtures/cases")}

    assert cases["items-direct-nested"].operation == "items"
    assert cases["items-direct-nested"].expected["result"]["entries"] == []
    assert cases["items-recursive-nested"].operation == "items_recursive"
    assert [
        entry["id"]
        for entry in cases["items-recursive-nested"].expected["result"]["entries"]
    ] == ["observation-2025"]


def test_metadata_validation_cases_have_version_matrix():
    cases = load_cases(ROOT / "fixtures/validation/cases")
    assert {"0.2.0", "0.3.0", "missing-profile", "unknown-profile"}.issubset(
        {tag for case in cases for tag in case.tags}
    )
    assert all(case.operation == METADATA_VALIDATION_OPERATION for case in cases)


def test_validation_result_requires_normalized_rule_sets():
    from portolan_conformance.protocol import validate_metadata_response

    validate_metadata_response(
        {
            "status": "ok",
            "result": {
                "profile_version": "1",
                "spec_version": "0.3.0",
                "valid": False,
                "errors": ["PTL-AST-002"],
                "warnings": [],
            },
        }
    )
    with pytest.raises(ValueError, match="sorted unique"):
        validate_metadata_response(
            {
                "status": "ok",
                "result": {
                    "profile_version": "1",
                    "spec_version": "0.3.0",
                    "valid": False,
                    "errors": ["PTL-AST-002", "PTL-AST-002"],
                    "warnings": [],
                },
            }
        )


def test_cli_selects_metadata_validation_profile(monkeypatch):
    seen = []

    def fake_invoke(command, operation, uri, *, timeout):
        seen.append((operation, uri))
        return {
            "status": "ok",
            "result": {
                "profile_version": "1",
                "spec_version": "0.2.0",
                "valid": True,
                "errors": [],
                "warnings": [],
            },
        }

    monkeypatch.setattr("portolan_conformance.cli.invoke", fake_invoke)
    assert (
        main(
            [
                "run",
                "--adapter",
                "unused",
                "--profile",
                "metadata-validation",
                "--tag",
                "smoke",
            ]
        )
        == 0
    )
    assert seen and all(
        operation == METADATA_VALIDATION_OPERATION for operation, _ in seen
    )


def test_write_profile_round_one_has_complete_case_matrix():
    cases = load_cases(ROOT / "fixtures/writing/cases")

    assert [case.id for case in cases] == [f"W{number:02d}" for number in range(1, 16)]
    assert all(case.operation == WRITE_OPERATION for case in cases)
    assert all(case.input is not None for case in cases)


def test_write_profile_expected_responses_have_valid_shape():
    for case in load_cases(ROOT / "fixtures/writing/cases"):
        validate_write_response(case.expected)


def test_write_response_rejects_unsafe_or_unsorted_operations():
    with pytest.raises(ValueError, match="safe relative POSIX path"):
        validate_write_response(
            {
                "status": "ok",
                "result": {
                    "profile_version": "1",
                    "spec_version": "0.3.0",
                    "operations": [{"kind": "put", "key": "../catalog.json", "content": "{}\n"}],
                },
            }
        )

    with pytest.raises(ValueError, match="sorted"):
        validate_write_response(
            {
                "status": "ok",
                "result": {
                    "profile_version": "1",
                    "spec_version": "0.3.0",
                    "operations": [
                        {"kind": "put", "key": "z.json", "content": "{}\n"},
                        {"kind": "put", "key": "a.json", "content": "{}\n"},
                    ],
                },
            }
        )
