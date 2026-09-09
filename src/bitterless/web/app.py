"""Web demo + 3D institute space (stdlib HTTP server, Three.js static assets)."""

from __future__ import annotations

import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from bitterless.institute.cycle import ResearchCycle, run_smoke_cycle
from bitterless.institute.researcher import ResearchThread
from bitterless.models.types import InterventionKind, ProvenanceKind
from bitterless.seed.eastern_zhou import build_seed_world

STATIC_ROOT = Path(__file__).resolve().parent / "static"

# ---------------------------------------------------------------------------
# Lab session — shared world + research thread for live 3D / API
# ---------------------------------------------------------------------------


class LabSession:
    """Persistent institute session backing the web/3D surface."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self.world = build_seed_world()
            self.thread = ResearchThread()
            self.last_result: dict[str, Any] | None = None
            self.cycle_count = 0
            # Seed sealed / failed models as lab culture (not sim kernel rewrite)
            self.sealed_models = [
                {
                    "id": "M-003",
                    "title": "商人=贪婪",
                    "status": "sealed",
                    "epitaph": "标签式自我验证；已封存为反面教材",
                    "failed_at_tick": -1,
                },
                {
                    "id": "M-007",
                    "title": "统一全图精度",
                    "status": "sealed",
                    "epitaph": "资源耗尽；多尺度被证明必要",
                    "failed_at_tick": -1,
                },
                {
                    "id": "M-012",
                    "title": "死亡即删除",
                    "status": "sealed",
                    "epitaph": "违背「人死媒介留」；封存",
                    "failed_at_tick": -1,
                },
            ]
            self.photo_wall = self._seed_xianying()

    def _seed_xianying(self) -> list[dict[str, Any]]:
        """显影 frames: 史料约束 + model + viewpoint + time → projection + provenance."""
        return [
            {
                "id": "xy-01",
                "title": "庭中低语 · 东门查验",
                "caption": "青在庭中听见东门传言；非穿越摄影",
                "viewpoint": "庭中 · 听者视角",
                "tick": 0,
                "provenance": ProvenanceKind.COMPUTED.value,
                "constraints": ["口传媒介可达", "种子硬事实：东门近市"],
                "model_note": "初始低分辨率东周近似",
            },
            {
                "id": "xy-02",
                "title": "书简 · 粮债约言",
                "caption": "史小所记「商氏负里老粮」",
                "viewpoint": "书手案前",
                "tick": 0,
                "provenance": ProvenanceKind.HARD_FACT.value,
                "constraints": ["简牍可达史小/里老", "债务关系 hard fact"],
                "model_note": "媒介=书简 channel",
            },
            {
                "id": "xy-03",
                "title": "里社萌芽 · 共祭轮廓",
                "caption": "形成中的制度；细节为重建则须标 reconstruction",
                "viewpoint": "里中沙盘俯视",
                "tick": 0,
                "provenance": ProvenanceKind.HYPOTHESIS.value,
                "constraints": ["里社 forming=True", "成员：里老/史小/青"],
                "model_note": "制度尚未固化",
            },
        ]

    def run_cycle(
        self,
        *,
        challenge: str | None = None,
        change_focus: str | None = None,
        fork: bool = True,
    ) -> dict[str, Any]:
        with self._lock:
            interventions: list[tuple[InterventionKind, str]] = []
            if challenge:
                interventions.append((InterventionKind.CHALLENGE_HYPOTHESIS, challenge))
            if change_focus:
                interventions.append((InterventionKind.CHANGE_FOCUS, change_focus))
            cycle = ResearchCycle(world=self.world, thread=self.thread)
            for kind, content in interventions:
                cycle.queue_intervention(kind, content)
            result = cycle.run(fork_experiment=fork and self.cycle_count == 0)
            self.cycle_count += 1
            self.last_result = result.to_dict()
            # Refresh 显影 captions from live focus / evidence when available
            self._refresh_photos_from_result(result)
            return self._state_unlocked()

    def _refresh_photos_from_result(self, result: Any) -> None:
        """Attach latest cycle focus onto photo wall as living institute material."""
        focus = result.focus or {}
        dims = focus.get("dims") or focus.get("dimensions") or []
        if isinstance(dims, dict):
            dims = list(dims.keys())
        tick = result.world_tick
        self.photo_wall.append(
            {
                "id": f"xy-cycle-{self.cycle_count}",
                "title": f"循环 #{self.cycle_count} · 聚焦显影",
                "caption": (result.new_problem or "（无新问题）")[:120],
                "viewpoint": f"研究所聚焦 dims={dims}",
                "tick": tick,
                "provenance": ProvenanceKind.COMPUTED.value,
                "constraints": [f"focus={focus}"],
                "model_note": (self.thread.current_model_summary or "")[:160],
            }
        )
        # Keep wall bounded
        if len(self.photo_wall) > 12:
            self.photo_wall = self.photo_wall[:3] + self.photo_wall[-9:]

    def state(self) -> dict[str, Any]:
        with self._lock:
            return self._state_unlocked()

    def _state_unlocked(self) -> dict[str, Any]:
        w = self.world
        t = self.thread
        people = {
            pid: {
                "id": p.id,
                "name": p.name,
                "role_hint": p.role_hint,
                "alive": p.alive,
                "location": p.location,
                "economy": dict(p.economy),
                "hard_facts": list(p.hard_facts),
            }
            for pid, p in w.people.items()
        }
        return {
            "tick": w.tick,
            "cycle_count": self.cycle_count,
            "place": (w.low_res_summary or {}).get("place", "东周小邑"),
            "research_thread": {
                "researcher_name": t.researcher_name,
                "current_problem": t.current_problem,
                "current_model_summary": t.current_model_summary,
                "current_hypothesis": t.current_hypothesis,
                "current_focus_dims": [d.value for d in t.current_focus_dims],
                "current_focus_targets": list(t.current_focus_targets),
                "anomalies": list(t.anomalies[-3:]),
                "steps": [s.to_dict() for s in t.steps[-12:]],
                "challenged": t.challenged,
            },
            "focus": dict(w.focus) if w.focus else {},
            "compression_snapshot": (
                self.last_result.get("compression_snapshot") if self.last_result else {}
            ),
            "last_result": self.last_result,
            "timeline": {
                "mode": "canonical",
                "canonical_events": [
                    {
                        "tick": e.tick,
                        "kind": e.kind,
                        "summary": e.summary,
                    }
                    for e in w.timelines.canonical.events[-20:]
                ],
                "experimental": [
                    {
                        "id": br.id,
                        "name": br.name,
                        "fork_tick": br.fork_tick,
                        "events": len(br.events),
                    }
                    for br in w.timelines.experimental
                ],
            },
            "people": people,
            "channels": {cid: c.to_dict() for cid, c in w.channels.items()},
            "institutions": {iid: i.to_dict() for iid, i in w.institutions.items()},
            "mechanisms": [m.to_dict() for m in w.mechanisms],
            "budget": w.budget.to_dict(),
            "sealed_models": list(self.sealed_models),
            "photo_wall": list(self.photo_wall),
            "materials": {
                "bamboo_slips": [
                    {
                        "id": "slip-debt",
                        "text": "约：商氏负里老粮，待还",
                        "channel": "书简",
                    },
                    {
                        "id": "slip-rite",
                        "text": "里社：季节共祭；约言须有见证",
                        "channel": "制度萌芽",
                    },
                ],
                "sand_table": {
                    "title": "小邑沙盘",
                    "nodes": [
                        {"id": "东门近市", "label": "东门近市", "x": 0.8, "z": 0.2},
                        {"id": "里中", "label": "里中", "x": 0.4, "z": 0.5},
                        {"id": "庭中", "label": "庭中", "x": 0.45, "z": 0.65},
                    ],
                    "note": "低分辨率空间近似；非全图精度",
                },
            },
        }


SESSION = LabSession()

# ---------------------------------------------------------------------------
# Legacy Phase-1 HTML form (kept intact)
# ---------------------------------------------------------------------------

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
    .cta { margin: 1.25rem 0; padding: 1rem; border: 1px solid #3d5a4a;
           border-radius: 8px; background: #15201a; }
  </style>
</head>
<body>
  <h1>BitterLess · 东周实验室</h1>
  <p class="muted">Phase 1 — research cycle against the Eastern Zhou seed world.</p>
  <div class="cta">
    <strong>3D 研究所空间</strong>
    <p class="muted" style="margin:0.4rem 0 0.8rem">研究室 · 艺术工作室 · 档案 · 博物馆 — geek + artist</p>
    <p><a href="/institute/">打开 3D Institute →</a></p>
  </div>
  <form method="POST" action="/run">
    <label>Challenge hypothesis (optional)</label>
    <input name="challenge" placeholder="e.g. 或许关键的是媒介重复而非债务本身"/>
    <label>Change focus dims (optional, comma-separated)</label>
    <input name="change_focus" placeholder="medium,institution"/>
    <p style="margin-top:1rem"><button type="submit">Run research cycle</button></p>
  </form>
  <p class="muted">Or <a href="/run">GET /run</a> for a default cycle JSON.
     Live state: <a href="/api/state">/api/state</a></p>
  __BODY__
</body>
</html>
"""


