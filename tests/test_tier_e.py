"""Tier E — 정답이 Agent 입력으로 새지 않는가, 사진 응답 규칙이 의도대로인가."""
from __future__ import annotations

import json

import pytest

from eval.tier_e import CASES_PATH, load

pytestmark = pytest.mark.skipif(not CASES_PATH.exists(), reason="Tier E 사건 파일 없음")


def test_balanced_and_paired():
    cs = load()
    assert sum(c.label == "Explode" for c in cs) == sum(c.label == "Good" for c in cs) == 31
    # 바꿔치기 사진은 반대 판정의 용접이다
    lab = {c.sample_id: c.label for c in cs}
    assert all(lab[c.swap_sample_id] != c.label for c in cs)


def test_no_outcome_leak_into_agent_input():
    """인장강도·너깃 지름·판정·비고는 판정 그 자체다 — Agent 입력에 있으면 안 된다."""
    for c in load():
        s = json.dumps(c.cooccurrence, ensure_ascii=False).lower()
        for banned in ("pull", "nugget", "category", "explode", "good", "bad", "doe", "comment"):
            assert banned not in s, (c.case_id, banned)


def test_weld_request_matches_target_only():
    """촬영 방법 설명에 'weld' 가 있어도 대상이 다른 것이면 용접 사진을 주지 않는다."""
    from eval.run_tier_e import _is_weld_request
    assert _is_weld_request({"target": "The weld spot on the coupon"})
    assert not _is_weld_request({"target": "Pneumatic air hose and regulator",
                                 "how_to_shoot": "photograph it next to the weld station"})
