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


# ── 뒷면 사진 (2026-11-20 방향 A) ──
def test_requested_sides():
    from eval.tier_e import requested_sides
    assert requested_sides({"target": "spot weld on the coupon face"}) == ["F"]
    assert requested_sides({"target": "back face of the coupon"}) == ["B"]
    assert requested_sides({"target": "weld", "how_to_shoot": "flip the coupon and shoot it"}) == ["B"]
    assert requested_sides({"target": "weld on both faces of the coupon"}) == ["F", "B"]


def test_back_photos_exist_for_every_case():
    from eval.tier_e import ROOT, back_of, load
    for c in load():
        for f in (c.photo, c.swap_photo, c.reference_photo):
            assert (ROOT / back_of(f)).exists(), back_of(f)


def test_answer_gives_each_face_once(monkeypatch):
    from eval import run_tier_e as R
    from eval.tier_e import load
    from app.agent.loop import initial_state
    case = load()[0]
    calls = []
    monkeypatch.setattr(R, "read_photo", lambda p, req, model, checks, reference: calls.append((p, reference)) or {"observation": "x"})
    st = initial_state(case)
    rec = {"requests": [], "given": None, "reading": None}
    st.photo_requests = [{"requests": [{"target": "spot weld on coupon", "how_to_shoot": "close"}]}]
    R._answer(st, case, "photo_ref", "haiku", rec)
    st.photo_requests.append({"requests": [{"target": "back face of the coupon", "how_to_shoot": "close"},
                                           {"target": "spot weld on coupon", "how_to_shoot": "again"}]})
    R._answer(st, case, "photo_ref", "haiku", rec)
    assert [p for p, _ in calls] == [case.photo, case.photo[:-5] + "B.jpg"]
    assert calls[1][1] == case.reference_photo[:-5] + "B.jpg"        # 뒷면은 기준 사진도 뒷면
    assert rec["given_sides"] == ["F", "B"]
    assert st.evidence[-1]["payload"]["status"] == "no_response"      # 앞면 재요청엔 더 줄 것이 없다
    swap = {"requests": [], "given": None, "reading": None}
    calls.clear()
    st.photo_requests = [{"requests": [{"target": "coupon", "how_to_shoot": "front and back"}]}]
    R._answer(st, case, "swap", "haiku", swap)
    assert [p for p, _ in calls] == [case.swap_photo, case.swap_photo[:-5] + "B.jpg"] and calls[0][1] is None
