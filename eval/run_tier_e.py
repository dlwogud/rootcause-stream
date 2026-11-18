#!/usr/bin/env python3
"""Tier E 실행기 — 실제 용접·실제 사진으로 사진 루프의 효과를 잰다 (eval/tier_e.py).

조건 (같은 사건, 같은 Agent, 같은 코드 경로 — 다른 것은 촬영 요청에 돌아가는 응답뿐)
  photo : Agent 가 용접부 촬영을 요청하면 **그 용접의 사진**을 준다
  swap  : 같은 요청에 **반대 판정을 받은 다른 용접의 사진**을 준다 (내용을 정말 쓰는지)
  none  : 응답 없음 (현장에서 15분 안에 사진이 오지 않은 경우와 같다)

용접부가 아닌 대상(전극 팁, 표시창 등)을 요청하면 세 조건 모두 '촬영 불가'로 답한다 —
실험실에는 그 용접의 시편 사진만 있다. 요청이 맞았는지도 기록한다.

사용: .venv/bin/python -m eval.run_tier_e [--conds photo swap none] [--workers 4] [--limit N]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from app.agent.loop import Ablation, run
from app.agent.tools.photo import read_photo
from app.db import connect, js
from eval.judge import judge
from eval.run import git_sha
from eval.tier_e import WELD_WORDS, load

CONDITIONS = ("photo", "swap", "none")
# 2026-11-18 파일럿(run #48)에서 이 4건을 보고 실행기 버그와 판독기 연결을 고쳤다.
# 본 지표에서는 제외한다 — 보고 고친 사건으로 성과를 재면 안 된다. (전체 62건 수치도 함께 낸다)
DEV_CASES = ("E-29", "E-54", "E-345", "E-391")
# RSW-01 기록을 읽는 도구는 이 설비에 쓸 수 없다. 매뉴얼·도면 검색은 일반 용접 지식이라 남긴다
AB = Ablation(disabled_tools=("query_timeseries", "recall_cases"))
OUT_JSON = Path("outputs/tier_e_results.json")
OUT_CSV = Path("eval/results/tier_e_results.csv")


def _is_weld_request(r: dict) -> bool:
    """요청 '대상' 만 본다. 촬영 방법 설명에는 다른 대상을 찍을 때도 'weld' 가 흔히 들어간다
    (2026-11-18 파일럿: 공압 호스 요청에 용접 사진을 준 버그)."""
    t = str(r.get("target", "")).lower()
    return any(w in t for w in WELD_WORDS)


def _answer(st, case, cond: str, model: str, rec: dict, first: bool) -> None:
    """마지막 촬영 요청에 답한다. 사진은 첫 요청에만 — 다시 요청하면 더 찍을 것이 없다."""
    given = False
    for r in st.photo_requests[-1]["requests"]:
        weld = _is_weld_request(r)
        rec["requests"].append({"target": r.get("target", "")[:160], "weld": weld})
        if not (first and weld and not given) or cond == "none":
            why = ("촬영 요청에 응답 없음 (타임아웃)" if cond == "none" or weld
                   else "이 대상은 촬영할 수 없다 — 이 용접의 시편 사진만 있다")
            st.add_evidence("photo", why, {"status": "no_response", "requested": r.get("target", ""),
                                           "note": "가진 증거만으로 결론을 내라."})
            continue
        path = case.photo if cond == "photo" else case.swap_photo
        reading = read_photo(path, r.get("target", ""), model=model,
                             checks=list((r.get("if_observed") or {}).keys()))
        given = True
        clean = {k: v for k, v in reading.items() if not k.startswith("_")}
        rec["given"] = path
        rec["reading"] = {k: clean.get(k) for k in ("fault_present", "fault_kind", "confidence",
                                                     "observation", "checks")}
        st.add_evidence("photo", f"사진 판독: {str(clean.get('observation', ''))[:120]}",
                        {"status": "received", "requested": r.get("target", ""), **clean})
    st.status = "diagnosing"


def one(case, cond: str, model: str) -> dict:
    rec = {"case_id": case.case_id, "label": case.label, "cond": cond, "asked_photo": False,
           "requests": [], "given": None, "reading": None}
    st = run(case, model=model, max_steps=9, ablation=AB)
    rounds = 0
    while st.status == "awaiting_photo" and rounds < 3:
        rec["asked_photo"] = True
        _answer(st, case, cond, model, rec, first=(rounds == 0))
        st = run(case, model=model, max_steps=st.step + 4, state=st, ablation=AB)
        rounds += 1
    v = judge(case.truth, st.root_cause or "")
    rec.update(status=st.status, root_cause=st.root_cause or "", confidence=st.confidence,
               m1=1.0 if v.get("match") else 0.0, judge_reason=v.get("reason", ""),
               steps=st.step, calls=st.usage.get("calls"),
               asked_weld=any(x["weld"] for x in rec["requests"]))
    return rec


def summarize(out: list[dict], conds, include_dev: bool = False) -> list[dict]:
    rows = []
    for cond in conds:
        rs = [x for x in out if x["cond"] == cond and (include_dev or x["case_id"] not in DEV_CASES)]
        if not rs:
            continue
        ex = [x for x in rs if x["label"] == "Explode"]
        gd = [x for x in rs if x["label"] == "Good"]
        pct = lambda xs, k="m1": round(100 * sum(x[k] for x in xs) / len(xs), 1) if xs else None
        rows.append({"cond": cond, "n": len(rs), "accuracy": pct(rs),
                     "explode_recall": pct(ex), "good_recall": pct(gd),
                     "asked_photo": pct(rs, "asked_photo"), "asked_weld": pct(rs, "asked_weld")})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--conds", nargs="*", default=list(CONDITIONS))
    ap.add_argument("--limit", type=int, default=0, help="앞에서 N건만 (시험 실행)")
    a = ap.parse_args()

    cases = load()[: a.limit or None]
    jobs = [(c, cond) for c in cases for cond in a.conds]
    print(f"Tier E — 사건 {len(cases)} × 조건 {len(a.conds)} = {len(jobs)}회", flush=True)
    con = connect()
    run_id = con.execute(
        "INSERT INTO eval_runs (started_at, config, git_sha, model_map) VALUES (?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(),
         js({"label": "tier_e", "conds": a.conds, "n_cases": len(cases), "model": a.model,
             "ablation": AB.label()}),
         git_sha(), js({"diagnoser": a.model, "judge": "sonnet", "vlm": a.model}))).lastrowid
    con.commit()

    out = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(one, c, cond, a.model): (c, cond) for c, cond in jobs}
        for fut in as_completed(futs):
            c, cond = futs[fut]
            try:
                rec = fut.result()
            except Exception as e:
                print(f"  ! {c.case_id} {cond}: {type(e).__name__}: {str(e)[:100]}",
                      file=sys.stderr, flush=True)
                continue
            out.append(rec)
            fp = (rec["reading"] or {}).get("fault_present")
            print(f"  {'✅' if rec['m1'] else '❌'} {rec['case_id']:7s} {rec['label']:7s} {cond:5s} "
                  f"요청={'용접부' if rec['asked_weld'] else ('다른것' if rec['asked_photo'] else '없음'):4s} "
                  f"판독={fp}  {rec['root_cause'][:60]}", flush=True)
            for metric, val in [("M1_match", rec["m1"]), ("E_asked_photo", rec["asked_photo"]),
                                ("E_asked_weld", rec["asked_weld"])]:
                con.execute("INSERT OR REPLACE INTO eval_results (run_id, case_id, tier, metric,"
                            " value, detail) VALUES (?,?,?,?,?,?)",
                            (run_id, f"{rec['case_id']}|{cond}", "E", metric, float(val), js(rec)))
            con.commit()

    rows = summarize(out, a.conds)
    rows_all = summarize(out, a.conds, include_dev=True)
    print(f"\n{'='*72}\nTier E run #{run_id} — 실제 용접 · 실제 사진 (Explode:Good = 1:1)")
    print(f"본 지표: 개발용 {len(DEV_CASES)}건 제외\n")
    print(f"{'조건':6s} {'n':>3s} {'정확도':>7s} {'날림 맞힘':>9s} {'정상 맞힘':>9s} {'촬영 요청':>9s} {'용접부 요청':>10s}")
    for r in rows:
        print(f"{r['cond']:6s} {r['n']:3d} {r['accuracy']:6.1f}% {r['explode_recall']:8.1f}% "
              f"{r['good_recall']:8.1f}% {r['asked_photo']:8.1f}% {r['asked_weld']:9.1f}%")
    OUT_JSON.parent.mkdir(exist_ok=True)
    for r in rows_all:
        print(f"  (참고: 개발용 포함 전체) {r['cond']:5s} n={r['n']} 정확도 {r['accuracy']}%")
    json.dump({"run_id": run_id, "dev_cases": DEV_CASES, "summary": rows,
               "summary_incl_dev": rows_all, "records": out}, open(OUT_JSON, "w"),
              ensure_ascii=False, indent=1)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["case_id", "label", "cond", "asked_photo", "asked_weld",
                                          "given", "fault_present", "m1", "status", "root_cause",
                                          "judge_reason"])
        w.writeheader()
        for r in sorted(out, key=lambda x: (x["case_id"], x["cond"])):
            w.writerow({**{k: r.get(k) for k in w.fieldnames if k != "fault_present"},
                        "fault_present": (r["reading"] or {}).get("fault_present")})
    print(f"\n→ {OUT_JSON} · {OUT_CSV} · eval_runs #{run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
