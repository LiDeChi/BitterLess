"""Smoke tests for 3D institute static assets and web routes."""

from __future__ import annotations

import json
from pathlib import Path

from bitterless.web import app as webapp


STATIC = Path(webapp.STATIC_ROOT) / "institute"


def test_institute_static_assets_exist():
    assert (STATIC / "index.html").is_file()
    assert (STATIC / "css" / "institute.css").is_file()
    assert (STATIC / "js" / "main.js").is_file()
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert "main.js" in html
    js = (STATIC / "js" / "main.js").read_text(encoding="utf-8")
    assert "Research Thread" in js or "fetchState" in js


def test_resolve_static_index():
    p = webapp._resolve_static("/institute/")
    assert p is not None and p.name == "index.html"
    assert webapp._resolve_static("/institute/../../../etc/passwd") is None


def test_health_and_institute_routes():
    webapp.SESSION.reset()
    server = webapp.HTTPServer(("127.0.0.1", 0), webapp.Handler)
    host, port = server.server_address
    import threading
    import urllib.request

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://{host}:{port}"
        with urllib.request.urlopen(base + "/api/health", timeout=3) as r:
            assert r.status == 200
            data = json.loads(r.read().decode())
            assert data["ok"] is True
            assert data["institute_index"] is True
        with urllib.request.urlopen(base + "/institute/", timeout=3) as r:
            assert r.status == 200
            body = r.read().decode()
            assert "canvas" in body or "main.js" in body
        with urllib.request.urlopen(base + "/api/state", timeout=3) as r:
            assert r.status == 200
            st = json.loads(r.read().decode())
            assert "research_thread" in st
            assert "timeline" in st
            assert "photo_wall" in st
            assert "sealed_models" in st
        req = urllib.request.Request(
            base + "/api/cycle",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            assert r.status == 200
            after = json.loads(r.read().decode())
            assert after["cycle_count"] >= 1
            assert after["tick"] >= 1
            assert after["research_thread"]["steps"]
    finally:
        server.shutdown()
