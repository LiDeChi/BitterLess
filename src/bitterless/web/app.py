"""Optional minimal web UI for the research-cycle demo (stdlib only)."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from bitterless.institute.cycle import run_smoke_cycle
from bitterless.models.types import InterventionKind
from bitterless.seed.eastern_zhou import build_seed_world

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>BitterLess · 东周实验室</title>
  <style>
    body { font-family: ui-sans-serif, system-ui, sans-serif; max-width: 880px;
           margin: 2rem auto; padding: 0 1rem; background: #0f1419; color: #e7ecf1; }
    h1 { font-weight: 600; letter-spacing: 0.02em; }
    a, button { color: #7dd3a7; }
    button { background: #1c2a24; border: 1px solid #2f4a3c; padding: 0.5rem 1rem;
             cursor: pointer; border-radius: 6px; }
    button:hover { background: #243830; }
    pre { background: #161b22; padding: 1rem; overflow: auto; border-radius: 8px;
          border: 1px solid #243044; font-size: 12px; }
    .muted { color: #8b9bb4; }
    label { display: block; margin: 0.5rem 0 0.2rem; }
    input { width: 100%; padding: 0.4rem; background: #161b22; border: 1px solid #243044;
            color: #e7ecf1; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>BitterLess · 东周实验室</h1>
  <p class="muted">Phase 1 — research cycle against the Eastern Zhou seed world.</p>
  <form method="POST" action="/run">
    <label>Challenge hypothesis (optional)</label>
    <input name="challenge" placeholder="e.g. 或许关键的是媒介重复而非债务本身"/>
    <label>Change focus dims (optional, comma-separated)</label>
    <input name="change_focus" placeholder="medium,institution"/>
    <p style="margin-top:1rem"><button type="submit">Run research cycle</button></p>
  </form>
  <p class="muted">Or <a href="/run">GET /run</a> for a default cycle JSON.</p>
  __BODY__
</body>
</html>
"""


def _run(challenge: str | None = None, change_focus: str | None = None) -> dict:
    world = build_seed_world()
    interventions = []
    if challenge:
        interventions.append((InterventionKind.CHALLENGE_HYPOTHESIS, challenge))
    if change_focus:
        interventions.append((InterventionKind.CHANGE_FOCUS, change_focus))
    result = run_smoke_cycle(world, interventions=interventions, fork_experiment=True)
    return {
        "result": result.to_dict(),
        "canonical_events": world.timelines.canonical.snapshot_events(),
        "budget": world.budget.to_dict(),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # quieter
        pass

    def _html(self, body: str = "") -> bytes:
        return HTML.replace("__BODY__", body).encode("utf-8")

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(self._html())
            return
        if path == "/run":
            data = _run()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/run":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        form = parse_qs(raw)
        challenge = (form.get("challenge") or [""])[0].strip() or None
        change_focus = (form.get("change_focus") or [""])[0].strip() or None
        data = _run(challenge, change_focus)
        body = "<h2>Result</h2><pre>" + json.dumps(data, ensure_ascii=False, indent=2) + "</pre>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(self._html(body))


def main(argv: list[str] | None = None) -> None:
    import argparse

    p = argparse.ArgumentParser(description="Minimal BitterLess web demo")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args(argv)
    server = HTTPServer((args.host, args.port), Handler)
    print(f"BitterLess web demo at http://{args.host}:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
