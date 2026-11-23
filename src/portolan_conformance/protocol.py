"""Protocol v1, deliberately independent of any Portolan SDK."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

PROTOCOL_VERSION = "1"
METADATA_VALIDATION_OPERATION = "validate_metadata"
WRITE_OPERATION = "plan_write"
EDIT_OPERATION = "edit_plan"
ROUNDTRIP_OPERATION = "roundtrip"
READ_OPERATIONS = frozenset(
    {
        "inspect",
        "document",
        "children",
        "collections",
        "items",
        "items_recursive",
        "assets",
        "links",
    }
)
OPERATIONS = READ_OPERATIONS | {
    METADATA_VALIDATION_OPERATION,
    WRITE_OPERATION,
    EDIT_OPERATION,
    ROUNDTRIP_OPERATION,
}
VALIDATION_PROFILE_VERSION = "1"
WRITE_PROFILE_VERSION = "1.1"


@dataclass(frozen=True)
class Case:
    id: str
    operation: str
    uri: str | None
    expected: dict[str, Any]
    input: dict[str, Any] | None = None
    tags: tuple[str, ...] = ()
    description: str = ""

    @classmethod
    def from_path(cls, path: Path) -> Case:
        data = json.loads(path.read_text(encoding="utf-8"))
        required = {"id", "operation", "expected"}
        if not required.issubset(data):
            raise ValueError(f"{path}: missing {required - data.keys()}")
        if data["operation"] not in OPERATIONS:
            raise ValueError(f"{path}: unsupported operation {data['operation']}")
        uri = data.get("uri")
        input_value = data.get("input")
        if data["operation"] in {WRITE_OPERATION, EDIT_OPERATION, ROUNDTRIP_OPERATION}:
            if not isinstance(input_value, dict) or uri is not None:
                raise ValueError(f"{path}: write cases require input and no uri")
            if data["operation"] == WRITE_OPERATION:
                validate_write_response(data["expected"])
        elif not isinstance(uri, str) or input_value is not None:
            raise ValueError(f"{path}: read cases require uri and no input")
        if data["operation"] == METADATA_VALIDATION_OPERATION:
            validate_metadata_response(data["expected"])
        return cls(
            id=data["id"],
            operation=data["operation"],
            uri=uri,
            expected=data["expected"],
            input=input_value,
            tags=tuple(data.get("tags", [])),
            description=data.get("description", ""),
        )


def load_cases(root: Path) -> list[Case]:
    cases = [Case.from_path(p) for p in sorted(root.glob("*.json"))]
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case IDs")
    if not cases:
        raise ValueError(f"No cases in {root}")
    return cases


def validate_metadata_response(response: dict[str, Any]) -> None:
    """Reject successful validation responses outside profile v1's exact shape."""
    if response.get("status") == "error":
        error = response.get("error")
        allowed = {
            "NOT_FOUND",
            "INVALID_JSON",
            "INVALID_REQUEST",
            "READ_ERROR",
            "UNSUPPORTED_PROFILE",
            "UNSUPPORTED_PROTOCOL",
        }
        if (
            not isinstance(error, dict)
            or set(error) != {"code"}
            or error["code"] not in allowed
        ):
            raise ValueError("invalid metadata validation domain error")
        return
    if response.get("status") != "ok":
        raise ValueError("metadata validation response status must be ok or error")
    result = response.get("result")
    if not isinstance(result, dict):
        raise TypeError("validation result must be an object")
    required = {"profile_version", "spec_version", "valid", "errors", "warnings"}
    if set(result) != required:
        raise ValueError(f"validation result fields must be exactly {sorted(required)}")
    if result["profile_version"] != VALIDATION_PROFILE_VERSION:
        raise ValueError("unsupported metadata validation profile version")
    if result["spec_version"] not in ("0.2.0", "0.3.0", None):
        raise ValueError("spec_version must be 0.2.0, 0.3.0, or null")
    if not isinstance(result["valid"], bool):
        raise TypeError("valid must be a boolean")
    for field in ("errors", "warnings"):
        values = result[field]
        if (
            not isinstance(values, list)
            or any(not isinstance(value, str) or not value for value in values)
            or values != sorted(set(values))
        ):
            raise ValueError(f"{field} must be a sorted unique string array")
    if result["valid"] != (not result["errors"]):
        raise ValueError("valid must be true exactly when errors is empty")


def validate_write_response(response: dict[str, Any]) -> None:
    """Validate the exact Write Profile v1 adapter response shape."""
    if response.get("status") == "error":
        error = response.get("error")
        allowed = {
            "DUPLICATE_OUTPUT_KEY",
            "INVALID_OUTPUT_PATH",
            "INVALID_REQUEST",
            "MISSING_REQUIRED_METADATA",
            "UNSUPPORTED_OPERATION",
            "UNSUPPORTED_PROTOCOL",
            "UNSUPPORTED_SPEC_VERSION",
            "WRITE_ERROR",
        }
        if (
            not isinstance(error, dict)
            or set(error) != {"code"}
            or error["code"] not in allowed
        ):
            raise ValueError("invalid write profile domain error")
        return
    if response.get("status") != "ok":
        raise ValueError("write response status must be ok or error")
    result = response.get("result")
    if not isinstance(result, dict) or set(result) != {
        "profile_version",
        "spec_version",
        "operations",
    }:
        raise ValueError("invalid write result fields")
    if result["profile_version"] != WRITE_PROFILE_VERSION:
        raise ValueError("unsupported write profile version")
    if result["spec_version"] != "0.3.0":
        raise ValueError("Write Profile v1.1 supports spec version 0.3.0")
    operations = result["operations"]
    if not isinstance(operations, list):
        raise TypeError("operations must be an array")
    keys: list[str] = []
    for operation in operations:
        if not isinstance(operation, dict) or set(operation) != {"kind", "key", "content"}:
            raise ValueError("invalid write operation fields")
        if operation["kind"] != "put":
            raise ValueError("write-v1 Round 1 operations must be put")
        key = operation["key"]
        if not _safe_output_key(key):
            raise ValueError("operation key must be a safe relative POSIX path")
        content = operation["content"]
        if not isinstance(content, str):
            raise TypeError("operation content must be UTF-8 text")
        if key.endswith(".json"):
            try:
                value = json.loads(content)
            except json.JSONDecodeError as exc:
                raise ValueError("JSON operation content must be valid JSON") from exc
            if not isinstance(value, dict):
                raise TypeError("JSON operation content must be an object")
        keys.append(key)
    if keys != sorted(keys) or len(keys) != len(set(keys)):
        raise ValueError("write operations must have sorted unique keys")


def _safe_output_key(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and path.as_posix() == value
        and all(part not in {"", ".", ".."} for part in path.parts)
    )
