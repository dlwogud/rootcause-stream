"""매뉴얼 색인 · 하이브리드 검색.

색인이 비어 있으면 건너뛴다 (`python3 scripts/01_index_manuals.py --reset` 선행 필요).
"""
from __future__ import annotations

import pytest

from app.db import DB_PATH, connect
from app.retrieval.hybrid import MODES, search

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="색인 DB 없음")


@pytest.fixture(scope="module")
def con():
    c = connect()
    yield c
    c.close()


def test_pages_indexed(con):
    n = con.execute("SELECT COUNT(*) FROM manual_pages").fetchone()[0]
    assert n == 415, f"매뉴얼 5종 415페이지여야 한다: {n}"


def test_diagram_pages_rendered(con):
    """도면 페이지가 PNG 로 남아 있어야 Multimodal RAG(기술 #3)가 성립한다."""
    rows = con.execute(
        "SELECT image_path FROM manual_pages WHERE page_kind='diagram'").fetchall()
    assert len(rows) >= 50
    from app.db import ROOT
    assert all((ROOT / r["image_path"]).exists() for r in rows[:20])


def test_text_indexed_on_diagram_pages_too(con):
    """페이지를 텍스트/도면으로 배타 분류하지 않는다.

    그림과 지시문이 함께 있는 페이지는 둘 다다. 배타 분류했을 때
    spotweldinc p.6 의 공압 기준값이 색인에서 빠졌다.
    """
    n = con.execute(
        "SELECT COUNT(*) FROM manual_chunks c JOIN manual_pages p ON p.id=c.page_id"
        " WHERE p.page_kind='diagram'").fetchone()[0]
    assert n > 0, "도면 페이지의 텍스트가 색인되지 않았다"


def test_pneumatic_setpoint_is_indexed(con):
    """VLM 판독 결과를 대조할 기준값이 검색 가능해야 한다.

    게이지 수치 판독을 설계에서 제외했으므로(spike/RESULTS.md), 이 기준값을 근거로
    작업자에게 직접 묻는다. 색인에 없으면 그 경로가 끊긴다.
    """
    n = con.execute("SELECT COUNT(*) FROM manual_chunks WHERE content LIKE '%0.5 MPa%'").fetchone()[0]
    assert n >= 1


def test_boilerplate_stripped(con):
    """머리말/꼬리말이 BM25 상위를 점유하면 안 된다."""
    hits = search("air pressure gauge setting for the cylinder", top_k=3, mode="bm25")
    assert hits
    for h in hits:
        assert "Resistance  Welding  Equipment" not in h.content


@pytest.mark.parametrize("mode", MODES)
def test_all_modes_return_hits(mode):
    """ablation 이 서비스와 같은 경로를 쓴다 — 모든 mode 가 동작해야 한다."""
    hits = search("electrode tip maintenance", top_k=3, mode=mode)
    assert hits, f"mode={mode} 결과 없음"
    assert all(h.doc.endswith(".pdf") and h.page_no > 0 for h in hits)


def test_troubleshooting_table_is_findable():
    """PROBLEM/CAUSE/REMEDY 표가 조치 카드의 원본이다."""
    hits = search("what to do when weld current is too low", top_k=5, mode="hybrid_rerank")
    pages = {(h.doc, h.page_no) for h in hits}
    assert any(d.startswith(("sureweld", "philips")) for d, _ in pages)


def test_citation_format():
    h = search("cooling water flow", top_k=1, mode="hybrid")[0]
    c = h.cite()
    assert ".pdf" in c and "p." in c
