#!/usr/bin/env python3
"""성과표 생성 — eval_runs 를 조건별로 나란히 놓는다.

발표자료에 그대로 들어갈 두 표를 만든다.
  ① Tier 별 성과 (주 지표를 Tier 마다 다르게 표기)
  ② 조건 비교 (ablation Δ)

사용: python3 -m eval.report              # 최근 실행 전부
      python3 -m eval.report --runs 1 2   # 특정 run 만
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from app.db import connect

ROOT = Path(__file__).resolve().parents[1]

# Tier 별 주 지표 — 정답의 성격이 다르므로 같은 잣대를 쓰지 않는다
PRIMARY = {
    "A": ("M9b_discriminating_request", "가르는 관측 요청"),
    "B": ("M2_primary_variable", "주 변수 식별"),
    "C": ("M1_match", "근본원인 정확도"),
    "D": ("M1_match", "측정 불성립(한계)"),
}
TIER_LABEL = {"A": "A 실측(원인 특정 불가)", "B": "B 합성(주입)",
              "C": "C 실측(데이터 품질)", "D": "D 구성(측정 불성립)"}
SHOW = ["M1_match", "M1_partial", "M2_primary_variable",
        "M9a_abstained", "M9b_discriminating_request"]
SHORT = {"M1_match": "M1정확", "M1_partial": "M1부분", "M2_primary_variable": "M2변수",
         "M9a_abstained": "M9보류", "M9b_discriminating_request": "M9가름"}


def load_runs(run_ids: list[int] | None = None) -> list[dict]:
    con = connect()
    q = "SELECT id, started_at, config, git_sha FROM eval_runs"
    if run_ids:
        q += f" WHERE id IN ({','.join('?' * len(run_ids))})"
    rows = con.execute(q + " ORDER BY id", run_ids or []).fetchall()
    out = []
    for r in rows:
        cfg = json.loads(r["config"])
        vals = defaultdict(lambda: defaultdict(list))
        for m in con.execute(
                "SELECT tier, metric, value FROM eval_results WHERE run_id=?", (r["id"],)):
            vals[m["tier"]][m["metric"]].append(m["value"])
        out.append({"id": r["id"], "label": cfg.get("label") or cfg.get("diagnoser"),
                    "model": cfg.get("model"), "git": r["git_sha"], "vals": vals})
    con.close()
    return out


def pct(v: list[float]) -> str:
    return f"{sum(v)/len(v)*100:5.1f}%" if v else "    –"


def table_tier(run: dict) -> list[str]:
    L = [f"### run #{run['id']} — {run['label']} (model={run['model']}, git={run['git']})", "",
         f"| Tier | n | {' | '.join(SHORT[m] for m in SHOW)} | 주 지표 |",
         "|---|---:|" + "---:|" * len(SHOW) + "---|"]
    for t in ["A", "C", "B", "D"]:
        if t not in run["vals"]:
            continue
        d = run["vals"][t]
        n = max((len(v) for v in d.values()), default=0)
        cells = " | ".join(pct(d.get(m, [])) for m in SHOW)
        L.append(f"| {TIER_LABEL[t]} | {n} | {cells} | {PRIMARY[t][1]} |")
    return L + [""]


def table_compare(runs: list[dict]) -> list[str]:
    if len(runs) < 2:
        return []
    L = ["### 조건 비교", "",
         "| Tier · 주 지표 | " + " | ".join(f"#{r['id']} {r['label']}" for r in runs) + " |",
         "|---|" + "---:|" * len(runs)]
    for t in ["A", "C", "B", "D"]:
        key, name = PRIMARY[t]
        cells = []
        any_val = False
        for r in runs:
            v = r["vals"].get(t, {}).get(key, [])
            any_val |= bool(v)
            cells.append(pct(v))
        if any_val:
            L.append(f"| {TIER_LABEL[t]} — {name} | " + " | ".join(cells) + " |")
    # 보조 지표도 한 줄씩
    for key in ["M1_partial", "M9a_abstained"]:
        for t in ["A", "B", "C"]:
            vals = [r["vals"].get(t, {}).get(key, []) for r in runs]
            if any(vals):
                L.append(f"| {TIER_LABEL[t]} — {SHORT[key]} | "
                         + " | ".join(pct(v) for v in vals) + " |")
    return L + [""]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="*", type=int)
    ap.add_argument("--out", default="outputs/eval_report.md")
    a = ap.parse_args()

    runs = load_runs(a.runs)
    if not runs:
        print("실행 기록이 없다"); return 1

    lines = ["# 평가 성과표", "",
             "> `python3 -m eval.report` 로 재생성한다. 수치를 손으로 고치지 말 것.",
             "> Tier 별 주 지표가 다르다 — 정답의 성격이 다르기 때문이다"
             " (`eval/metrics/__init__.py`).", ""]
    for r in runs:
        lines += table_tier(r)
    lines += table_compare(runs)

    p = ROOT / a.out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"→ {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
