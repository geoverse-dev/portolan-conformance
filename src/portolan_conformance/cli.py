from __future__ import annotations

import argparse
import json
import shlex
import sys
import sysconfig
import time
from pathlib import Path

from .fixture_server import fixture_http_server
from .protocol import (
    METADATA_VALIDATION_OPERATION,
    WRITE_OPERATION,
    load_cases,
    validate_metadata_response,
    validate_write_response,
)
from .runner import AdapterFailure, compare, invoke

SOURCE_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
INSTALLED_FIXTURES = (
    Path(sysconfig.get_path("data"))
    / "share"
    / "portolan-conformance"
    / "fixtures"
)
FIXTURES = SOURCE_FIXTURES if SOURCE_FIXTURES.is_dir() else INSTALLED_FIXTURES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Portolan SDK conformance suites")
    parser.add_argument("run", nargs="?", choices=["run"], default="run")
    parser.add_argument(
        "--adapter", required=True, help="Adapter command, shell-style quoted"
    )
    parser.add_argument(
        "--profile",
        choices=(
            "read",
            "resource-resolution",
            "compatibility",
            "metadata-validation",
            "write",
        ),
        default="read",
        help="Behavior profile to run",
    )
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--catalogs", type=Path)
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--tag", help="Run cases with this tag")
    parser.add_argument(
        "--report", type=Path, help="Write machine-readable JSON report"
    )
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    command = shlex.split(args.adapter)
    if not command:
        parser.error("--adapter must not be empty")
    profile_root = FIXTURES
    if args.profile == "metadata-validation":
        profile_root /= "validation"
    elif args.profile == "write":
        profile_root /= "writing"
    elif args.profile == "resource-resolution":
        profile_root /= "resolution"
    elif args.profile == "compatibility":
        profile_root /= "compatibility"
    cases_root = args.cases or profile_root / "cases"
    catalogs_root = args.catalogs or profile_root / "catalogs"
    cases = load_cases(cases_root)
    if args.tag:
        cases = [c for c in cases if args.tag in c.tags]
    if not cases:
        parser.error("No cases selected")
    results = []
    with fixture_http_server(catalogs_root) as http_catalogs:
        for case in cases:
            uri = (
                case.uri.replace(
                    "${CATALOGS}", catalogs_root.resolve().as_uri()
                ).replace("${HTTP_CATALOGS}", http_catalogs)
                if case.uri is not None
                else None
            )
            started = time.monotonic()
            try:
                if case.input is None:
                    actual = invoke(command, case.operation, uri, timeout=args.timeout)
                else:
                    actual = invoke(
                        command,
                        case.operation,
                        input_value=case.input,
                        timeout=args.timeout,
                    )
                if case.operation == METADATA_VALIDATION_OPERATION:
                    try:
                        validate_metadata_response(actual)
                    except (TypeError, ValueError) as exc:
                        raise AdapterFailure(str(exc)) from exc
                if case.operation == WRITE_OPERATION:
                    try:
                        validate_write_response(actual)
                    except (TypeError, ValueError) as exc:
                        raise AdapterFailure(str(exc)) from exc
                expected = json.loads(
                    json.dumps(case.expected)
                    .replace("${CATALOGS}", catalogs_root.resolve().as_uri())
                    .replace("${HTTP_CATALOGS}", http_catalogs)
                )
                passed, message = compare(actual, expected)
            except AdapterFailure as exc:
                passed, message = False, str(exc)
            elapsed = round(time.monotonic() - started, 4)
            results.append(
                {
                    "id": case.id,
                    "status": "PASS" if passed else "FAIL",
                    "duration_seconds": elapsed,
                    "message": message,
                }
            )
            print(
                f"{'PASS' if passed else 'FAIL'} {case.id}"
                + (f" — {message[:300]}" if message else "")
            )
    summary = {
        "total": len(results),
        "passed": sum(x["status"] == "PASS" for x in results),
        "failed": sum(x["status"] == "FAIL" for x in results),
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(
                {"protocol_version": "1", "summary": summary, "cases": results},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(json.dumps(summary))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
