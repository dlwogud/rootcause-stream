"""현장 사진 판독 (VLM).

스파이크(spike/RESULTS.md)에서 자기일관성이 확인된 판독 과제만 쓴다.
  채택: 이상징후 유무(91.7%) · 에러코드 유무(100%) · 경고등 점등(대상 명확 시 100%)
  제외: 게이지 수치/구간(50% — 이진화해도 개선되지 않았다)

confidence 는 일관성과 단조 관계가 있으므로(high 83% / medium 62% / low 40%)
1차 필터로 쓰되, 단독 확정 근거로는 쓰지 않는다.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.db import ROOT

PROMPT = """Read the photograph at {path}.

A maintenance technician took this photo in response to a specific request:
  "{request}"

Report ONLY what is visibly present. Do not infer the machine's state from context,
and do not guess at anything the image does not show. If the photo does not show the
requested subject at all, say so — that is a useful answer, not a failure.

Do NOT attempt to read numeric values from analogue dials. That reading is unreliable
and is out of scope. Report presence/absence and condition categories only.

Respond with ONLY this JSON object, no fence:
{{"shows_requested_subject": true|false,
  "observation": "<1-2 sentences of what is actually visible>",
  "fault_present": true|false|null,
  "fault_kind": "corrosion|crack|wear|leak|deformation|breakage|discolouration|none|unknown",
  "error_code_visible": true|false|null,
  "warning_lamp_lit": true|false|null,
  "confidence": "low|medium|high",
  "unreadable_reason": "<blur|occlusion|too_small|wrong_subject|null>"}}"""


def read_photo(path: str | Path, request: str, model: str = "haiku") -> dict:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        return {"error": f"사진이 없다: {p}", "shows_requested_subject": False}
    r = subprocess.run(
        ["claude", "-p", "--model", model, "--allowedTools", "Read",
         "--output-format", "json", PROMPT.format(path=p, request=request)],
        capture_output=True, text=True, timeout=240)
    if r.returncode != 0:
        return {"error": f"VLM 호출 실패: {r.stderr[:120]}", "shows_requested_subject": False}
    env = json.loads(r.stdout)
    raw = (env.get("result") or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        out = json.loads(raw)
        if isinstance(out, list):
            out = next((x for x in out if isinstance(x, dict)), {})
    except json.JSONDecodeError:
        out = {"observation": raw[:400], "confidence": "low",
               "unreadable_reason": "parse_failure", "shows_requested_subject": None}
    out["_photo"] = str(p.relative_to(ROOT)) if str(p).startswith(str(ROOT)) else str(p)
    out["_cost_cc"] = env.get("total_cost_usd", 0.0)
    out["_model"] = next(iter(env.get("modelUsage", {})), model)
    return out
