"""Non-normative observations of mutable external Portolan catalogs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .runner import AdapterFailure, invoke

MANIFEST_VERSION = "1"
ALLOWED_OPERATIONS = frozenset({"document", "inspect", "links", "assets"})
PORTOLAN_SCHEMA = re.compile(
    r"^https://schemas\.portolan-sdi\.org/portolan/v([^/]+)/schema\.json$"
)
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
USER_AGENT = "portolan-conformance-external-smoke/1"


class ManifestError(ValueError):
    """The external catalog manifest is malformed or unsafe."""


def load_manifest(value: Path | dict[str, Any]) -> dict[str, Any]:
    """Load and validate a non-normative external catalog manifest."""
    if isinstance(value, Path):
        try:
            raw = json.loads(value.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ManifestError(f"Cannot load manifest: {exc}") from exc
    else:
        raw = value
    if not isinstance(raw, dict) or raw.get("manifest_version") != MANIFEST_VERSION:
        raise ManifestError(f"manifest_version must be {MANIFEST_VERSION!r}")
    catalogs = raw.get("catalogs")
    if not isinstance(catalogs, list) or not catalogs:
        raise ManifestError("catalogs must be a non-empty array")

    normalized: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for entry in catalogs:
        if not isinstance(entry, dict):
            raise ManifestError("each catalog entry must be an object")
        identifier = entry.get("id")
        url = entry.get("url")
        operations = entry.get("operations")
        if not isinstance(identifier, str) or not SAFE_ID.fullmatch(identifier):
            raise ManifestError("catalog id must be a safe lowercase identifier")
        if identifier in identifiers:
            raise ManifestError(f"duplicate catalog id: {identifier}")
        identifiers.add(identifier)
        if not isinstance(url, str) or urlparse(url).scheme not in {"http", "https"}:
            raise ManifestError("catalog url must use HTTP or HTTPS")
        if (
            not isinstance(operations, list)
            or not operations
            or any(not isinstance(operation, str) for operation in operations)
            or len(operations) != len(set(operations))
            or not set(operations).issubset(ALLOWED_OPERATIONS)
        ):
            raise ManifestError(
                "operations must be unique supported root-document observations"
            )
        mutable = entry.get("mutable", True)
        notes = entry.get("notes")
        if not isinstance(mutable, bool) or notes is not None and not isinstance(notes, str):
            raise ManifestError("mutable must be boolean and notes must be a string")
        normalized.append(
            {
                "id": identifier,
                "url": url,
                "mutable": mutable,
                "operations": operations,
                "notes": notes,
            }
        )
    return {"manifest_version": MANIFEST_VERSION, "catalogs": normalized}


def run_smoke(
    manifest: Path | dict[str, Any],
    command: list[str],
    *,
    observations: Path,
    timeout: float = 15.0,
    max_bytes: int = 5_000_000,
    reuse_observations: bool = False,
) -> dict[str, Any]:
    """Capture catalog roots and observe one SDK against the captured bytes."""
    if not command:
        raise ValueError("adapter command must not be empty")
    if timeout <= 0 or max_bytes <= 0:
        raise ValueError("timeout and max_bytes must be positive")
    loaded = load_manifest(manifest)
    observations.mkdir(parents=True, exist_ok=True)
    catalog_results = [
        _observe_catalog(
            entry,
            command,
            observations=observations,
            timeout=timeout,
            max_bytes=max_bytes,
            reuse_observations=reuse_observations,
        )
        for entry in loaded["catalogs"]
    ]
    passed = sum(result["status"] == "PASS" for result in catalog_results)
    return {
        "report_version": "1",
        "kind": "external-catalog-smoke",
        "normative": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest_version": loaded["manifest_version"],
        "summary": {
            "total": len(catalog_results),
            "passed": passed,
            "failed": len(catalog_results) - passed,
        },
        "catalogs": catalog_results,
    }


def _observe_catalog(
    entry: dict[str, Any],
    command: list[str],
    *,
    observations: Path,
    timeout: float,
    max_bytes: int,
    reuse_observations: bool,
) -> dict[str, Any]:
    target = observations / f"{entry['id']}.json"
    started = time.monotonic()
    try:
        if reuse_observations:
            content = target.read_bytes()
            final_url = entry["url"]
            capture_status = "REUSED"
        else:
            content, final_url = _fetch(entry["url"], timeout=timeout, max_bytes=max_bytes)
            target.write_bytes(content)
            capture_status = "CAPTURED"
    except FileNotFoundError:
        return _capture_failure(entry, "OBSERVATION_MISSING", started)
    except TimeoutError:
        return _capture_failure(entry, "TIMEOUT", started)
    except (HTTPError, URLError, OSError):
        return _capture_failure(entry, "REMOTE_UNAVAILABLE", started)
    except ValueError:
        return _capture_failure(entry, "CAPTURE_TOO_LARGE", started)

    try:
        document = json.loads(content)
    except json.JSONDecodeError:
        return _captured_invalid(entry, target, content, final_url, capture_status, started)
    if not isinstance(document, dict):
        return _captured_invalid(entry, target, content, final_url, capture_status, started)

    capture = _capture_metadata(
        target, content, document, final_url=final_url, status=capture_status
    )
    operations = [
        _invoke_observation(command, operation, target.resolve().as_uri(), timeout)
        for operation in entry["operations"]
    ]
    failed = next((result["status"] for result in operations if result["status"] != "PASS"), None)
    return {
        "id": entry["id"],
        "source_url": entry["url"],
        "mutable": entry["mutable"],
        "notes": entry["notes"],
        "normative": False,
        "status": failed or "PASS",
        "duration_seconds": round(time.monotonic() - started, 4),
        "capture": capture,
        "operations": operations,
    }


def _fetch(url: str, *, timeout: float, max_bytes: int) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            content_length = response.headers.get("Content-Length")
            if content_length is not None and int(content_length) > max_bytes:
                raise ValueError("remote document exceeds max_bytes")
            content = response.read(max_bytes + 1)
            if len(content) > max_bytes:
                raise ValueError("remote document exceeds max_bytes")
            return content, response.geturl()
    except (socket.timeout, TimeoutError) as exc:
        raise TimeoutError from exc


def _invoke_observation(
    command: list[str], operation: str, uri: str, timeout: float
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        response = invoke(command, operation, uri, timeout=timeout)
    except AdapterFailure as exc:
        return {
            "operation": operation,
            "status": "ADAPTER_FAILURE",
            "duration_seconds": round(time.monotonic() - started, 4),
            "message": str(exc),
        }
    encoded = json.dumps(response, ensure_ascii=False, sort_keys=True).encode("utf-8")
    if response["status"] == "error":
        error = response.get("error", {})
        return {
            "operation": operation,
            "status": "SDK_ERROR",
            "duration_seconds": round(time.monotonic() - started, 4),
            "error_code": error.get("code"),
            "response_sha256": hashlib.sha256(encoded).hexdigest(),
            "response": response,
        }
    return {
        "operation": operation,
        "status": "PASS",
        "duration_seconds": round(time.monotonic() - started, 4),
        "response_sha256": hashlib.sha256(encoded).hexdigest(),
        "response": response,
    }


def _capture_metadata(
    path: Path,
    content: bytes,
    document: dict[str, Any],
    *,
    final_url: str,
    status: str,
) -> dict[str, Any]:
    extensions = document.get("stac_extensions")
    versions = []
    if isinstance(extensions, list):
        for extension in extensions:
            if isinstance(extension, str) and (match := PORTOLAN_SCHEMA.fullmatch(extension)):
                versions.append(match.group(1))
    return {
        "status": status,
        "path": path.name,
        "final_url": final_url,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "json_type": document.get("type"),
        "catalog_id": document.get("id"),
        "stac_version": document.get("stac_version"),
        "declared_portolan_versions": sorted(set(versions)),
        "normative_validation": "not_checked",
    }


def _capture_failure(
    entry: dict[str, Any], status: str, started: float
) -> dict[str, Any]:
    return {
        "id": entry["id"],
        "source_url": entry["url"],
        "mutable": entry["mutable"],
        "notes": entry["notes"],
        "normative": False,
        "status": status,
        "duration_seconds": round(time.monotonic() - started, 4),
        "capture": None,
        "operations": [],
    }


def _captured_invalid(
    entry: dict[str, Any],
    target: Path,
    content: bytes,
    final_url: str,
    capture_status: str,
    started: float,
) -> dict[str, Any]:
    result = _capture_failure(entry, "CATALOG_INVALID_JSON", started)
    result["capture"] = {
        "status": capture_status,
        "path": target.name,
        "final_url": final_url,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "normative_validation": "not_checked",
    }
    return result


def smoke_main(argv: list[str]) -> int:
    """CLI entrypoint for the non-normative external smoke runner."""
    parser = argparse.ArgumentParser(
        prog="portolan-conformance smoke",
        description="Observe mutable external catalogs without treating them as normative",
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--adapter", required=True, help="Adapter command, shell-style quoted")
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--reuse-observations", action="store_true")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--max-bytes", type=int, default=5_000_000)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    command = shlex.split(args.adapter)
    if not command:
        parser.error("--adapter must not be empty")
    try:
        report = run_smoke(
            args.manifest,
            command,
            observations=args.observations,
            timeout=args.timeout,
            max_bytes=args.max_bytes,
            reuse_observations=args.reuse_observations,
        )
    except (ManifestError, ValueError) as exc:
        parser.error(str(exc))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for catalog in report["catalogs"]:
        print(f"{catalog['status']} {catalog['id']}")
    print(json.dumps(report["summary"]))
    return 1 if report["summary"]["failed"] else 0
