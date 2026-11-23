#!/usr/bin/env python3
"""평가 하네스 — 케이스 × 진단기 → 지표 → eval_runs/eval_results 기록.

성과표의 재현 가능성을 위해 **git_sha 와 config 를 함께 저장한다.**
선행 프로젝트(kamp-welding)가 산출물 진위 검사를 파이프라인 종료 조건으로
걸었던 방식을 따른다.

사용:
  python3 -m eval.run --diagnoser baseline --model haiku
  python3 -m eval.run --tiers A C --workers 2
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from app.db import connect, init_db, js, DB_PATH
from eval import cases as case_mod
from eval.diagnosers import DIAGNOSERS
from eval.metrics import ALL_METRICS


def git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def record_resolved(con, run_id: int, seen: dict) -> dict:
    """실제로 답한 모델 이름을 eval_runs.model_map 의 "resolved" 에 남긴다.
    코드는 별칭만 넘기고 별칭이 가리키는 버전은 바뀐다 (eval/MODEL_VERSIONS.md)."""
    resolved = {role: sorted(v) for role, v in seen.items() if v}
    row = con.execute("SELECT model_map FROM eval_runs WHERE id=?", (run_id,)).fetchone()
    mm = json.loads(row[0]) if row and row[0] else {}
    mm["resolved"] = resolved
    con.execute("UPDATE eval_runs SET model_map=? WHERE id=?", (json.dumps(mm, ensure_ascii=False), run_id))
    con.commit()
    return resolved


def score_one(case, diagnoser, model, judge_model, ablation=None, max_steps=9) -> tuple[dict, dict]:
    result = diagnoser(case, model=model, ablation=ablation, max_steps=max_steps)
    scores: dict = {}
    for fn in ALL_METRICS:
        scores.update(fn(case, result, judge_model=judge_model))
    # 결론 원문을 남긴다 — 정답지를 고쳤을 때 다시 채점할 수 있어야 한다(2026-11-17 교훈)
    scores["_root_cause"] = str(result.get("root_cause") or "")[:1500]
    u = result.get("_usage") or {}
    scores["_diagnoser_models"] = u.get("models") or ([u["model"]] if u.get("model") else [])
    return result, scores


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--diagnoser", default="baseline", choices=list(DIAGNOSERS))
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--judge-model", default="sonnet")
    ap.add_argument("--tiers", nargs="*", default=["A", "B", "C"])
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--label", default="", help="성과표에 붙일 이름 (ablation 조건명)")
    ap.add_argument("--rebuild-cases", action="store_true")
    ap.add_argument("--no-tool", nargs="*", default=[],
                    choices=["query_timeseries", "search_manual", "lookup_diagram",
                             "recall_cases", "query_sql"], help="끌 도구 (ablation)")
    ap.add_argument("--no-signal-guide", action="store_true")
    ap.add_argument("--no-photo", action="store_true")
    ap.add_argument("--extra-tool", nargs="*", default=[], choices=["query_sql"],
                    help="기본으로 꺼진 도구를 켠다")
    ap.add_argument("--max-steps", type=int, default=9)
    ap.add_argument("--search-mode", default="hybrid_rerank",
                    choices=["vector", "bm25", "hybrid", "hybrid_rerank"])
    a = ap.parse_args()

    if a.rebuild_cases or not (case_mod.CASES_DIR / "cases.jsonl").exists():
        case_mod.save(case_mod.build_all())
    cs = [c for c in case_mod.load() if c.tier in a.tiers]
    if not cs:
        print("케이스 없음", file=sys.stderr); return 2

    if not DB_PATH.exists():
        init_db()
    con = connect()
    cfg = {"diagnoser": a.diagnoser, "model": a.model, "judge_model": a.judge_model,
           "tiers": a.tiers, "label": a.label or a.diagnoser}
    run_id = con.execute(
        "INSERT INTO eval_runs (started_at, config, git_sha, model_map) VALUES (?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(), js(cfg), git_sha(),
         js({"diagnoser": a.model, "judge": a.judge_model}))).lastrowid
    con.commit()

    from app.agent.loop import Ablation
    ab = Ablation(disabled_tools=tuple(a.no_tool), signal_guide=not a.no_signal_guide,
                  allow_photo=not a.no_photo, search_mode=a.search_mode,
                  extra_tools=tuple(a.extra_tool))
    cfg["ablation"] = ab.label()
    cfg["max_steps"] = a.max_steps
    con.execute("UPDATE eval_runs SET config=? WHERE id=?", (js(cfg), run_id))
    con.commit()
    fn = DIAGNOSERS[a.diagnoser]
    print(f"run #{run_id} · {cfg['label']} · 케이스 {len(cs)}건 · 동시 {a.workers}\n")

    rows, cost, errs = [], 0.0, 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(score_one, c, fn, a.model, a.judge_model, ab, a.max_steps): c for c in cs}
        for fut in as_completed(futs):
            c = futs[fut]
            try:
                result, scores = fut.result()
            except Exception as e:
                errs += 1
                print(f"  ! {c.case_id}: {type(e).__name__}: {str(e)[:110]}", file=sys.stderr)
                continue
            cost += (result.get("_usage") or {}).get("cost_cc", 0.0)
            rows.append((c, result, scores))
            prim = {"B": "M2_primary_variable"}.get(c.tier, "M1_match")
            sec = "M1_partial"
            mark = "✅" if scores.get(prim) else ("🟡" if scores.get(sec) else "❌")
            print(f"  {mark} {c.case_id:22s} {str(result.get('root_cause',''))[:62]}")
            if not scores.get(prim) and scores.get("_M1_reason"):
                print(f"       판정: {scores.get('_M1_reason','')[:96]}")

            for metric, value in scores.items():
                if metric.startswith("_"):
                    continue
                con.execute(
                    "INSERT OR REPLACE INTO eval_results"
                    " (run_id, case_id, tier, metric, value, detail) VALUES (?,?,?,?,?,?)",
                    (run_id, c.case_id, c.tier, metric, float(value),
                     js({k: v for k, v in scores.items() if k.startswith("_")})))
            con.commit()

    seen: dict = {"diagnoser": set(), "judge": set()}
    for _, _, s in rows:
        seen["diagnoser"].update(s.get("_diagnoser_models") or [])
        if s.get("_M1_judge"):
            seen["judge"].add(s["_M1_judge"])
    record_resolved(con, run_id, seen)

    # ── 성과표 ────────────────────────────────────────────────
    by_tier = defaultdict(lambda: defaultdict(list))
    for c, _, s in rows:
        for k, v in s.items():
            if not k.startswith("_"):
                by_tier[c.tier][k].append(v)

    def avg(d, k):
        v = d.get(k, [])
        return f"{sum(v)/len(v)*100:6.1f}%" if v else "     –"

    print(f"\n{'='*76}\nrun #{run_id} — {cfg['label']} (model={a.model}, judge={a.judge_model})")
    print("Tier 별 주 지표가 다르다 — 정답의 성격이 다르기 때문이다\n")
    print(f"{'Tier':5s} {'n':>3s} {'M1정확':>7s} {'M1부분':>7s} {'M2변수':>7s} "
          f"{'M9보류':>7s} {'M9가름':>7s}  주 지표")
    PRIMARY = {"A": "M1 (근본원인) — 2026-11-17 정답 정정", "B": "M2 (주 변수) ※합성",
               "C": "M1 (근본원인)", "D": "측정 불성립 — RESULTS_TIER_D.md"}
    for t in ["A", "C", "B", "D"]:
        if t not in by_tier:
            continue
        d = by_tier[t]
        n = max((len(v) for v in d.values()), default=0)
        print(f"{t:5s} {n:3d} {avg(d,'M1_match')} {avg(d,'M1_partial')} "
              f"{avg(d,'M2_primary_variable')} {avg(d,'M9a_abstained')} "
              f"{avg(d,'M9b_discriminating_request')}  {PRIMARY.get(t,'')}")
    print(f"\n실패 {errs}건 · 구독 사용량 환산 ${cost:.3f} (Claude Code 오버헤드 포함)")
    print(f"→ eval_runs #{run_id}, git {git_sha()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
