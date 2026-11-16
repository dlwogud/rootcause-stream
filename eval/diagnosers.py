"""진단기(diagnoser) — 평가 하네스에 꽂히는 교체 가능한 구현.

`baseline` : 알람 요약만 보고 단일 LLM 호출로 진단한다. 도구도 매뉴얼도 사진도 없다.
             이것이 ablation 의 바닥이고, 본 Agent 는 이것 대비 Δ 로 평가된다.
`agent`    : D6~D9 에서 구현 (app/agent/loop.py)
"""
from __future__ import annotations

import json
import re
import subprocess

BASELINE_PROMPT = """You are diagnosing an industrial alarm burst on a resistance spot welding machine.

INCIDENT
  equipment: RSW-01
  window: {window_start} → {window_end}
  total alarms: {alarm_count}

ALARM SUMMARY (aggregated by the stream layer)
{cooccurrence}

ALARM SAMPLE (first {n_sample} of {alarm_count}, chronological)
{alarms}

DETECTOR REFERENCE
  knn       : conformal p-value of a k-NN distance in the physics-derived space
              [weld force, dynamic resistance R=V/I, heat input E=V*I*t].
              Fitted on stable production days. Low p = far from normal operation.
  chart     : 2-sigma control chart on the window median of weld force.
              Control limits come from stable days only.
  residual  : residual of the normal-operation model (weld force -> weld current),
              flagged beyond 3 sigma.

Identify the single most likely ROOT cause of this burst. Most alarms in a burst are
consequences, not causes. The cause may also be something other than an equipment fault
(for example a data-acquisition problem) — say so if the evidence points that way.

Respond with ONLY this JSON object, no fence, no prose:
{{"root_cause": "<2-3 sentences naming the mechanism>",
  "primary_variable": "<force|current|voltage|time|none>",
  "confidence": "low|medium|high",
  "reasoning": "<one sentence on what in the data led you there>"}}"""


def _strip(t: str) -> str:
    t = t.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1].rsplit("```", 1)[0]
    return t.strip()


def _parse(raw: str) -> dict:
    raw = _strip(raw)
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            raise RuntimeError(f"JSON 파싱 실패: {raw[:160]!r}")
        out = json.loads(m.group(0))
    if isinstance(out, list):
        out = next((x for x in out if isinstance(x, dict)), None)
    if not isinstance(out, dict):
        raise RuntimeError(f"객체가 아님: {raw[:160]!r}")
    return out


def baseline(case, model: str = "haiku", **_) -> dict:
    """알람 요약만으로 단일 호출 진단. 도구·매뉴얼·사진 없음."""
    alarms = "\n".join(
        f"  {a['ts'][11:19]}  {a['detector']:9s} {a['tag']:20s} "
        f"val={a['value']:<12.6g} thr={a['threshold']:<10.6g} sev={a['severity']}"
        for a in case.alarm_sample)
    prompt = BASELINE_PROMPT.format(
        window_start=case.window_start, window_end=case.window_end,
        alarm_count=case.alarm_count, n_sample=len(case.alarm_sample),
        cooccurrence=json.dumps(case.cooccurrence, ensure_ascii=False, indent=2),
        alarms=alarms)
    r = subprocess.run(
        ["claude", "-p", "--model", model, "--output-format", "json", prompt],
        capture_output=True, text=True, timeout=240)
    if r.returncode != 0:
        raise RuntimeError(f"claude exit {r.returncode}: {r.stderr[:160]}")
    env = json.loads(r.stdout)
    if env.get("is_error"):
        raise RuntimeError(f"claude error: {str(env.get('result'))[:160]}")
    out = _parse(env.get("result", ""))
    u = env.get("usage", {}) or {}
    out["_usage"] = {
        "in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0),
        "cache_read": u.get("cache_read_input_tokens", 0),
        "ms": env.get("duration_ms", 0), "cost_cc": env.get("total_cost_usd", 0.0),
        "model": next(iter(env.get("modelUsage", {})), model),
    }
    out.setdefault("evidence", [])
    out.setdefault("cited_evidence_ids", [])
    return out


DIAGNOSERS = {"baseline": baseline}
