"""사전 선언 대조 (app/agent/declaration.py) — LLM 없이 돌린다."""
import json
from types import SimpleNamespace

from app.agent import loop
from app.agent.declaration import conflicts, photo_payload, reconcile

REQ = {"target": "spot weld on the coupon face",
       "if_observed": {"Spatter or a crater at the weld centre": {"H2": "support", "H1": "refute"},
                       "Clean round indentation, no spatter": {"H1": "support (strong)"}}}
HYPS = [{"id": "H1", "statement": "acceptable weld"}, {"id": "H2", "statement": "expulsion"}]


def _reading(spatter, clean):
    return {"observation": "x", "checks": [
        {"observation": "Spatter or a crater at the weld centre.", "visible": spatter},   # 판독기가 조금 바꿔 옮김
        {"observation": "Clean round indentation, no spatter", "visible": clean}]}


def test_reconcile_maps_visible_checks_to_own_declaration():
    r = reconcile(REQ, _reading(True, False), HYPS)
    assert [s["declared"] for s in r["seen"]] == [{"H2": "support", "H1": "refute"}]
    assert r["seen"][0]["hypotheses_at_declaration"]["H2"] == "expulsion"
    assert r["absent"] == ["Clean round indentation, no spatter"]
    assert "VISIBLE" in r["lines"][0]


def test_effect_with_trailing_words_is_parsed():
    r = reconcile(REQ, _reading(False, True), HYPS)
    assert r["seen"][0]["declared"] == {"H1": "support"}


def test_no_declaration_or_unjudgeable_gives_nothing():
    assert reconcile({"target": "x"}, _reading(True, True)) is None
    assert reconcile(REQ, _reading(None, None)) is None


def test_payload_puts_declaration_first():
    p = photo_payload({"hypotheses": HYPS}, REQ, _reading(True, False))
    assert list(p)[:3] == ["status", "requested", "your_declaration"]


def _ev(p):
    return [{"id": "E3", "kind": "photo", "summary": "", "payload": p}]


def test_conflict_when_supported_hypothesis_is_not_top():
    ev = _ev(photo_payload({"hypotheses": HYPS}, REQ, _reading(True, False)))
    final = [{"id": "H1", "score": 0.7}, {"id": "H2", "score": 0.3}]
    c = conflicts(ev, final)
    assert any("SUPPORTS H2" in x for x in c) and any("REFUTES H1" in x for x in c)
    assert conflicts(ev, [{"id": "H2", "score": 0.8}, {"id": "H1", "score": 0.2}]) == []


def test_tie_with_top_is_not_a_conflict_for_support():
    ev = _ev(photo_payload({"hypotheses": HYPS}, {"if_observed": {"Spatter or a crater at the weld centre": {"H2": "support"}}},
                           _reading(True, None)))
    assert conflicts(ev, [{"id": "H1", "score": 0.5}, {"id": "H2", "score": 0.5}]) == []


# ── 루프 안에서: 한 번만 되묻고, 두 번째 finalize 는 받아들인다 ──
def _step(hyps, action):
    return json.dumps({"hypotheses": hyps, "action": action})


def test_gate_challenges_once_then_accepts(monkeypatch):
    case = SimpleNamespace(case_id="T-1", kind="weld_quality", alarm_count=1, window_start="",
                           window_end="", cooccurrence={}, alarm_sample=[], data_ref=None)
    h_bad = [{"id": "H1", "statement": "acceptable", "score": 0.7, "cited_evidence_ids": []},
             {"id": "H2", "statement": "expulsion", "score": 0.3, "cited_evidence_ids": []}]
    replies = iter([
        _step(h_bad, {"type": "request_photo", "requests": [{**REQ, "how_to_shoot": "close",
              "discriminates": ["H1", "H2"], "why_this_photo": "x"}]}),
        _step(h_bad, {"type": "finalize", "root_cause": "no defect", "confidence": 0.6,
                      "cited_evidence_ids": ["E1"]}),
        _step(h_bad, {"type": "finalize", "root_cause": "no defect, because ...", "confidence": 0.5,
                      "cited_evidence_ids": ["E1"]}),
    ])
    prompts = []

    def fake_call(prompt, model, session=None):
        prompts.append(prompt)
        return next(replies), {"session": "s"}

    monkeypatch.setattr(loop, "_call", fake_call)
    st = loop.run(case)
    assert st.status == loop.SUSPENDED
    loop.resume_with_photo(st, _reading(True, False))
    assert "your_declaration" in st.evidence[-1]["payload"]
    st = loop.run(case, state=st, max_steps=st.step + 4)
    assert st.status == loop.DONE
    assert st.root_cause == "no defect, because ..."           # 두 번째는 그대로 받아들인다
    assert prompts[-1].startswith("BEFORE YOU FINALIZE")
    assert st.usage["declaration_challenges"] == 1 and st.usage["schema_retries"] == 0
    assert any(t.get("action") == "declaration_challenge" for t in st.transcript)


def test_gate_off_does_not_challenge(monkeypatch):
    case = SimpleNamespace(case_id="T-1", kind="weld_quality", alarm_count=1, window_start="",
                           window_end="", cooccurrence={}, alarm_sample=[], data_ref=None)
    st = loop.initial_state(case)
    st.session_id = "s"
    st.photo_requests = [{"requests": [REQ], "hypotheses": HYPS}]
    loop.resume_with_photo(st, _reading(True, False))
    h_bad = [{"id": "H1", "statement": "a", "score": 0.7, "cited_evidence_ids": []}]
    monkeypatch.setattr(loop, "_call", lambda p, m, s=None: (_step(h_bad, {
        "type": "finalize", "root_cause": "no defect", "cited_evidence_ids": ["E1"]}), {}))
    st = loop.run(case, state=st, ablation=loop.Ablation(declaration_gate=False))
    assert st.status == loop.DONE and not st.usage.get("declaration_challenges")


def test_all_new_evidence_is_shown_after_a_photo_round():
    """한 라운드에 증거가 여러 개 붙으면(앞면·뒷면, 또는 사진 + '촬영 불가') 다음 스텝에 모두 보여야 한다.
    2026-11-22 까지 마지막 것만 보여줘 앞 판독이 가려졌다."""
    case = SimpleNamespace(case_id="T-1", kind="weld_quality", alarm_count=1, window_start="",
                           window_end="", cooccurrence={}, alarm_sample=[], data_ref=None)
    st = loop.initial_state(case)
    st.add_evidence("search_manual", "manual", {"hits": []})
    st.shown_evidence = 1
    st.add_evidence("photo", "사진 판독 (앞면): FRONT", {"observation": "front"})
    st.add_evidence("photo", "사진 판독 (뒷면): BACK", {"observation": "back"})
    st.add_evidence("photo", "이 대상은 촬영할 수 없다", {"status": "no_response"})
    p = loop._render_next(st, 9, "Continue.")
    assert "[E2]" in p and "[E3]" in p and "[E4]" in p and "[E1]" not in p
    assert st.shown_evidence == 4
    assert "NEW EVIDENCE" not in loop._render_next(st, 9, "Continue.")
