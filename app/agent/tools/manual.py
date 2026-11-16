"""search_manual — 설비 매뉴얼 검색. 인용(문서·페이지)을 함께 돌려준다."""
from __future__ import annotations

from app.retrieval.hybrid import search


def search_manual(query: str, top_k: int = 4, mode: str = "hybrid_rerank", **_) -> dict:
    hits = search(query, top_k=top_k, mode=mode)
    return {"query": query, "mode": mode, "hits": [
        {"cite": h.cite(), "doc": h.doc, "page": h.page_no,
         "is_diagram_description": h.source == "vlm_description",
         "text": h.content[:700]}
        for h in hits]}
