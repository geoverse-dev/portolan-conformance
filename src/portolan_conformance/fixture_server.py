"""Deterministic local HTTP transport for read-profile fixtures."""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator


class _Handler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/__delay/basic":
            time.sleep(0.05)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")
            return
        if self.path == "/__body/truncated":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"type":"Catalog"')
            return
        if self.path == "/__media/text-plain":
            body = (
                b'{"type":"Catalog","stac_version":"1.1.0",'
                b'"id":"wrong-media-type","title":"Wrong media type",'
                b'"description":"Valid JSON served as text/plain","links":[]}'
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/__status/403":
            self.send_error(403, "Forbidden")
            return
        if self.path == "/__status/404":
            self.send_error(404, "Not Found")
            return
        if self.path == "/__status/500":
            self.send_error(500, "Internal Server Error")
            return
        if self.path == "/__redirect/final-base":
            self.send_response(302)
            self.send_header("Location", "/redirected/catalog.json")
            self.end_headers()
            return
        if self.path == "/redirect/nested-items":
            self.send_response(302)
            self.send_header("Location", "/nested-items/collection.json")
            self.end_headers()
            return
        super().do_GET()

    def log_message(self, format: str, *args: object) -> None:
        pass


@contextmanager
def fixture_http_server(catalogs_root: Path) -> Iterator[str]:
    """Serve fixture catalogs on an ephemeral loopback port."""
    handler = partial(_Handler, directory=str(catalogs_root.resolve()))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
