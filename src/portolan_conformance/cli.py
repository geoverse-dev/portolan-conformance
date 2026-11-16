from __future__ import annotations
import argparse
import json
import shlex
import sys
import time
from pathlib import Path
from .protocol import load_cases
from .runner import AdapterFailure, compare, invoke

ROOT = Path(__file__).resolve().parents[2]

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Portolan SDK read-only conformance suite")
    parser.add_argument("run", nargs="?", choices=["run"], default="run")
    parser.add_argument("--adapter", required=True, help="Adapter command, shell-style quoted")
    parser.add_argument("--cases", type=Path, default=ROOT / "fixtures" / "cases")
    parser.add_argument("--catalogs", type=Path, default=ROOT / "fixtures" / "catalogs")
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--tag", help="Run cases with this tag")
    parser.add_argument("--report", type=Path, help="Write machine-readable JSON report")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    command = shlex.split(args.adapter)
    if not command:
        parser.error("--adapter must not be empty")
    cases = load_cases(args.cases)
    if args.tag:
        cases = [c for c in cases if args.tag in c.tags]
    if not cases:
        parser.error("No cases selected")
    results = []
    for case in cases:
        uri = case.uri.replace("${CATALOGS}", args.catalogs.resolve().as_uri())
        started = time.monotonic()
        try:
            actual = invoke(command, case.operation, uri, timeout=args.timeout)
            expected = json.loads(json.dumps(case.expected).replace("${CATALOGS}", args.catalogs.resolve().as_uri()))
            passed, message = compare(actual, expected)
        except AdapterFailure as exc:
            passed, message = False, str(exc)
        elapsed = round(time.monotonic() - started, 4)
        results.append({"id": case.id, "status": "PASS" if passed else "FAIL", "duration_seconds": elapsed, "message": message})
        print(f"{'PASS' if passed else 'FAIL'} {case.id}" + (f" — {message[:300]}" if message else ""))
    summary = {"total": len(results), "passed": sum(x["status"] == "PASS" for x in results),
               "failed": sum(x["status"] == "FAIL" for x in results)}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({"protocol_version": "1", "summary": summary, "cases": results}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))
    return 1 if summary["failed"] else 0

if __name__ == "__main__":
    sys.exit(main())
