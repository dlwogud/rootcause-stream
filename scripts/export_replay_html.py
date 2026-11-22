"""녹화 재생을 **서버 없이** 여는 HTML 파일 하나로 내보낸다.

관제 화면(app/templates/dashboard.html)에 녹화 기록(data/demo_runs/<name>.json)과 그 안에 나오는
사진을 data: URI 로 싣는다. 더블클릭하면 브라우저에서 바로 재생된다 — 발표장 노트북, 오프라인에서도.
이벤트 내용은 손대지 않는다. 재생 화면은 서버 모드의 `/?replay=<name>` 과 같다.

스타일: --tailwind 에 Tailwind CLI(3.4.x) 경로를 주면 쓰는 클래스만 뽑아 CSS 로 넣는다(오프라인 가능).
주지 않으면 CDN 스크립트를 그대로 둔다(인터넷 필요).

사용: .venv/bin/python scripts/export_replay_html.py e323-faces --tailwind <tailwindcss 경로>
→ deck/replay/<name>.html
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jinja2 import Environment, FileSystemLoader  # noqa: E402

TEMPLATE_DIR = ROOT / "app" / "templates"
OUT_DIR = ROOT / "deck" / "replay"
CDN = '<script src="https://cdn.tailwindcss.com"></script>'
ATTRIBUTION = ("용접 사진: L. A. Dominguez Molina, Resistance Spot Welding Insights, Mendeley Data V3 "
               "(doi:10.17632/rwh8kjzdch.3), CC BY 4.0 · 실제 실행 기록을 시간만 압축해 재생")


def _photos(run: dict) -> dict:
    out = {}
    for ev in run["events"]:
        for k in ("photo", "reference"):
            p = ev.get(k)
            if p and p not in out and (ROOT / p).exists():
                out[p] = "data:image/jpeg;base64," + base64.b64encode((ROOT / p).read_bytes()).decode()
    return out


def _tailwind_css(html: str, cli: str) -> str:
    with tempfile.TemporaryDirectory() as d:
        page, src, css = Path(d, "page.html"), Path(d, "in.css"), Path(d, "out.css")
        page.write_text(html, encoding="utf-8")
        src.write_text("@tailwind base;\n@tailwind components;\n@tailwind utilities;\n")
        subprocess.run([cli, "-i", str(src), "-o", str(css), "--content", str(page), "--minify"],
                       check=True, capture_output=True)
        return css.read_text()


def export(name: str, tailwind: str | None = None) -> Path:
    run = json.loads((ROOT / "data" / "demo_runs" / f"{name}.json").read_text())
    from app.main import CASE_BLURB, MODEL, VLM_MODEL, _all_cases
    cases = [{"id": c.case_id, "tier": c.case_id[0], "kind": c.kind, "alarms": c.alarm_count,
              "truth": c.truth_key, "blurb": CASE_BLURB.get(c.case_id[0], "")}
             for c in _all_cases().values() if c.case_id == run["meta"]["case_id"]]
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    html = env.get_template("dashboard.html").render(cases=cases, model=MODEL, vlm=VLM_MODEL)

    embed = {"name": name, "run": run, "photos": _photos(run)}
    blob = json.dumps(embed, ensure_ascii=False).replace("</", "<\\/")
    html = html.replace("<script>\nlet es = null", f"<script>window.__EMBED__ = {blob};</script>\n<script>\nlet es = null", 1)
    html = html.replace("</body>", f'<footer class="px-6 pb-4 text-[11px] text-stone-400">{ATTRIBUTION}</footer>\n</body>', 1)
    if tailwind:
        html = html.replace(CDN, f"<style>{_tailwind_css(html, tailwind)}</style>", 1)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{name}.html"
    out.write_text(html, encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="+", help="data/demo_runs 아래 녹화 이름 (예: e323-faces)")
    ap.add_argument("--tailwind", help="Tailwind CLI 3.4.x 경로 — 주면 오프라인에서도 스타일이 나온다")
    a = ap.parse_args()
    for n in a.name:
        p = export(n, a.tailwind)
        print(f"→ {p}  ({p.stat().st_size / 1024:.0f} KB)")
