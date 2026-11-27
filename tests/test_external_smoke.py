from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from portolan_conformance.cli import main
from portolan_conformance.external_smoke import ManifestError, load_manifest, run_smoke
from portolan_conformance.fixture_server import fixture_http_server

COMMAND = [sys.executable, "-m", "portolan_conformance.reference_adapter"]


def _catalog() -> dict[str, object]:
    return {
        "type": "Catalog",
        "stac_version": "1.1.0",
        "stac_extensions": [
            "https://schemas.portolan-sdi.org/portolan/v0.3.0/schema.json"
        ],
        "id": "external-demo",
        "title": "External demo",
        "description": "A mutable catalog used as an observation, not an oracle.",
        "links": [],
    }


def _manifest(url: str) -> dict[str, object]:
    return {
        "manifest_version": "1",
        "catalogs": [
            {
                "id": "external-demo",
                "url": url,
                "mutable": True,
                "operations": ["document", "inspect", "links"],
                "notes": "No values in this entry are normative expectations.",
            }
        ],
    }


def test_smoke_captures_once_and_invokes_adapter_against_saved_bytes(tmp_path: Path) -> None:
    catalogs = tmp_path / "served"
    catalogs.mkdir()
    content = json.dumps(_catalog(), separators=(",", ":")).encode() + b"\n"
    (catalogs / "catalog.json").write_bytes(content)

    with fixture_http_server(catalogs) as base_url:
        report = run_smoke(
            _manifest(f"{base_url}/catalog.json"),
            COMMAND,
            observations=tmp_path / "observations",
            timeout=5,
        )

    observed = report["catalogs"][0]
    assert report["kind"] == "external-catalog-smoke"
    assert report["normative"] is False
    assert report["summary"] == {"total": 1, "passed": 1, "failed": 0}
    assert observed["capture"]["sha256"] == hashlib.sha256(content).hexdigest()
    assert observed["capture"]["declared_portolan_versions"] == ["0.3.0"]
    assert observed["capture"]["normative_validation"] == "not_checked"
    assert [operation["operation"] for operation in observed["operations"]] == [
        "document",
        "inspect",
        "links",
    ]
    assert all(operation["status"] == "PASS" for operation in observed["operations"])
    assert (tmp_path / "observations" / "external-demo.json").read_bytes() == content


def test_smoke_reuses_capture_without_contacting_source(tmp_path: Path) -> None:
    observations = tmp_path / "observations"
    observations.mkdir()
    content = json.dumps(_catalog()).encode()
    (observations / "external-demo.json").write_bytes(content)

    report = run_smoke(
        _manifest("http://127.0.0.1:1/catalog.json"),
        COMMAND,
        observations=observations,
        reuse_observations=True,
        timeout=5,
    )

    capture = report["catalogs"][0]["capture"]
    assert capture["status"] == "REUSED"
    assert capture["sha256"] == hashlib.sha256(content).hexdigest()
    assert report["summary"]["passed"] == 1


def test_remote_failure_is_classified_without_invoking_adapter(tmp_path: Path) -> None:
    report = run_smoke(
        _manifest("http://127.0.0.1:1/catalog.json"),
        COMMAND,
        observations=tmp_path / "observations",
        timeout=0.2,
    )

    observed = report["catalogs"][0]
    assert observed["status"] == "REMOTE_UNAVAILABLE"
    assert observed["operations"] == []
    assert report["summary"] == {"total": 1, "passed": 0, "failed": 1}


@pytest.mark.parametrize(
    "manifest",
    [
        {},
        {"manifest_version": "2", "catalogs": []},
        {"manifest_version": "1", "catalogs": []},
        {
            "manifest_version": "1",
            "catalogs": [
                {"id": "duplicate", "url": "https://example.test/a", "operations": ["inspect"]},
                {"id": "duplicate", "url": "https://example.test/b", "operations": ["inspect"]},
            ],
        },
        {
            "manifest_version": "1",
            "catalogs": [
                {"id": "unsafe/id", "url": "https://example.test/a", "operations": ["inspect"]}
            ],
        },
        {
            "manifest_version": "1",
            "catalogs": [
                {"id": "demo", "url": "file:///tmp/catalog.json", "operations": ["inspect"]}
            ],
        },
        {
            "manifest_version": "1",
            "catalogs": [
                {"id": "demo", "url": "https://example.test/a", "operations": ["collections"]}
            ],
        },
    ],
)
def test_manifest_rejects_unsafe_or_unsupported_entries(manifest: dict[str, object]) -> None:
    with pytest.raises(ManifestError):
        load_manifest(manifest)


def test_cli_smoke_writes_non_normative_report(tmp_path: Path) -> None:
    catalogs = tmp_path / "served"
    catalogs.mkdir()
    (catalogs / "catalog.json").write_text(json.dumps(_catalog()), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    report_path = tmp_path / "report.json"

    with fixture_http_server(catalogs) as base_url:
        manifest_path.write_text(
            json.dumps(_manifest(f"{base_url}/catalog.json")), encoding="utf-8"
        )
        result = main(
            [
                "smoke",
                "--manifest",
                str(manifest_path),
                "--adapter",
                f'"{sys.executable}" -m portolan_conformance.reference_adapter',
                "--observations",
                str(tmp_path / "observations"),
                "--report",
                str(report_path),
            ]
        )

    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["normative"] is False
    assert report["catalogs"][0]["status"] == "PASS"


def test_repository_manifest_is_valid_and_contains_initial_sources() -> None:
    manifest = load_manifest(Path(__file__).resolve().parents[1] / "external-catalogs/catalogs.json")

    assert {entry["id"] for entry in manifest["catalogs"]} == {
        "portolan-registry",
        "geomermaids-root",
        "geomermaids-osm-na",
        "dhis2-nepal",
    }
    assert all(entry["mutable"] for entry in manifest["catalogs"])
