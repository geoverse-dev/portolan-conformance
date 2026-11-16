"""Fixture-only reference adapter to self-test the harness. NOT a Portolan SDK.

Do not use this as a behavioral oracle: the expectations in fixtures/cases require
independent review, and the adapter exists solely to exercise the protocol.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote


def read(uri: str) -> dict:
    parts = urlsplit(uri)
    if parts.scheme != "file":
        raise ValueError("Fixture adapter supports file:// only")
    path = Path(unquote(parts.path))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LookupError("NOT_FOUND") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("INVALID_JSON") from exc


def target_type(doc: dict) -> str:
    return doc.get("type", "")


def summarize(doc: dict, uri: str) -> dict:
    return {"type": doc.get("type"), "id": doc.get("id"), "title": doc.get("title"),
            "description": doc.get("description"), "stac_version": doc.get("stac_version"),
            "stac_extensions": doc.get("stac_extensions", [])}


def main() -> int:
    try:
        request = json.loads(sys.stdin.readline())
        if request.get("protocol_version") != "1":
            raise ValueError("UNSUPPORTED_PROTOCOL")
        op, uri = request["operation"], request["uri"]
        doc = read(uri)
        links = doc.get("links", [])
        if op == "inspect":
            result = summarize(doc, uri)
        elif op == "document":
            result = {"document": doc}
        elif op in ("children", "collections", "items"):
            rels = {"children": {"child"}, "collections": {"child"}, "items": {"item"}}[op]
            if op == "collections":
                # Traverses nested catalogs, but never treats items as collections.
                def walk(d, base, visited):
                    if base in visited: return []
                    visited.add(base)
                    out = []
                    for link in d.get("links", []):
                        if link.get("rel") != "child": continue
                        dest = urljoin(base, link["href"])
                        child = read(dest)
                        if child.get("type") == "Collection": out.append({"id": child["id"], "uri": dest})
                        elif child.get("type") == "Catalog": out.extend(walk(child, dest, visited))
                    return out
                result = {"entries": sorted(walk(doc, uri, set()), key=lambda e:(e["id"], e["uri"]))}
            else:
                result = {"entries": sorted([{"id": read(urljoin(uri,l["href"]))["id"], "uri": urljoin(uri,l["href"])}
                           for l in links if l.get("rel") in rels], key=lambda e:(e["id"],e["uri"]))}
        elif op == "assets":
            result = {"entries": sorted([{"key": key, "href": asset["href"],
                "resolved_href": urljoin(uri, asset["href"]), "type": asset.get("type"),
                "roles": asset.get("roles", []), "title": asset.get("title"),
                "description": asset.get("description"),
                "extra_fields": {k:v for k,v in asset.items() if k not in {"href","type","roles","title","description"}}}
                for key, asset in doc.get("assets", {}).items()], key=lambda e:e["key"])}
        elif op == "links":
            result = {"entries": sorted([{"rel": l["rel"], "href": l["href"],
                "resolved_href": urljoin(uri,l["href"]), "type": l.get("type"),
                "title": l.get("title"),
                "extra_fields": {k:v for k,v in l.items() if k not in {"rel","href","type","title"}}}
                for l in links], key=lambda e:(e["rel"],e["href"]))}
        else:
            raise ValueError("UNSUPPORTED_OPERATION")
        print(json.dumps({"status":"ok","result":result},ensure_ascii=False))
    except Exception as exc:
        code = str(exc)
        if code not in {"NOT_FOUND","INVALID_JSON","UNSUPPORTED_PROTOCOL","UNSUPPORTED_OPERATION"}:
            code = "READ_ERROR"
        print(json.dumps({"status":"error","error":{"code":code}}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
