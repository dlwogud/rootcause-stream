"""M1 — 근본원인 진단 정확도. 서비스의 1차 목적."""
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
