"""녹화 재생을 **서버 없이** 여는 HTML 파일 하나로 내보낸다.

관제 화면(app/templates/dashboard.html)에 녹화 기록(data/demo_runs/<name>.json)과 그 안에 나오는
사진을 data: URI 로 싣는다. 더블클릭하면 브라우저에서 바로 재생된다 — 발표장 노트북, 오프라인에서도.
이벤트 내용은 손대지 않는다. 재생 화면은 서버 모드의 `/?replay=<name>` 과 같다.

스타일: --tailwind 에 Tailwind CLI(3.4.x) 경로를 주면 쓰는 클래스만 뽑아 CSS 로 넣는다(오프라인 가능).
주지 않으면 CDN 스크립트를 그대로 둔다(인터넷 필요).

녹화를 여러 개 주면 한 파일에 담는다 — 왼쪽 사건을 누르면 그 사건의 기록이 재생된다.

사용: .venv/bin/python scripts/export_replay_html.py e323-ko e357-ko a25-ko --out demo --tailwind <tailwindcss 경로>
→ deck/replay/<out>.html (out 을 주지 않으면 첫 녹화 이름)
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


# 재생 파일의 사건 목록에 보일 한 줄 설명
LABELS = {
    "e323-ko": "날림 불량 — 기록으론 애매, 사진으로 찾아냄",
    "e357-ko": "정상 용접 — 양면 사진을 보고 정상 확인",
    "a25-ko": "공장 데이터 — 사진 없이 기록만으로 원인 추적",
}


def _photos(runs: list) -> dict:
    out = {}
    for ev in (e for run in runs for e in run["events"]):
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


def export(names: list[str] | str, tailwind: str | None = None, out_name: str | None = None) -> Path:
    names = [names] if isinstance(names, str) else list(names)
    runs = {n: json.loads((ROOT / "data" / "demo_runs" / f"{n}.json").read_text()) for n in names}
    from app.main import CASE_BLURB, MODEL, VLM_MODEL, _all_cases
    allc = _all_cases()
    cases = []
    for n in names:
        c = allc[runs[n]["meta"]["case_id"]]
        cases.append({"id": c.case_id, "tier": c.case_id[0], "kind": c.kind, "alarms": c.alarm_count,
                      "truth": c.truth_key, "blurb": LABELS.get(n) or CASE_BLURB.get(c.case_id[0], "")})
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    html = env.get_template("dashboard.html").render(cases=cases, model=MODEL, vlm=VLM_MODEL)

    embed = {"order": names, "runs": runs, "photos": _photos(list(runs.values()))}
    blob = json.dumps(embed, ensure_ascii=False).replace("</", "<\\/")
    html = html.replace("<script>\nlet es = null", f"<script>window.__EMBED__ = {blob};</script>\n<script>\nlet es = null", 1)
    html = html.replace("</body>", f'<footer class="px-6 pb-4 text-[11px] text-stone-400">{ATTRIBUTION}</footer>\n</body>', 1)
    if tailwind:
        html = html.replace(CDN, f"<style>{_tailwind_css(html, tailwind)}</style>", 1)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{out_name or names[0]}.html"
    out.write_text(html, encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="+", help="data/demo_runs 아래 녹화 이름 (예: e323-ko e357-ko a25-ko)")
    ap.add_argument("--out", help="출력 파일 이름 (기본: 첫 녹화 이름)")
    ap.add_argument("--tailwind", help="Tailwind CLI 3.4.x 경로 — 주면 오프라인에서도 스타일이 나온다")
    a = ap.parse_args()
    p = export(a.name, a.tailwind, a.out)
    print(f"→ {p}  ({p.stat().st_size / 1024:.0f} KB, 녹화 {len(a.name)}개)")
