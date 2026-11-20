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

from app.agent.declaration import challenge, conflicts, photo_payload
from app.agent.inputs import agent_view
from app.agent.schemas import OPTIONAL_TOOLS, SchemaError, TOOLS, parse_json_object, validate_step
from app.agent.tools import REGISTRY, signature


@dataclass(frozen=True)
class Ablation:
    """구성요소를 끄는 스위치. 서비스와 **같은 코드 경로**를 쓴다.

    평가용 분기를 따로 만들면 성과표가 서비스를 설명하지 못한다.
    """
    disabled_tools: tuple = ()        # 'lookup_diagram' 등
    signal_guide: bool = True         # repeat_signals 설명 제공 여부
    allow_photo: bool = True          # 촬영 요청 허용 여부
    search_mode: str = "hybrid_rerank"
    extra_tools: tuple = ()           # 기본으로 꺼진 선택 도구를 켠다 ('query_sql')
    declaration_gate: bool = True     # 사진 사전 선언과 어긋난 결론을 한 번 되묻는다 (declaration.py)

    @property
    def tools(self) -> dict:
        out = {k: v for k, v in TOOLS.items() if k not in self.disabled_tools}
        out.update({k: OPTIONAL_TOOLS[k] for k in self.extra_tools if k not in self.disabled_tools})
        return out

    def label(self) -> str:
        bits = []
        for t in self.disabled_tools:
            bits.append(f"no_{t.replace('query_', '').replace('search_', '')}")
        if not self.signal_guide:
            bits.append("no_signal_guide")
        if not self.allow_photo:
            bits.append("no_photo")
        if self.search_mode != "hybrid_rerank":
            bits.append(self.search_mode)
        for t in self.extra_tools:
            bits.append(f"with_{t}")
        if not self.declaration_gate:
            bits.append("no_declaration_gate")
        return "+".join(bits) or "full"


