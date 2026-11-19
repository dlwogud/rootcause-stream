"""정답 누출 검사 — Agent·베이스라인이 **실제로 받는 프롬프트 전체**를 렌더해서 본다.

2026-11-19: 사건 요약의 `dup_fraction`(= Tier C 정답 라벨)이 프롬프트에 들어가 있었다.
설계 검증 51항목도, 도구 출력 검사도 이것을 잡지 못했다. 그래서 개별 필드가 아니라
**최종 프롬프트 문자열**을 검사한다.
"""
from __future__ import annotations

import pytest

from app.agent.inputs import LABEL_KEYS
from app.agent.loop import FULL, _render_first, initial_state
from eval.cases import load as load_abc
from eval.diagnosers import baseline_prompt

CASES = load_abc()
try:
    from eval.tier_e import load as load_e
    CASES += load_e()
except FileNotFoundError:
    pass


def _forbidden(case) -> list[str]:
    # 라벨 키 이름, 정답 문장, 정답 요약 라벨
    out = [k for k in LABEL_KEYS if k not in ("label", "category", "truth")]   # 일반어는 문장에 나올 수 있다
    out += [case.truth[:40], case.truth_key]
    return [x for x in out if x]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.case_id)
def test_agent_first_prompt_has_no_label(case):
    prompt = _render_first(initial_state(case), 9, FULL)
    for bad in _forbidden(case):
        assert bad not in prompt, f"{case.case_id}: '{bad}' 가 Agent 프롬프트에 있다"


@pytest.mark.parametrize("case", [c for c in CASES if c.tier in "ABC"], ids=lambda c: c.case_id)
def test_baseline_prompt_has_no_label(case):
    prompt = baseline_prompt(case)
    for bad in _forbidden(case):
        assert bad not in prompt, f"{case.case_id}: '{bad}' 가 베이스라인 프롬프트에 있다"


@pytest.mark.parametrize("case", [c for c in CASES if c.tier in "ABC"], ids=lambda c: c.case_id)
def test_evidence_summary_hides_case_file(case):
    """도구를 인자 없이 불러도 증거 요약에 사건 파일 이름(예: 'B-A5_동시드리프트-k2.csv')이 없다."""
    from app.agent.loop import _execute
    st = initial_state(case)
    _execute(st, {"type": "use_tool", "tool": "query_timeseries", "args": {}}, case)
    summary = st.evidence[-1]["summary"]
    assert "data_ref" not in summary and (case.data_ref or "@@") not in summary
    assert case.case_id not in summary
