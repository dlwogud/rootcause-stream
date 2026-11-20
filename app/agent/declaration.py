"""사전 선언 대조 — '사진을 보기 전에 한 약속' 을 결론까지 지키게 한다.

Agent 는 촬영을 요청할 때 `if_observed` 로 "이게 보이면 H2 지지, H1 반박" 을 미리 적는다
(docs/03, 사후 합리화 방지). 그런데 2026-11-20 까지는 이 선언이 판독기의 질문 목록으로만
쓰였고, 사진을 본 뒤 선언과 다른 결론을 내도 아무 일도 일어나지 않았다.

Tier E 기준 사진 실행(run #73·#74)에서 실제로 그런 일이 있었다 — 판독기가 "Agent 가 날림의
증거라고 선언한 관찰이 보인다" 고 답했는데, Agent 는 센서 값이 정상 범위라며 "결함 없음" 으로
결론 냈다. 이 모듈은 두 가지를 한다.

  1. 판독 결과가 오면, 보인 관찰마다 Agent 자신의 선언을 되돌려 보여준다 (`reconcile`)
  2. finalize 가 그 선언과 어긋나면 **한 번** 되묻는다 (`challenge`).
     Agent 는 결론을 고치거나, 선언을 뒤집는 구체적 근거를 root_cause 에 적고 그대로 낼 수 있다.

정답이 무엇인지는 쓰지 않는다. Agent 가 스스로 한 선언과 판독기의 관찰만 쓴다.
"""
from __future__ import annotations

import difflib
import re

EFFECTS = ("support", "weaken", "refute")
MATCH_MIN = 0.6          # 판독기가 관찰 문구를 옮겨 적으며 조금 바꾸는 경우까지 같은 항목으로 본다


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).lower()).strip()


def _effect(v) -> str | None:
    w = _norm(v).split(" ")[0] if v else ""
    w = w.strip(".,;:()")
    return w if w in EFFECTS else None


def _match(obs: str, declared: list[str]) -> str | None:
    o = _norm(obs)
    best, score = None, 0.0
    for k in declared:
        kn = _norm(k)
        if o and (o == kn or o.startswith(kn[:60]) or kn.startswith(o[:60])):
            return k
        r = difflib.SequenceMatcher(None, o, kn).ratio()
        if r > score:
            best, score = k, r
    return best if score >= MATCH_MIN else None


def reconcile(request: dict, reading: dict, hypotheses: list | None = None) -> dict | None:
    """판독 결과의 checks 를 Agent 의 if_observed 선언과 맞춘다.

    보인 관찰(visible=true)에 대해서만 선언된 영향을 되돌려준다. 선언은 '보이면 무엇을
    뜻하는가' 만 말하므로, 안 보인 것(false)은 정보로만 적고 영향을 추론하지 않는다.
    """
    decl = request.get("if_observed") or {}
    if not isinstance(decl, dict) or not decl:
        return None
    stmts = {str(h.get("id")): str(h.get("statement", ""))[:160]
             for h in (hypotheses or []) if isinstance(h, dict)}
    seen, absent = [], []
    for c in reading.get("checks") or []:
        if not isinstance(c, dict):
            continue
        k = _match(c.get("observation", ""), list(decl))
        if k is None:
            continue
        if c.get("visible") is True:
            eff = {str(h): e for h, v in (decl[k] or {}).items() if (e := _effect(v))}
            if eff:
                seen.append({"observation": k, "declared": eff,
                             "hypotheses_at_declaration": {h: stmts[h] for h in eff if h in stmts}})
        elif c.get("visible") is False:
            absent.append(k)
    if not seen and not absent:
        return None
    lines = []
    for s in seen:
        what = ", ".join(f"{h} → {e}" for h, e in s["declared"].items())
        lines.append(f'VISIBLE: "{s["observation"][:140]}". Before seeing the photo you declared: {what}.')
    for a in absent:
        lines.append(f'Visibly absent: "{a[:140]}".')
    return {"note": "Your own pre-declaration, checked against what the reader saw.",
            "lines": lines, "seen": seen, "absent": absent}


def photo_payload(entry: dict, request: dict, reading: dict) -> dict:
    """사진 증거의 payload. 선언 대조를 맨 앞에 둔다 — 다음 스텝 프롬프트는 앞 1400자만 보여준다."""
    rec = reconcile(request, reading, entry.get("hypotheses") if entry else None)
    out = {"status": "received", "requested": request.get("target", "")}
    if rec:
        out["your_declaration"] = rec
    out.update(reading)
    return out


def conflicts(evidence: list, hypotheses: list) -> list[str]:
    """최종 가설 순위가 '보인 관찰' 에 대한 자기 선언과 어긋나는 지점."""
    if not hypotheses:
        return []
    score = {str(h.get("id")): float(h.get("score") or 0.0) for h in hypotheses}
    top = max(score, key=score.get)
    out = []
    for e in evidence:
        p = e.get("payload") if isinstance(e, dict) else None
        rec = (p or {}).get("your_declaration") or {}
        for s in rec.get("seen", []):
            at = s.get("hypotheses_at_declaration", {})
            for h, eff in s["declared"].items():
                label = f'{h} ("{at[h]}")' if h in at else h
                if eff == "support" and h != top and score.get(h, 0.0) < score[top]:
                    out.append(f'[{e["id"]}] "{s["observation"][:120]}" is visible. You declared it '
                               f"SUPPORTS {label}, but your final ranking puts {top} first.")
                elif eff == "refute" and h == top:
                    out.append(f'[{e["id"]}] "{s["observation"][:120]}" is visible. You declared it '
                               f"REFUTES {label}, yet {top} is your top hypothesis.")
    return out


def challenge(items: list[str]) -> str:
    return ("BEFORE YOU FINALIZE — your conclusion departs from your own pre-declaration.\n"
            "When you requested the photograph you stated what each observation would mean, "
            "before seeing it. The photo reader reported:\n"
            + "\n".join(f"  - {x}" for x in items) + "\n"
            "Hypothesis ids refer to your hypotheses at the time you declared; if you renumbered "
            "since, map them by statement.\n"
            "A declaration made before seeing the evidence stands unless specific evidence defeats "
            "it. Either (a) finalize consistently with your declaration, or (b) keep your "
            "conclusion and state in root_cause the specific evidence that overrides it.\n"
            "Answer with the same JSON object shape.")
