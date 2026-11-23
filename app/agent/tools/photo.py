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

from app.agent.cli import resolved_model
from app.db import ROOT

PROMPT = """Read the photograph at {path}.

A maintenance technician took this photo in response to a specific request:
  "{request}"

Report ONLY what is visibly present. Do not infer the machine's state from context,
and do not guess at anything the image does not show. If the photo does not show the
requested subject at all, say so — that is a useful answer, not a failure.

Do NOT attempt to read numeric values from analogue dials. That reading is unreliable
and is out of scope. Report presence/absence and condition categories only.

{reference}{checks}Respond with ONLY this JSON object, no fence:
{{"shows_requested_subject": true|false,
  "observation": "<1-2 sentences of what is actually visible>",
  "fault_present": true|false|null,
  "fault_kind": "corrosion|crack|wear|leak|deformation|breakage|discolouration|none|unknown",
  "error_code_visible": true|false|null,
  "warning_lamp_lit": true|false|null,
  "confidence": "low|medium|high",
  "unreadable_reason": "<blur|occlusion|too_small|wrong_subject|null>",
  "checks": [{{"observation": "<copied from the list above>", "visible": true|false|null}}],
  "differs_from_reference": true|false|null,
  "reference_difference": "<what differs from the reference weld, or null if no reference>"}}"""

# Agent 가 사진을 보기 전에 선언한 '이게 보이면 이 가설' 의 관찰 항목을 판독기에 넘긴다.
# 2026-11-18 Tier E 파일럿에서 발견: 이것을 넘기지 않으면 판독기는 대상 이름만 보고 막연히
# 묘사하고, Agent 가 가르려던 바로 그 특징의 유무를 답하지 않는다. 사전 선언이 판독에
# 연결되어야 설계(docs/03)대로 '선언 → 확인' 이 성립한다.
CHECKS = """The requester declared, BEFORE seeing the photo, that these observations would
matter. For EACH one, say whether it is visible in this photo (true), visibly absent
(false), or cannot be judged from this photo (null). Judge only what is in the image.
{items}

"""


# ③ 기준 사진 (2026-11-19, eval/RESULTS_TIER_E.md): 미세한 결함은 '정상이 어떻게 생겼는지'
# 없이는 판독기가 대부분 '판단 불가'로 답했다. 같은 설비·같은 설정의 정상 샘플을 함께 보여준다.
REFERENCE = """A second photograph, at {ref}, is a REFERENCE: a weld made on the same machine
with the same settings that passed destructive testing. Read it too. Use it as the baseline
for what an acceptable weld looks like here, and compare the photo under review against it.
Lighting and framing may differ slightly — report only differences in the weld itself.
Every weld differs a little in nugget size, texture, gloss and colour; that is normal
variation, not a defect. Set differs_from_reference to true ONLY for a difference that
would indicate a defect — for example a crack, a hole, metal ejected from or missing at
the weld, or a burn — and false when the weld looks like an acceptable variant of the reference.

"""


def _reference_block(ref) -> str:
    if not ref:
        return ""
    r = Path(ref)
    if not r.is_absolute():
        r = ROOT / r
    return REFERENCE.format(ref=r) if r.exists() else ""


def _checks_block(checks: list[str] | None) -> str:
    items = [c.strip() for c in (checks or []) if str(c).strip()][:6]
    if not items:
        return ""
    return CHECKS.format(items="\n".join(f"  - {c}" for c in items))


KOREAN = ("Write the values of observation and reference_difference in Korean (한국어). "
          "In checks, copy each observation string exactly as it was given.\n\n")


def read_photo(path: str | Path, request: str, model: str = "haiku",
               checks: list[str] | None = None, reference: str | Path | None = None,
               language: str = "en") -> dict:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        return {"error": f"사진이 없다: {p}", "shows_requested_subject": False}
    r = subprocess.run(
        ["claude", "-p", "--model", model, "--allowedTools", "Read",
         "--output-format", "json",
         PROMPT.format(path=p, request=request, checks=_checks_block(checks),
                       reference=_reference_block(reference))
         + ("\n\n" + KOREAN if language == "ko" else "")],
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
    out["_model"] = resolved_model(env, model)
    return out
