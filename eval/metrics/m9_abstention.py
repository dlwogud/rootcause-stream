"""M9 — 적절한 보류와 가르는 관측 요청.

Tier A 전용. 이 사건은 **공정 데이터만으로는 원인을 특정할 수 없다**(eval/cases.py 참조).
그러므로 정답은 특정 원인이 아니라 두 가지 행동이다.

  M9a 적절한 보류   : 단정하지 않고 추가 관측을 요청했는가
  M9b 가르는 관측   : 요청한 관측이 '실제 저하' vs '측정 오류' 를 실제로 가르는가
                      (측정 경로와 **독립적인** 힘 확인이어야 한다)

억지로 원인을 맞히게 하면 환각을 보상하게 된다. 모른다고 말할 수 있어야
사람에게 묻는 설계가 성립한다.
"""
from __future__ import annotations

import re

# 측정 경로와 독립적인 힘 확인 — 이것만 두 가설을 가른다
DISCRIMINATING = [
    r"setpoint", r"set point", r"설정", r"recipe", r"program", r"preset",
    r"hmi", r"display", r"control panel", r"controller", r"제어반",
    r"regulator", r"pressure gauge", r"manometer", r"공압", r"pneumatic",
    r"independent", r"calibrat", r"교정", r"reference",
]
# 이 신호를 설명하지 못하는 관측
NON_DISCRIMINATING = [r"electrode tip", r"전극", r"cooling", r"냉각", r"coolant",
                      r"water", r"tip dress", r"weld nugget", r"spatter"]


def m9_abstention(case, result: dict, **_) -> dict:
    if case.tier != "A":
        return {}
    status = result.get("status") or ""
    reqs = result.get("photo_requests") or []
    asked = bool(reqs) or status == "awaiting_photo"

    # finalize 했더라도 '추가 확인 필요' 를 명시했으면 보류로 인정
    rc = (result.get("root_cause") or "").lower()
    hedged = bool(re.search(
        r"cannot (be )?(determine|distinguish|resolve)|insufficient|"
        r"requires? (further|additional)|unable to (distinguish|determine)|"
        r"independent (check|verification|measurement)|확인 필요|구별할 수 없",
        rc))
    out = {"M9a_abstained": 1.0 if (asked or hedged) else 0.0}

    if not asked:
        out["M9b_discriminating_request"] = 0.0
        return out

    targets = " ".join(
        f"{r.get('target','')} {r.get('why_this_photo','')} {r.get('how_to_shoot','')}"
        for group in reqs for r in (group.get("requests") or [group]))
    t = targets.lower()
    hit = any(re.search(p, t) for p in DISCRIMINATING)
    miss_only = (not hit) and any(re.search(p, t) for p in NON_DISCRIMINATING)
    out["M9b_discriminating_request"] = 1.0 if hit else 0.0
    out["_M9_targets"] = targets[:200]
    if miss_only:
        out["_M9_note"] = "이 신호를 설명하지 못하는 관측만 요청했다"
    return out
