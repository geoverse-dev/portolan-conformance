"""Isolated one-request-per-process JSON adapter runner."""
from __future__ import annotations
import json
import os
import subprocess
from pathlib import Path
from typing import Any

class AdapterFailure(Exception):
    pass

def invoke(
    command: list[str],
    operation: str,
    uri: str | None = None,
    *,
    input_value: dict[str, Any] | None = None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    request: dict[str, Any] = {"protocol_version": "1", "operation": operation}
    if uri is not None:
        request["uri"] = uri
    if input_value is not None:
        request["input"] = input_value
    try:
        proc = subprocess.run(command, input=json.dumps(request) + "\n", text=True,
                              capture_output=True, timeout=timeout, check=False,
                              env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    except subprocess.TimeoutExpired as exc:
        raise AdapterFailure(f"Adapter timeout ({timeout}s)") from exc
    except OSError as exc:
        raise AdapterFailure(f"Cannot launch adapter: {exc}") from exc
    if proc.returncode != 0:
        raise AdapterFailure(f"Adapter exited {proc.returncode}: {proc.stderr[:1000]}")
    try:
        response = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AdapterFailure(f"Adapter stdout must contain exactly one JSON object: {proc.stdout[:500]!r}") from exc
    if not isinstance(response, dict) or response.get("status") not in ("ok", "error"):
        raise AdapterFailure(f"Malformed adapter response: {response!r}")
    if response["status"] == "ok" and not isinstance(response.get("result"), dict):
        raise AdapterFailure("Successful response must contain object 'result'")
    if response["status"] == "error" and not isinstance(response.get("error"), dict):
        raise AdapterFailure("Error response must contain object 'error'")
    return response

def canonicalize(value: Any) -> Any:
    """Only normalize ordering of JSON object keys; preserve array order and values."""
    if isinstance(value, dict):
        return {k: canonicalize(value[k]) for k in sorted(value)}
    if isinstance(value, list):
        return [canonicalize(v) for v in value]
    return value

def compare(actual: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, str]:
    a, e = canonicalize(actual), canonicalize(expected)
    if a == e:
        return True, ""
    return False, "expected=" + json.dumps(e, ensure_ascii=False, sort_keys=True) + " actual=" + json.dumps(a, ensure_ascii=False, sort_keys=True)
