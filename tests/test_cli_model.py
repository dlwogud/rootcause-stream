"""실제로 답한 모델 이름 — Claude Code 가 내부에서 부르는 haiku 를 집으면 안 된다."""
from app.agent.cli import resolved_model

# 2026-11-23 실측한 응답 모양: 보조 haiku 가 맨 앞
ENV = {"modelUsage": {"claude-haiku-5-5": {"inputTokens": 1683, "outputTokens": 24},
                      "claude-opus-5-5": {"inputTokens": 2, "outputTokens": 398}}}


def test_alias_wins_over_first_key():
    assert resolved_model(ENV, "opus") == "claude-opus-5-5"


def test_haiku_alias_still_haiku():
    env = {"modelUsage": {"claude-haiku-5-5": {"outputTokens": 300}}}
    assert resolved_model(env, "haiku") == "claude-haiku-5-5"


def test_full_id_or_unknown_alias_falls_back_to_most_output():
    assert resolved_model(ENV, "best") == "claude-opus-5-5"


def test_no_usage_returns_alias():
    assert resolved_model({}, "sonnet") == "sonnet"
