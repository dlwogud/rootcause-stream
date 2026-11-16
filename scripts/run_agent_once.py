#!/usr/bin/env python3
"""단일 케이스로 Agent 루프를 돌려본다 (개발·시연용)."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.agent.loop import run           # noqa: E402
from eval.cases import load              # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("case_id")
ap.add_argument("--model", default="haiku")
ap.add_argument("--max-steps", type=int, default=6)
a = ap.parse_args()

c = next(x for x in load() if x.case_id == a.case_id)
print(f"=== {c.case_id}  [{c.kind}]  알람 {c.alarm_count}건 ===", flush=True)
print(f"정답: {c.truth_key}\n", flush=True)

def show(st, act, note):
    top = max(st.hypotheses, key=lambda h: h["score"])
    print(f"  step {st.step}: {act['type']:14s} {str(act.get('tool') or ''):18s} → {note}", flush=True)
    for h in sorted(st.hypotheses, key=lambda x: -x["score"])[:3]:
        print(f"      [{h['score']:.2f}] {h['id']} {h['statement'][:72]}  ←{h['cited_evidence_ids']}", flush=True)

st = run(c, model=a.model, max_steps=a.max_steps, on_step=show)
print(f"\n상태={st.status} 스텝={st.step} 호출={st.usage['calls']} "
      f"스키마재시도={st.usage['schema_retries']} ${st.usage['cost_cc']:.3f}")
print("증거:", [(e["id"], e["kind"]) for e in st.evidence])
if st.photo_requests:
    print("\n촬영 요청:")
    for r in st.photo_requests[-1]["requests"]:
        print(f"  · {r['target']} — {r['why_this_photo'][:90]}")
        print(f"    가르는 가설: {r['discriminates']}")
if st.root_cause:
    print(f"\n근본원인: {st.root_cause}")
    print(f"인용 {st.cited_evidence_ids} · 신뢰도 {st.confidence}")