def _run_legacy(challenge: str | None = None, change_focus: str | None = None) -> dict:
    """One-shot cycle (legacy form) — does not mutate the live LabSession."""
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


def _json_bytes(data: Any, status: int = 200) -> tuple[int, bytes, str]:
    body = json.dumps(data, ensure_ascii=False, indent=2, default=str).encode("utf-8")
    return status, body, "application/json; charset=utf-8"


def _resolve_static(path: str) -> Path | None:
    """Map URL path under /institute/ to a file in static/institute/."""
    rel = path[len("/institute/") :] if path.startswith("/institute/") else ""
    if path.rstrip("/") == "/institute":
        rel = "index.html"
    if not rel or rel.endswith("/"):
        rel = (rel or "") + "index.html"
    # Normalize and prevent traversal
    candidate = (STATIC_ROOT / "institute" / rel).resolve()
    root = (STATIC_ROOT / "institute").resolve()
    if not str(candidate).startswith(str(root)):
        return None
    if candidate.is_file():
        return candidate
    return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # quieter
        pass

    def _html(self, body: str = "") -> bytes:
        return HTML.replace("__BODY__", body).encode("utf-8")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_or_form(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        ctype = (self.headers.get("Content-Type") or "").lower()
        if "application/json" in ctype:
            try:
                return json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return {}
        form = parse_qs(raw)
        return {k: (v[0] if v else "") for k, v in form.items()}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._send(200, self._html(), "text/html; charset=utf-8")
            return

        if path in ("/institute", "/institute/"):
            target = _resolve_static("/institute/")
            if target:
                data = target.read_bytes()
                self._send(200, data, "text/html; charset=utf-8")
                return
            self._send(404, b"institute assets missing", "text/plain; charset=utf-8")
            return

        if path.startswith("/institute/"):
            target = _resolve_static(path)
            if target:
                mime, _ = mimetypes.guess_type(str(target))
                self._send(200, target.read_bytes(), mime or "application/octet-stream")
                return
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return

        if path == "/api/state":
            status, body, ctype = _json_bytes(SESSION.state())
            self._send(status, body, ctype)
            return

        if path == "/api/health":
            status, body, ctype = _json_bytes(
                {
                    "ok": True,
                    "institute_index": (_resolve_static("/institute/") is not None),
                    "static_root": str(STATIC_ROOT),
                }
            )
            self._send(status, body, ctype)
            return

        if path == "/run":
            data = _run_legacy()
            status, body, ctype = _json_bytes(data)
            self._send(status, body, ctype)
            return

        self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path

        if path == "/api/cycle":
            payload = self._read_json_or_form()
            challenge = (payload.get("challenge") or "").strip() or None
            change_focus = (payload.get("change_focus") or "").strip() or None
            fork = bool(payload.get("fork", True))
            data = SESSION.run_cycle(
                challenge=challenge, change_focus=change_focus, fork=fork
            )
            status, body, ctype = _json_bytes(data)
            self._send(status, body, ctype)
            return

        if path == "/api/reset":
            SESSION.reset()
            status, body, ctype = _json_bytes(SESSION.state())
            self._send(status, body, ctype)
            return

        if path == "/run":
            payload = self._read_json_or_form()
            challenge = (payload.get("challenge") or "").strip() or None
            change_focus = (payload.get("change_focus") or "").strip() or None
            data = _run_legacy(challenge, change_focus)
            body_html = (
                "<h2>Result</h2><pre>"
                + json.dumps(data, ensure_ascii=False, indent=2)
                + "</pre>"
            )
            self._send(200, self._html(body_html), "text/html; charset=utf-8")
            return

        self._send(404, b"not found", "text/plain; charset=utf-8")


def main(argv: list[str] | None = None) -> None:
    import argparse

    p = argparse.ArgumentParser(description="BitterLess web demo + 3D institute")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args(argv)
    server = HTTPServer((args.host, args.port), Handler)
    print(f"BitterLess web demo at http://{args.host}:{args.port}/")
    print(f"3D Institute        at http://{args.host}:{args.port}/institute/")
    print(f"Live API state      at http://{args.host}:{args.port}/api/state")
    server.serve_forever()


if __name__ == "__main__":
    main()
