"""LLM-as-Judge — 진단 결과가 정답과 일치하는지 판정한다.

**피평가 모델과 다른 모델을 쓴다.** 같은 모델로 자기 답을 채점하면 신뢰받지 못한다.
판정에는 반드시 근거 문장을 요구해 '그냥 맞다' 를 막는다.
"""
from __future__ import annotations

import json
import re
import subprocess

from app.agent.cli import resolved_model

JUDGE_MODEL = "sonnet"      # 피평가(기본 haiku/opus)와 분리

PROMPT = """You are grading an industrial fault-diagnosis system. Be strict but fair.

GROUND TRUTH (established independently of the system under test):
{truth}

SYSTEM'S DIAGNOSIS:
{answer}

Decide whether the system's diagnosis identifies the same underlying cause as the ground
truth. Judge the substance, not the wording — different vocabulary for the same physical
cause counts as a match. A diagnosis that is merely consistent with the truth but names a
different mechanism is NOT a match. A diagnosis that correctly says "this is not an
equipment fault" when the truth says so IS a match.

Respond with ONLY this JSON object, no fence, no prose:
{{"match": true|false, "partial": true|false, "reason": "<one sentence, max 30 words>"}}

"partial" means the diagnosis names the right system or variable but the wrong mechanism."""


def _strip(t: str) -> str:
    t = t.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1].rsplit("```", 1)[0]
    return t.strip()


def judge(truth: str, answer: str, model: str = JUDGE_MODEL) -> dict:
    if not answer or not answer.strip():
        return {"match": False, "partial": False, "reason": "빈 응답", "judge_model": model}
    r = subprocess.run(
        ["claude", "-p", "--model", model, "--output-format", "json",
         PROMPT.format(truth=truth, answer=answer)],
        capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(f"judge claude exit {r.returncode}: {r.stderr[:160]}")
    env = json.loads(r.stdout)
    raw = _strip(env.get("result", ""))
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            raise RuntimeError(f"judge 응답 파싱 실패: {raw[:160]!r}")
        out = json.loads(m.group(0))
    if not isinstance(out, dict):
        raise RuntimeError(f"judge 가 객체를 반환하지 않음: {raw[:160]!r}")
    out["judge_model"] = resolved_model(env, model)
    out["cost_cc"] = env.get("total_cost_usd", 0.0)
    return out
