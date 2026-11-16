"""하이브리드 검색 — 벡터 + BM25(FTS5) + RRF + 리랭킹.

`mode` 를 파라미터로 노출하는 이유: **ablation 실험이 서비스와 같은 경로를 쓴다.**
평가용 코드와 서비스 코드가 갈라지면 성과표가 서비스를 설명하지 못한다.
기술 #4(Hybrid) · #5(Rerank) 의 기여도는 이 mode 를 바꿔 측정한다.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from app.db import connect, from_blob

EMB_MODEL = "BAAI/bge-small-en-v1.5"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"   # 90MB
RRF_K = 60
MODES = ("vector", "bm25", "hybrid", "hybrid_rerank")


@dataclass
class Hit:
    chunk_id: int
    doc: str
    page_no: int
    heading: str | None
    content: str
    score: float
    source: str          # text | vlm_description
    page_kind: str
    image_path: str | None

    def cite(self) -> str:
        h = f" {self.heading}" if self.heading else ""
        return f"{self.doc} p.{self.page_no}{h}"


@lru_cache(maxsize=1)
def _embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMB_MODEL)


@lru_cache(maxsize=1)
def _reranker():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(RERANK_MODEL)


def _fts_query(q: str) -> str:
    """FTS5 는 특수문자에 민감하다. 토큰만 뽑아 OR 로 잇는다."""
    toks = re.findall(r"[A-Za-z가-힣0-9]+", q)
    return " OR ".join(f'"{t}"' for t in toks if len(t) > 1) or '"' + q.strip() + '"'


def _rows(con: sqlite3.Connection, ids: list[int]) -> dict[int, sqlite3.Row]:
    if not ids:
        return {}
    qs = ",".join("?" * len(ids))
    sql = (f"SELECT c.id, c.heading, c.content, c.source, p.doc, p.page_no, p.page_kind,"
           f" p.image_path FROM manual_chunks c JOIN manual_pages p ON p.id = c.page_id"
           f" WHERE c.id IN ({qs})")
    return {r["id"]: r for r in con.execute(sql, ids)}


def _vector_rank(con: sqlite3.Connection, query: str, top: int) -> list[tuple[int, float]]:
    rows = con.execute("SELECT id, embedding FROM manual_chunks"
                       " WHERE embedding IS NOT NULL").fetchall()
    if not rows:
        return []
    M = np.stack([from_blob(r["embedding"]) for r in rows])
    q = _embedder().encode([query], normalize_embeddings=True)[0]
    sims = M @ q
    idx = np.argsort(-sims)[:top]
    return [(int(rows[i]["id"]), float(sims[i])) for i in idx]


def _bm25_rank(con: sqlite3.Connection, query: str, top: int) -> list[tuple[int, float]]:
    try:
        rows = con.execute(
            "SELECT rowid, bm25(manual_fts) AS s FROM manual_fts"
            " WHERE manual_fts MATCH ? ORDER BY s LIMIT ?", (_fts_query(query), top)).fetchall()
    except sqlite3.OperationalError:
        return []
    return [(int(r["rowid"]), -float(r["s"])) for r in rows]   # bm25()는 작을수록 좋다


def _rrf(*ranked: list[tuple[int, float]], k: int = RRF_K) -> list[tuple[int, float]]:
    acc: dict[int, float] = {}
    for lst in ranked:
        for rank, (cid, _) in enumerate(lst, start=1):
            acc[cid] = acc.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(acc.items(), key=lambda kv: -kv[1])


def search(query: str, top_k: int = 5, mode: str = "hybrid_rerank",
           pool: int = 30, con: sqlite3.Connection | None = None) -> list[Hit]:
    if mode not in MODES:
        raise ValueError(f"mode 는 {MODES} 중 하나여야 한다: {mode}")
    own = con is None
    con = con or connect()
    try:
        if mode == "vector":
            ranked = _vector_rank(con, query, top_k)
        elif mode == "bm25":
            ranked = _bm25_rank(con, query, top_k)
        else:
            ranked = _rrf(_vector_rank(con, query, pool), _bm25_rank(con, query, pool))[:pool]

        meta = _rows(con, [cid for cid, _ in ranked])
        hits = [Hit(chunk_id=cid, doc=meta[cid]["doc"], page_no=meta[cid]["page_no"],
                    heading=meta[cid]["heading"], content=meta[cid]["content"], score=sc,
                    source=meta[cid]["source"], page_kind=meta[cid]["page_kind"],
                    image_path=meta[cid]["image_path"])
                for cid, sc in ranked if cid in meta]

        if mode == "hybrid_rerank" and hits:
            scores = _reranker().predict([(query, h.content) for h in hits])
            for h, s in zip(hits, scores):
                h.score = float(s)
            hits.sort(key=lambda h: -h.score)
        return hits[:top_k]
    finally:
        if own:
            con.close()
