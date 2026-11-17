"""Protocol v1, deliberately independent of any Portolan SDK."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "1"
METADATA_VALIDATION_OPERATION = "validate_metadata"
READ_OPERATIONS = frozenset(
    {"inspect", "document", "children", "collections", "items", "assets", "links"}
)
OPERATIONS = READ_OPERATIONS | {METADATA_VALIDATION_OPERATION}
VALIDATION_PROFILE_VERSION = "1"


@dataclass(frozen=True)
class Case:
    id: str
    operation: str
    uri: str
    expected: dict[str, Any]
    tags: tuple[str, ...] = ()
    description: str = ""

    @classmethod
    def from_path(cls, path: Path) -> Case:
        data = json.loads(path.read_text(encoding="utf-8"))
        required = {"id", "operation", "uri", "expected"}
        if not required.issubset(data):
            raise ValueError(f"{path}: missing {required - data.keys()}")
        if data["operation"] not in OPERATIONS:
            raise ValueError(f"{path}: unsupported operation {data['operation']}")
        if data["operation"] == METADATA_VALIDATION_OPERATION:
            validate_metadata_response(data["expected"])
        return cls(
            id=data["id"],
            operation=data["operation"],
            uri=data["uri"],
            expected=data["expected"],
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
