"""진단 Agent — 수동 루프 + 상태 외부화.

Tool Runner 헬퍼를 쓰지 않는 이유: `request_photo` 는 일반 도구 호출이 아니라
**비동기 중단점**이다. 작업자가 현장으로 이동해 사진을 찍는 데 수 분이 걸리고,
아예 응답하지 않을 수도 있다. 동기 루프로는 버틸 수 없으므로 상태를 외부화한다.
(docs/02-architecture.md 핵심 설계 결정)

스텝마다 상태를 저장하므로 프로세스가 죽어도 이어서 재개할 수 있다.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.agent.schemas import SchemaError, TOOLS, parse_json_object, validate_step
from app.agent.tools import REGISTRY, signature

PROMPTS = Path(__file__).resolve().parent / "prompts"
MAX_STEPS = 9
MAX_RETRIES = 2          # 스키마 위반 시 재시도. 한 번의 비정상 응답이 루프를 죽이면 안 된다

SUSPENDED = "awaiting_photo"
DONE = "finalized"
EXHAUSTED = "max_steps"


@dataclass
class Evidence:
    id: str
    kind: str
    summary: str
    payload: dict = field(default_factory=dict)


@dataclass
class AgentState:
    case_id: str
    kind: str                               # burst | level_shift
    incident: dict
    evidence: list = field(default_factory=list)
    hypotheses: list = field(default_factory=list)
    transcript: list = field(default_factory=list)   # [{step, action, raw}]
    step: int = 0
    status: str = "diagnosing"
    root_cause: str | None = None
    confidence: float | None = None
    cited_evidence_ids: list = field(default_factory=list)
    photo_requests: list = field(default_factory=list)
    usage: dict = field(default_factory=lambda: {"in": 0, "out": 0, "ms": 0,
                                                 "cost_cc": 0.0, "calls": 0,
                                                 "schema_retries": 0})

    def evidence_ids(self) -> set[str]:
        return {e["id"] if isinstance(e, dict) else e.id for e in self.evidence}

    def next_evidence_id(self) -> str:
        return f"E{len(self.evidence) + 1}"

    def add_evidence(self, kind: str, summary: str, payload: dict) -> str:
        eid = self.next_evidence_id()
        self.evidence.append(asdict(Evidence(eid, kind, summary, payload)))
        return eid

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, default=str)

    @staticmethod
    def from_json(s: str) -> "AgentState":
        return AgentState(**json.loads(s))


def _call(prompt: str, model: str) -> tuple[str, dict]:
    r = subprocess.run(
        ["claude", "-p", "--model", model, "--output-format", "json", prompt],
        capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"claude exit {r.returncode}: {r.stderr[:160]}")
    env = json.loads(r.stdout)
    if env.get("is_error"):
        raise RuntimeError(f"claude error: {str(env.get('result'))[:160]}")
    u = env.get("usage", {}) or {}
    return env.get("result", ""), {
        "in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0),
        "ms": env.get("duration_ms", 0), "cost_cc": env.get("total_cost_usd", 0.0)}


def _render(st: AgentState, error: str | None = None) -> str:
    system = (PROMPTS / "system.md").read_text(encoding="utf-8")
    kickoff = (PROMPTS / f"kickoff_{st.kind}.md").read_text(encoding="utf-8")
    parts = [system, "", kickoff, "", "INCIDENT SUMMARY",
             json.dumps(st.incident, ensure_ascii=False, indent=2), ""]

    parts.append("AVAILABLE TOOLS")
    parts += [f"  {k:18s} {v}" for k, v in TOOLS.items()]
    parts.append("")

    if st.evidence:
        parts.append("EVIDENCE COLLECTED SO FAR (cite these ids, and only these)")
        for e in st.evidence:
            parts.append(f"  [{e['id']}] ({e['kind']}) {e['summary']}")
            parts.append(f"        {json.dumps(e['payload'], ensure_ascii=False)[:900]}")
    else:
        parts.append("EVIDENCE COLLECTED SO FAR: none yet. You may cite nothing.")
    parts.append("")

    if st.hypotheses:
        parts.append("YOUR HYPOTHESES FROM THE PREVIOUS STEP")
        parts.append(json.dumps(st.hypotheses, ensure_ascii=False, indent=2))
        parts.append("")

    parts.append(f"STEP {st.step + 1} of {MAX_STEPS}. "
                 f"{'This is your last step — finalize.' if st.step + 1 >= MAX_STEPS else ''}")
    if error:
        parts.append(f"\nYOUR PREVIOUS RESPONSE WAS REJECTED: {error}\nFix it and answer again.")
    return "\n".join(parts)


def _execute(st: AgentState, act: dict, case) -> tuple[str, bool]:
    """도구를 실행하고 증거를 적립한다. (요약, 중단여부) 반환."""
    t = act["type"]
    if t == "use_tool":
        name, args = act["tool"], dict(act.get("args") or {})
        fn = REGISTRY[name]
        if name == "query_timeseries":
            args.update(window_start=case.window_start, window_end=case.window_end,
                        data_ref=case.data_ref)
        elif name == "recall_cases":
            args["sig"] = signature(case.cooccurrence)
        try:
            res = fn(**args)
        except Exception as e:                      # 도구 실패가 루프를 죽이면 안 된다
            res = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
        eid = st.add_evidence(name, f"{name}({json.dumps(args, ensure_ascii=False, default=str)[:120]})", res)
        return f"{eid} ← {name}", False

    if t == "request_photo":
        st.photo_requests.append({"requested_at": datetime.now(timezone.utc).isoformat(),
                                  "requests": act["requests"]})
        st.status = SUSPENDED
        return f"촬영 요청 {len(act['requests'])}건 — 루프 중단", True

    st.root_cause = act["root_cause"]
    st.confidence = float(act.get("confidence") or 0.0)
    st.cited_evidence_ids = [str(x) for x in act.get("cited_evidence_ids", [])]
    st.status = DONE
    return "finalize", True


def resume_with_photo(st: AgentState, reading: dict | None = None) -> AgentState:
    """중단된 루프를 재개한다.

    `reading` 이 None 이면 **무응답 경로**다 — 작업자가 15분 안에 사진을 주지 않은 경우.
    사진 없이 최선의 결론을 내게 한다. 이 경로의 성능도 측정 대상이다
    (현장에서 늘 사진이 오지는 않는다).
    """
    req = st.photo_requests[-1]["requests"] if st.photo_requests else []
    if reading is None:
        st.add_evidence("photo", "촬영 요청에 응답 없음 (타임아웃)",
                        {"status": "no_response", "requested": [r["target"] for r in req],
                         "note": "사진을 받지 못했다. 가진 증거만으로 결론을 내라."})
    else:
        st.add_evidence("photo", f"사진 판독: {reading.get('observation', '')[:120]}",
                        {"status": "received", "requested": [r["target"] for r in req],
                         **reading})
    st.status = "diagnosing"
    return st


def run(case, model: str = "haiku", max_steps: int = MAX_STEPS,
        state: AgentState | None = None, on_step=None) -> AgentState:
    """진단 루프. `request_photo` 를 만나면 상태를 반환하고 멈춘다(중단).

    재개하려면 사진 판독 결과를 증거로 넣은 뒤 같은 state 로 다시 호출한다.
    """
    st = state or AgentState(case_id=case.case_id, kind=case.kind,
                             incident={"kind": case.kind, "alarm_count": case.alarm_count,
                                       "window": [case.window_start, case.window_end],
                                       "summary": case.cooccurrence,
                                       "alarm_sample": case.alarm_sample[:15]})
    st.status = "diagnosing"

    while st.step < max_steps:
        err, step_ok = None, False
        for _ in range(MAX_RETRIES + 1):
            raw, u = _call(_render(st, err), model)
            for k in ("in", "out", "ms", "cost_cc"):
                st.usage[k] += u[k]
            st.usage["calls"] += 1
            try:
                d = validate_step(parse_json_object(raw), st.evidence_ids())
            except (SchemaError, ValueError) as e:
                err = str(e)
                st.usage["schema_retries"] += 1
                continue
            step_ok = True
            break
        if not step_ok:
            st.status = "schema_failure"
            st.transcript.append({"step": st.step + 1, "error": err})
            return st

        st.hypotheses = d["hypotheses"]
        act = d["action"]
        note, stop = _execute(st, act, case)
        st.step += 1
        st.transcript.append({"step": st.step, "action": act.get("type"),
                              "tool": act.get("tool"), "note": note,
                              "hypotheses": st.hypotheses})
        if on_step:
            on_step(st, act, note)
        if stop:
            return st

    st.status = EXHAUSTED
    return st
