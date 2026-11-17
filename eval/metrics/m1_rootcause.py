"""M1 — 근본원인 진단 정확도.

Tier A·C 의 주 지표이고, Tier B 에는 참고로만 쓴다.
(2026-11-17 이전에는 Tier A 를 제외했다 — 당시 정답이 '원인 특정 불가'였기 때문이다.
 정답이 '기록 재활용'으로 정정되어 이제 A 도 M1 로 채점한다. docs/14-data-reuse-finding.md)
"""
from __future__ import annotations

from eval.judge import judge


def m1_rootcause(case, result: dict, judge_model: str = "sonnet") -> dict:
    ans = result.get("root_cause") or ""
    v = judge(case.truth, ans, model=judge_model)
    return {
        "M1_match": 1.0 if v.get("match") else 0.0,
        "M1_partial": 1.0 if (v.get("match") or v.get("partial")) else 0.0,
        "_M1_reason": v.get("reason", ""),
        "_M1_judge": v.get("judge_model", judge_model),
    }
