"""M1 — 근본원인 진단 정확도.

Tier C(정답이 명확한 데이터 현상)의 주 지표이고, Tier B 에는 참고로만 쓴다.
**Tier A 에는 적용하지 않는다** — 그 사건은 공정 데이터로 원인이 특정되지 않으므로
(eval/cases.py 의 TRUTH 주석 참조), 원인을 맞히라고 요구하면 환각을 보상하게 된다.
Tier A 는 M9(적절한 보류 + 가르는 관측 요청)로 채점한다.
"""
from __future__ import annotations

from eval.judge import judge


def m1_rootcause(case, result: dict, judge_model: str = "sonnet") -> dict:
    if case.tier == "A":
        return {}
    ans = result.get("root_cause") or ""
    v = judge(case.truth, ans, model=judge_model)
    return {
        "M1_match": 1.0 if v.get("match") else 0.0,
        "M1_partial": 1.0 if (v.get("match") or v.get("partial")) else 0.0,
        "_M1_reason": v.get("reason", ""),
        "_M1_judge": v.get("judge_model", judge_model),
    }
