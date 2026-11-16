"""M2 — 주 변수 식별. Tier B 만 정답이 정확히 알려져 있다(주입한 변수).

Tier A/C 는 주 변수가 단일하지 않으므로 채점하지 않는다. 억지로 라벨을 만들면
정답의 출처가 이 프로젝트 안으로 들어와 평가의 전제가 깨진다.
"""
from __future__ import annotations

import re

# 주입 모드 → 직접 조작된 변수
INJECTED_VAR = {
    "A1_결합이탈": ["current", "전류"],
    "A2_가압이탈": ["force", "가압", "pressure"],
    "A3_전압강하": ["voltage", "전압"],
    "A4_통전단축": ["time", "통전", "weld time"],
    "A5_동시드리프트": ["force", "current", "가압", "전류"],
    "A6_산포증가": ["variance", "산포", "variability", "scatter", "spread"],
    "A7_지속반복이상": ["repeat", "반복", "constant", "고정", "identical", "stuck"],
}


def m2_primary_variable(case, result: dict, **_) -> dict:
    if case.tier != "B" or not case.injected:
        return {}
    text = " ".join(str(result.get(k, "")) for k in
                    ("root_cause", "reasoning", "primary_variable")).lower()
    keys = INJECTED_VAR.get(case.injected, [])
    hit = any(re.search(re.escape(k.lower()), text) for k in keys)
    return {"M2_primary_variable": 1.0 if hit else 0.0}
