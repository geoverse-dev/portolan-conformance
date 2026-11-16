"""Protocol v1, deliberately independent of any Portolan SDK."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "1"
OPERATIONS = frozenset({"inspect", "document", "children", "collections", "items", "assets", "links"})

@dataclass(frozen=True)
class Case:
    id: str
    operation: str
    uri: str
    expected: dict[str, Any]
    tags: tuple[str, ...] = ()
    description: str = ""

    @classmethod
    def from_path(cls, path: Path) -> "Case":
        data = json.loads(path.read_text(encoding="utf-8"))
        required = {"id", "operation", "uri", "expected"}
        if not required.issubset(data):
            raise ValueError(f"{path}: missing {required - data.keys()}")
        if data["operation"] not in OPERATIONS:
            raise ValueError(f"{path}: unsupported operation {data['operation']}")
        return cls(id=data["id"], operation=data["operation"], uri=data["uri"],
                   expected=data["expected"], tags=tuple(data.get("tags", [])),
                   description=data.get("description", ""))

def load_cases(root: Path) -> list[Case]:
    cases = [Case.from_path(p) for p in sorted(root.glob("*.json"))]
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case IDs")
    if not cases:
        raise ValueError(f"No cases in {root}")
    return cases
