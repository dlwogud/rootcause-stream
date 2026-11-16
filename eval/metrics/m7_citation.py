"""M7 — 인용 무결성. 환각 방어의 측정.

① 존재하지 않는 증거 id 를 인용했는가
② 결론에 인용이 아예 없는가
"""
from __future__ import annotations


def m7_citation_integrity(case, result: dict, **_) -> dict:
    cited = result.get("cited_evidence_ids") or []
    available = {e.get("id") for e in (result.get("evidence") or []) if isinstance(e, dict)}
    if not cited:
        return {"M7_has_citation": 0.0, "M7_phantom_rate": 0.0}
    phantom = [c for c in cited if c not in available]
    return {
        "M7_has_citation": 1.0,
        "M7_phantom_rate": len(phantom) / len(cited),
        "_M7_phantom": ",".join(phantom),
    }
