#!/usr/bin/env python3
"""평가 결과와 도면 서술문을 텍스트로 내보낸다 → 레포에 커밋되는 형태.

DB(data/rootcause.db)는 레포에 올리지 않는다. 매뉴얼 본문이 들어 있어서다
(제조사 매뉴얼은 재배포 권한이 불명 — data/manuals/SOURCES.md).
그래서 **우리가 만든 것만** 꺼내 남긴다.
  eval/results/eval_runs.csv     실행별 조건 · git sha · 모델
  eval/results/eval_results.csv  사건 × 지표 값 (판정 근거 포함)
  data/manuals/diagram_descriptions.jsonl  도면을 VLM 이 서술한 텍스트

사용: python3 -m eval.export_results
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from app.db import ROOT, connect


def main() -> int:
    con = connect()
    out = ROOT / "eval" / "results"
    out.mkdir(parents=True, exist_ok=True)

    runs = con.execute("SELECT id, started_at, config, git_sha, model_map FROM eval_runs ORDER BY id").fetchall()
    with open(out / "eval_runs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["run_id", "started_at", "label", "ablation", "tiers", "model", "judge", "git_sha"])
        for r in runs:
            c = json.loads(r["config"]); m = json.loads(r["model_map"])
            w.writerow([r["id"], r["started_at"], c.get("label"), c.get("ablation", ""),
                        "|".join(c.get("tiers", [])) if isinstance(c.get("tiers"), list) else c.get("tiers", ""),
                        m.get("diagnoser"), m.get("judge"), r["git_sha"]])

    res = con.execute("SELECT run_id, case_id, tier, metric, value, detail FROM eval_results"
                      " ORDER BY run_id, case_id, metric").fetchall()
    with open(out / "eval_results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["run_id", "case_id", "tier", "metric", "value", "judge_reason"])
        for r in res:
            try:
                reason = json.loads(r["detail"] or "{}").get("_M1_reason", "")
            except (json.JSONDecodeError, AttributeError):
                reason = ""
            w.writerow([r["run_id"], r["case_id"], r["tier"], r["metric"], r["value"], reason])

    pages = con.execute("SELECT doc, page_no, vlm_description FROM manual_pages"
                        " WHERE vlm_description IS NOT NULL AND vlm_description<>''"
                        " ORDER BY doc, page_no").fetchall()
    with open(ROOT / "data" / "manuals" / "diagram_descriptions.jsonl", "w", encoding="utf-8") as f:
        for p in pages:
            f.write(json.dumps({"doc": p["doc"], "page": p["page_no"],
                                "description": p["vlm_description"]}, ensure_ascii=False) + "\n")
    print(f"eval_runs {len(runs)} · eval_results {len(res)} · 도면 서술 {len(pages)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
