#!/usr/bin/env python3
"""Tier D 실행기 — 사진 루프의 기여를 측정한다.

조건 3개를 같은 케이스에 돌린다.
  agent_photo  : Agent 가 요청한 대상에 맞는 사진을 준다
  random_photo : Agent 요청과 무관하게 **가설과 무관한 사진**을 준다 (대조군)
  no_photo     : 사진을 주지 않는다 (타임아웃 경로)

측정
  M1 근본원인 — D1·D2 는 공정 데이터가 **동일**하다. 사진 없이는 둘에 같은 답을
     낼 수밖에 없으므로 최대 50%. 사진이 정보를 실어 나르면 100% 까지 간다
  M4 정보이득 — 사진 직전 vs 사진 직후 가설 분포의 엔트로피 감소(bit),
     공통 가설 id 기준 (가설을 늘렸다 줄이는 조작을 막는다)

사용: python3 -m eval.run_tier_d --repeats 2
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from app.agent.loop import FULL, run
from app.agent.tools.photo import read_photo
from app.db import connect, js
from eval.judge import judge
from eval.run import git_sha
from eval.tier_d import RANDOM_PHOTO, information_gain, load

CONDITIONS = ("agent_photo", "random_photo", "no_photo")


def one(case, cond: str, model: str, rep: int) -> dict:
    st = run(case, model=model, max_steps=9)
    rec = {"case_id": case.case_id, "cond": cond, "rep": rep,
           "asked_photo": st.status == "awaiting_photo", "matched": [],
           "ig": None, "h_before": None, "h_after": None}

    if st.status == "awaiting_photo":
        before = [dict(h) for h in st.hypotheses]
        reqs = st.photo_requests[-1]["requests"]

        if cond == "no_photo":
            st.add_evidence("photo", "촬영 요청에 응답 없음 (타임아웃)",
                            {"status": "no_response", "note": "가진 증거만으로 결론을 내라."})
        else:
            for r in reqs:
                target = f"{r.get('target','')} {r.get('how_to_shoot','')}"
                if cond == "agent_photo":
                    ph = case.photo_for(target) or RANDOM_PHOTO
                else:
                    ph = RANDOM_PHOTO
                rec["matched"].append({"requested": r.get("target", "")[:80],
                                       "given": ph.key, "discriminating": ph.discriminating})
                reading = read_photo(ph.path, r.get("target", ""), model=model)
                st.add_evidence("photo", f"사진 판독({ph.key}): "
                                f"{str(reading.get('observation',''))[:120]}",
                                {"status": "received", "requested": r.get("target", ""),
                                 **{k: v for k, v in reading.items() if not k.startswith("_")}})
        st.status = "diagnosing"

        # 사진 직후 1스텝 — 가설 갱신을 본다 (정보이득 측정 지점)
        st = run(case, model=model, max_steps=st.step + 1, state=st)
        after = [dict(h) for h in st.hypotheses]
        g = information_gain(before, after)
        rec.update(ig=g["information_gain"], h_before=g["h_before"], h_after=g["h_after"])
        # 결론까지
        if st.status not in ("finalized",):
            st = run(case, model=model, max_steps=st.step + 4, state=st)

    v = judge(case.truth, st.root_cause or "")
    rec.update(status=st.status, root_cause=st.root_cause or "",
               m1=1.0 if v.get("match") else 0.0, judge_reason=v.get("reason", ""),
               steps=st.step, calls=st.usage.get("calls"))
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--conds", nargs="*", default=list(CONDITIONS))
    a = ap.parse_args()

    cases = load()
    jobs = [(c, cond, r) for c in cases for cond in a.conds for r in range(a.repeats)]
    print(f"Tier D — 케이스 {len(cases)} × 조건 {len(a.conds)} × 반복 {a.repeats} = {len(jobs)}회\n",
          flush=True)

    con = connect()
    run_id = con.execute(
        "INSERT INTO eval_runs (started_at, config, git_sha, model_map) VALUES (?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(),
         js({"label": "tier_d", "conds": a.conds, "repeats": a.repeats, "model": a.model}),
         git_sha(), js({"diagnoser": a.model, "judge": "sonnet"}))).lastrowid
    con.commit()

    out = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(one, c, cond, a.model, r): (c, cond, r) for c, cond, r in jobs}
        for fut in as_completed(futs):
            c, cond, r = futs[fut]
            try:
                rec = fut.result()
            except Exception as e:
                print(f"  ! {c.case_id} {cond} r{r}: {type(e).__name__}: {str(e)[:100]}",
                      file=sys.stderr, flush=True)
                continue
            out.append(rec)
            mark = "✅" if rec["m1"] else "❌"
            print(f"  {mark} {rec['case_id']:18s} {cond:13s} r{r}  IG={rec['ig']}  "
                  f"사진={[m['given'] for m in rec['matched']]}  {rec['root_cause'][:60]}",
                  flush=True)
            cid = f"{rec['case_id']}|{cond}|r{r}"
            for metric, val in [("M1_match", rec["m1"]), ("M4_information_gain", rec["ig"])]:
                if val is not None:
                    con.execute("INSERT OR REPLACE INTO eval_results"
                                " (run_id, case_id, tier, metric, value, detail)"
                                " VALUES (?,?,?,?,?,?)",
                                (run_id, cid, "D", metric, float(val), js(rec)))
            con.commit()

    # 요약
    print(f"\n{'='*72}\nTier D run #{run_id} (구성된 사건 — 합성)\n")
    print(f"{'조건':14s} {'n':>3s} {'M1 정확':>8s} {'평균 IG(bit)':>13s} {'가르는 사진 비율':>16s}")
    for cond in a.conds:
        rs = [x for x in out if x["cond"] == cond]
        if not rs:
            continue
        m1 = sum(x["m1"] for x in rs) / len(rs)
        igs = [x["ig"] for x in rs if x["ig"] is not None]
        ig = f"{sum(igs)/len(igs):.3f}" if igs else "–"
        ms = [m for x in rs for m in x["matched"]]
        disc = f"{sum(m['discriminating'] for m in ms)/len(ms)*100:.0f}%" if ms else "–"
        print(f"{cond:14s} {len(rs):3d} {m1*100:7.1f}% {ig:>13s} {disc:>16s}")
    json.dump(out, open("outputs/tier_d_results.json", "w"), ensure_ascii=False, indent=1)
    print(f"\n→ outputs/tier_d_results.json · eval_runs #{run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
