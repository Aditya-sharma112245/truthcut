from __future__ import annotations
import html, json
from pathlib import Path

def render_report(run_dir: str | Path, output: str | Path) -> None:
    run_dir, output = Path(run_dir), Path(output)
    plans = []
    for path in sorted(run_dir.glob("*_trailer.json")):
        plans.append(json.loads(path.read_text(encoding="utf-8")))
    cards = []
    for p in plans:
        segs = "".join(f"<li><b>{html.escape(s['source_in'])}–{html.escape(s['source_out'])}</b> · {html.escape(s['video'])}<br><small>{html.escape(s['claim'])}</small></li>" for s in p['segments'])
        warnings = "".join(f"<li>{html.escape(w)}</li>" for w in p.get('warnings', [])) or "<li>None</li>"
        cards.append(f"<article><div class='pill'>{html.escape(p['validation_status'])}</div><h2>{html.escape(p['audience'])}</h2><p>{html.escape(p['audience_promise'])}</p><h3>EDL timeline · {p['duration_seconds']}s</h3><ol>{segs}</ol><h3>Warnings / approvals</h3><ul>{warnings}</ul></article>")
    page = f"""<!doctype html><html><head><meta charset='utf-8'><title>TruthCut EDL Inspector</title><style>body{{font:16px system-ui;background:#10141d;color:#eaf0f6;margin:40px}}main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px}}article{{background:#182232;border:1px solid #33465f;border-radius:16px;padding:22px;box-shadow:0 8px 24px #0004}}h1{{font-size:42px;margin-bottom:4px}}h2{{text-transform:capitalize}}h3{{color:#8fd3ff;font-size:14px;text-transform:uppercase;letter-spacing:.08em}}.pill{{display:inline-block;border-radius:99px;padding:6px 10px;background:#164e3b;color:#b5f5d6;font-size:12px;font-weight:700}}li{{margin:10px 0}}small{{color:#a9bbce}}</style></head><body><h1>TruthCut</h1><p>Auditable audience-aware trailer decisions. Director proposes; Auditor proves.</p><main>{''.join(cards)}</main></body></html>"""
    output.write_text(page, encoding="utf-8")
