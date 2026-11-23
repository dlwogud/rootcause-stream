"""`claude -p --output-format json` 응답에서 실제로 답한 모델 이름을 꺼낸다.

코드는 별칭(haiku · sonnet · opus)만 넘긴다. 별칭이 가리키는 버전은 Claude Code 가 정하고,
2026-11-17 에 4.x → 5.5 로 바뀌었다 (eval/MODEL_VERSIONS.md). 그래서 응답의 실제 이름을 남긴다.

주의: modelUsage 에는 Claude Code 가 내부에서 짧게 부르는 haiku 가 **맨 앞에** 함께 들어온다
(실측: sonnet 지정 → haiku 출력 24 토큰 + sonnet 1,653 토큰). 첫 키를 집으면 sonnet·opus
호출도 haiku 로 기록된다 — 2026-11-23 까지 채점 기록이 그랬다.
"""
from __future__ import annotations


def resolved_model(env: dict, alias: str) -> str:
    usage = env.get("modelUsage") or {}
    if not usage:
        return alias
    named = [k for k in usage if alias and alias in k]
    if named:
        return named[0]
    out = lambda k: usage[k].get("outputTokens", 0) if isinstance(usage[k], dict) else 0
    return max(usage, key=out)
