#!/usr/bin/env python3
"""저장된 결론 원문(_root_cause)을 현재 정답지로 다시 채점한다 — M1 만.

정답지를 정정했을 때 Agent 를 다시 돌리지 않고 채점만 다시 하기 위한 도구다.
결론 원문이 없는 실행(2026-11-17 이전)은 채점할 수 없으므로 건너뛴다.

사용: .venv/bin/python -m eval.regrade --runs 30-47 --tiers A
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor

from app.db import connect, js
from eval.cases import load
from eval.metrics.m1_rootcause import m1_rootcause


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True, help="예: 30-47")
    ap.add_argument("--tiers", nargs="*", default=["A"])
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    lo, hi = map(int, a.runs.split("-"))
    cases = {c.case_id: c for c in load()}
    con = connect()
    rows = con.execute(
        "SELECT run_id, case_id, tier, detail FROM eval_results WHERE run_id BETWEEN ? AND ?"
        f" AND tier IN ({','.join('?' * len(a.tiers))}) GROUP BY run_id, case_id",
        (lo, hi, *a.tiers)).fetchall()
    jobs = []
    for r in rows:
        d = json.loads(r["detail"] or "{}")
        if "_root_cause" not in d:
            print(f"  건너뜀 run {r['run_id']} {r['case_id']}: 결론 원문 없음")
            continue
        jobs.append((r["run_id"], r["case_id"], r["tier"], d))

    def grade(j):
        run_id, cid, tier, d = j
        return j, m1_rootcause(cases[cid], {"root_cause": d["_root_cause"]})

    with ThreadPoolExecutor(a.workers) as ex:
        for (run_id, cid, tier, d), s in ex.map(grade, jobs):
            detail = {**d, **{k: v for k, v in s.items() if k.startswith("_")}}
            for m in ("M1_match", "M1_partial"):
                con.execute("INSERT OR REPLACE INTO eval_results"
                            " (run_id, case_id, tier, metric, value, detail) VALUES (?,?,?,?,?,?)",
                            (run_id, cid, tier, m, s[m], js(detail)))
            con.commit()
            mark = "✅" if s["M1_match"] else ("🟡" if s["M1_partial"] else "❌")
            print(f"  {mark} run {run_id:3d} {cid}  {s.get('_M1_reason','')[:90]}")
    print(f"재채점 {len(jobs)}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