FULL = Ablation()
# 다른 설비(RSW-LAB) 용접 품질 사건 — RSW-01 기록을 읽는 도구는 쓸 수 없다 (Tier E 실행기·웹 공용)
WELD_QUALITY = Ablation(disabled_tools=("query_timeseries", "recall_cases"))
# 실행기가 채우는 인자 — Agent 에게 되돌려 보여주지 않는다
INTERNAL_ARGS = frozenset({"data_ref", "window_start", "window_end", "sig", "mode"})

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
    session_id: str | None = None     # claude -p 세션. 중단 후 재개 시에도 이어쓴다
    usage: dict = field(default_factory=lambda: {"in": 0, "out": 0, "cache_read": 0,
                                                 "ms": 0, "cost_cc": 0.0, "calls": 0,
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


def _call(prompt: str, model: str, session: str | None = None) -> tuple[str, dict]:
    """세션이 있으면 이어간다.

    매 스텝 새 세션을 열면 Claude Code 시스템 프롬프트(~16.5K 토큰)가 스텝마다
    새로 붙어 지연과 한도 소모가 누적된다. 실측: 새 세션 입력 4,893 토큰 / 3.6초
    vs --resume 입력 155 토큰 / 1.0초 — **31배 차이**다.
    루프를 N 개의 독립 호출이 아니라 하나의 대화로 다루는 것이 설계상으로도 맞다.
    """
    cmd = ["claude", "-p", "--model", model, "--output-format", "json"]
    if session:
        cmd += ["--resume", session]
    r = subprocess.run(cmd + [prompt], capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"claude exit {r.returncode}: {r.stderr[:160]}")
    env = json.loads(r.stdout)
    if env.get("is_error"):
        raise RuntimeError(f"claude error: {str(env.get('result'))[:160]}")
    u = env.get("usage", {}) or {}
    return env.get("result", ""), {
        "in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0),
        "cache_read": u.get("cache_read_input_tokens", 0),
        "ms": env.get("duration_ms", 0), "cost_cc": env.get("total_cost_usd", 0.0),
        "session": env.get("session_id")}


def _strip_block(text: str, start: str, end: str) -> str:
    i, j = text.find(start), text.find(end)
    return text[:i] + text[j:] if 0 <= i < j else text


def _render_first(st: AgentState, max_steps: int, ab: Ablation = FULL) -> str:
    system = (PROMPTS / "system.md").read_text(encoding="utf-8")
    if not ab.signal_guide:
        system = _strip_block(system, "  query_timeseries also returns repeat_signals",
                              "WHAT A PHOTOGRAPH CAN")
    if not ab.allow_photo:
        system = _strip_block(system, "WHAT A PHOTOGRAPH CAN", "OUTPUT —")
        system = system.replace(
            '  {"type": "request_photo", "requests": [{"target": "...", "how_to_shoot": "...",\n'
            '      "discriminates": ["H1","H3"],\n'
            '      "if_observed": {"<what you might see>": {"H1": "support|weaken|refute"}},\n'
            '      "why_this_photo": "..."}]}\n', "")
        system = system.replace(
            "6. When sensors cannot separate your top hypotheses, request a photograph. "
            "Say exactly\n   what to shoot and what each possible observation would mean "
            "— BEFORE you see it.",
            "6. No additional observation can be requested. Reach the best conclusion the "
            "data supports.")
    kickoff = (PROMPTS / f"kickoff_{st.kind}.md").read_text(encoding="utf-8")
    parts = [system, "", kickoff, "", "INCIDENT SUMMARY",
             json.dumps(st.incident, ensure_ascii=False, indent=2), "",
             "AVAILABLE TOOLS"]
    parts += [f"  {k:18s} {v}" for k, v in ab.tools.items()] or ["  (none)"]
    parts += ["", "EVIDENCE COLLECTED SO FAR: none yet. You may cite nothing.", "",
              f"STEP 1 of {max_steps}. Answer now."]
    return "\n".join(parts)


def _render_next(st: AgentState, max_steps: int, note: str) -> str:
    """이어지는 스텝 — **새로 생긴 것만** 보낸다. 앞 내용은 세션이 들고 있다."""
    parts = [note, ""]
    new = st.evidence[-1] if st.evidence else None
    if new:
        parts += [f"NEW EVIDENCE [{new['id']}] ({new['kind']}) {new['summary']}",
                  json.dumps(new["payload"], ensure_ascii=False)[:1400], ""]
    parts.append(f"Evidence ids you may cite: {sorted(st.evidence_ids()) or 'none'}")
    last = max_steps - st.step
    parts.append(f"STEP {st.step + 1} of {max_steps}."
                 + (" This is your last step — finalize now." if last <= 1 else ""))
    parts.append("Respond with the same JSON object shape as before.")
    return "\n".join(parts)


def _render_retry(error: str) -> str:
    if error.startswith("BEFORE YOU FINALIZE"):
        return error
    return (f"YOUR PREVIOUS RESPONSE WAS REJECTED: {error}\n"
            "Fix it and answer again with the same JSON object shape.")


def _execute(st: AgentState, act: dict, case, ab: Ablation = FULL) -> tuple[str, bool]:
    """도구를 실행하고 증거를 적립한다. (요약, 중단여부) 반환."""
    t = act["type"]
    if t == "use_tool":
        name, args = act["tool"], dict(act.get("args") or {})
        if name in ab.disabled_tools:
            eid = st.add_evidence(name, f"{name} 사용 불가 (ablation)",
                                  {"error": "This tool is not available in this run."})
            return f"{eid} ← {name} 차단됨", False
        fn = REGISTRY[name]
        if name == "search_manual":
            args.setdefault("mode", ab.search_mode)
        if name == "query_timeseries":
            args.update(window_start=case.window_start, window_end=case.window_end,
                        data_ref=case.data_ref)
        elif name == "recall_cases":
            args["sig"] = signature(case.cooccurrence)
        elif name == "query_sql":
            args["data_ref"] = case.data_ref
        shown = {k: v for k, v in act.get("args", {}).items() if k not in INTERNAL_ARGS}
        try:
            res = fn(**args)
        except Exception as e:                      # 도구 실패가 루프를 죽이면 안 된다
            res = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
        # 증거 요약에는 Agent 가 보낸 인자만 쓴다. 실행기가 채운 인자(data_ref 등)를 넣으면
        # 사건 파일 이름(예: 'B-A5_동시드리프트-k2.csv')이 Agent 에게 보인다 (2026-11-19 발견)
        eid = st.add_evidence(name, f"{name}({json.dumps(shown, ensure_ascii=False, default=str)[:160]})", res)
        return f"{eid} ← {name}", False

    if t == "request_photo":
        if not ab.allow_photo:
            eid = st.add_evidence("photo", "촬영 요청 불가 (ablation)",
                                  {"status": "unavailable",
                                   "note": "가진 증거만으로 결론을 내라."})
            return f"{eid} ← 촬영 요청 차단됨", False
        # 선언 당시의 가설을 함께 남긴다 — 나중에 가설 번호가 바뀌어도 선언을 대조할 수 있게
        st.photo_requests.append({"requested_at": datetime.now(timezone.utc).isoformat(),
                                  "requests": act["requests"],
                                  "hypotheses": [{"id": h.get("id"), "statement": h.get("statement")}
                                                 for h in st.hypotheses]})
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
    entry = st.photo_requests[-1] if st.photo_requests else {}
    req = entry.get("requests", [])
    if reading is None:
        st.add_evidence("photo", "촬영 요청에 응답 없음 (타임아웃)",
                        {"status": "no_response", "requested": [r["target"] for r in req],
                         "note": "사진을 받지 못했다. 가진 증거만으로 결론을 내라."})
    else:
        p = photo_payload(entry, req[0] if req else {}, reading)
        p["requested"] = [r["target"] for r in req]
        st.add_evidence("photo", f"사진 판독: {reading.get('observation', '')[:120]}", p)
    st.status = "diagnosing"
    return st


def initial_state(case) -> AgentState:
    """Agent 가 처음 보는 사건. 정답 라벨은 agent_view 로 걷어낸다."""
    return AgentState(case_id=case.case_id, kind=case.kind,
                      incident={"kind": case.kind, "alarm_count": case.alarm_count,
                                "window": [case.window_start, case.window_end],
                                "summary": agent_view(case.cooccurrence),
                                "alarm_sample": agent_view(case.alarm_sample[:15])})


def run(case, model: str = "haiku", max_steps: int = MAX_STEPS,
        state: AgentState | None = None, on_step=None,
        ablation: Ablation = FULL) -> AgentState:
    """진단 루프. `request_photo` 를 만나면 상태를 반환하고 멈춘다(중단).

    재개하려면 사진 판독 결과를 증거로 넣은 뒤 같은 state 로 다시 호출한다.
    """
    st = state or initial_state(case)
    st.status = "diagnosing"

    pending_note = "Continue."
    while st.step < max_steps:
        err, step_ok, tries = None, False, 0
        while tries <= MAX_RETRIES:
            if st.session_id is None:
                prompt = _render_first(st, max_steps, ablation)
            elif err:
                prompt = _render_retry(err)
            else:
                prompt = _render_next(st, max_steps, pending_note)
            raw, u = _call(prompt, model, st.session_id)
            st.session_id = u.get("session") or st.session_id
            for k in ("in", "out", "cache_read", "ms", "cost_cc"):
                st.usage[k] = st.usage.get(k, 0) + u.get(k, 0)
            st.usage["calls"] += 1
            try:
                d = validate_step(parse_json_object(raw), st.evidence_ids(),
                              allowed_tools=set(ablation.tools),
                              allow_photo=ablation.allow_photo)
            except (SchemaError, ValueError) as e:
                err = str(e)
                st.usage["schema_retries"] += 1
                tries += 1
                continue
            # 사전 선언 대조 — 스키마 재시도 예산을 쓰지 않고, 사건당 한 번만 되묻는다
            if (ablation.declaration_gate and d["action"]["type"] == "finalize"
                    and not st.usage.get("declaration_challenges")):
                items = conflicts(st.evidence, d["hypotheses"])
                if items:
                    st.usage["declaration_challenges"] = 1
                    st.transcript.append({"step": st.step + 1, "action": "declaration_challenge",
                                          "conflicts": items,
                                          "draft_root_cause": d["action"].get("root_cause", "")})
                    err = challenge(items)
                    continue
            step_ok = True
            break
        if not step_ok:
            st.status = "schema_failure"
            st.transcript.append({"step": st.step + 1, "error": err})
            return st

        st.hypotheses = d["hypotheses"]
        act = d["action"]
        note, stop = _execute(st, act, case, ablation)
        pending_note = f"Result of your last action: {note}"
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
