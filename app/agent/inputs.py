"""Agent(와 베이스라인)가 보는 입력에서 **정답 라벨을 걷어낸다.**

2026-11-19 발견: 사건 요약(Incident.cooccurrence)에 `dup_fraction` 이 들어 있었다.
그것은 선행 프로젝트의 복제 라벨(is_dup)로 계산한 값 — 즉 Tier C 의 정답 라벨이다
(C 는 전부 1.0, B 는 전부 0.0). 도구 출력에서는 11/17 에 걷어냈지만 사건 요약에는 남아 있었다.

사건 선정(eval/cases.py)에는 계속 쓰므로 원본은 그대로 두고, Agent 경계에서만 뺀다.
tests/test_no_label_leak.py 가 렌더된 프롬프트 전체를 검사한다.
"""
from __future__ import annotations

LABEL_KEYS = frozenset({"dup_fraction", "is_dup", "is_duplicate", "category", "truth", "label"})


def agent_view(x):
    """dict/list 를 재귀로 돌며 라벨 키를 뺀 사본을 돌려준다."""
    if isinstance(x, dict):
        return {k: agent_view(v) for k, v in x.items() if str(k).lower() not in LABEL_KEYS}
    if isinstance(x, list):
        return [agent_view(v) for v in x]
    return x
