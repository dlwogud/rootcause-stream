"""Agent 구조화 출력 스키마.

`claude -p` 에는 `output_config.format` 같은 스키마 강제 장치가 없다(스파이크에서
JSON 배열 반환으로 루프가 중단된 적이 있다). 그래서 여기서 **형태를 검증하고
위반을 격리한다** — 한 번의 비정상 응답이 루프 전체를 죽이면 안 된다.
API 백엔드로 바꾸면 이 검증은 서버가 대신한다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

TOOLS = {
    "query_timeseries": "공정 변수의 사건 구간 통계를 안정일 기준과 대조한다. "
                        "args: {variable: force|current|voltage|time|all}",
    "search_manual":    "설비 매뉴얼을 검색한다. args: {query: str}",
    "lookup_diagram":   "도면(배선도·공압계통·플로우차트)을 찾아 질문에 답하게 한다. "
                        "선으로만 그려진 연결 관계는 이것으로만 알 수 있다. args: {question: str}",
    "recall_cases":     "과거 유사 사례를 조회한다. args: {}",
}
ACTIONS = ("use_tool", "request_photo", "finalize")


@dataclass
class Hypothesis:
    id: str
    statement: str
    score: float
    cited_evidence_ids: list[str] = field(default_factory=list)

    @staticmethod
    def parse(d: dict) -> "Hypothesis":
        return Hypothesis(
            id=str(d.get("id", "")).strip() or "H?",
            statement=str(d.get("statement", "")).strip(),
            score=max(0.0, min(1.0, float(d.get("score", 0.0)))),
            cited_evidence_ids=[str(x) for x in (d.get("cited_evidence_ids") or [])])


class SchemaError(ValueError):
    """모델 응답이 요구 형태를 벗어났다. 루프를 죽이지 말고 재시도한다."""


def strip_fence(t: str) -> str:
    t = (t or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1].rsplit("```", 1)[0]
    return t.strip()


def parse_json_object(raw: str) -> dict:
    raw = strip_fence(raw)
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            raise SchemaError(f"JSON 을 찾을 수 없다: {raw[:160]!r}")
        out = json.loads(m.group(0))
    if isinstance(out, list):
        out = next((x for x in out if isinstance(x, dict)), None)
    if not isinstance(out, dict):
        raise SchemaError(f"객체가 아니다: {raw[:160]!r}")
    return out


def validate_step(d: dict, known_evidence: set[str]) -> dict:
    """한 스텝 응답을 검증한다. 인용 무결성(기술 #9)도 여기서 강제한다."""
    hyps = d.get("hypotheses")
    if not isinstance(hyps, list) or not hyps:
        raise SchemaError("hypotheses 가 비었다")
    parsed = [Hypothesis.parse(h) for h in hyps if isinstance(h, dict)]
    if not parsed:
        raise SchemaError("가설을 하나도 파싱하지 못했다")

    phantom = sorted({c for h in parsed for c in h.cited_evidence_ids} - known_evidence)
    if phantom:
        raise SchemaError(f"존재하지 않는 증거를 인용했다: {phantom}. "
                          f"사용 가능한 증거 id: {sorted(known_evidence) or '없음'}")

    act = d.get("action")
    if not isinstance(act, dict) or act.get("type") not in ACTIONS:
        raise SchemaError(f"action.type 은 {ACTIONS} 중 하나여야 한다: {act}")

    t = act["type"]
    if t == "use_tool":
        if act.get("tool") not in TOOLS:
            raise SchemaError(f"알 수 없는 도구: {act.get('tool')}. 가능한 것: {list(TOOLS)}")
        act.setdefault("args", {})
    elif t == "request_photo":
        reqs = act.get("requests")
        if not isinstance(reqs, list) or not reqs:
            raise SchemaError("request_photo 에는 requests 배열이 필요하다")
        for r in reqs:
            miss = [k for k in ("target", "how_to_shoot", "discriminates",
                                "if_observed", "why_this_photo") if not r.get(k)]
            if miss:
                raise SchemaError(f"촬영 요청에 빠진 필드: {miss}")
    elif t == "finalize":
        if not str(act.get("root_cause", "")).strip():
            raise SchemaError("finalize 에는 root_cause 가 필요하다")
        if not act.get("cited_evidence_ids"):
            raise SchemaError("finalize 는 근거 증거를 인용해야 한다 (인용 없는 결론 금지)")
        bad = sorted(set(map(str, act["cited_evidence_ids"])) - known_evidence)
        if bad:
            raise SchemaError(f"finalize 가 존재하지 않는 증거를 인용했다: {bad}")

    d["hypotheses"] = [h.__dict__ for h in parsed]
    return d
