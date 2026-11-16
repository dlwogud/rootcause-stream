"""SQLite 접근 계층.

1단계는 SQLite, 2단계(11/29~)에서 Postgres + pgvector 로 이전한다.
결정 근거는 docs/99-open-decisions.md 참조 — 요약하면 메모리 여유가 4GB뿐이라
Docker Desktop(~2GB)을 띄우면 임베딩 모델을 돌릴 수 없고, 데이터 규모가 작다.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "rootcause.db"
SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def connect(path: Path | None = None) -> sqlite3.Connection:
    con = sqlite3.connect(path or DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db(path: Path | None = None, drop: bool = False) -> sqlite3.Connection:
    p = path or DB_PATH
    if drop and p.exists():
        p.unlink()
    p.parent.mkdir(parents=True, exist_ok=True)
    con = connect(p)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.commit()
    return con


# ── 벡터 직렬화 ────────────────────────────────────────────────
def to_blob(v: np.ndarray) -> bytes:
    return np.asarray(v, dtype=np.float32).tobytes()


def from_blob(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)


def load_matrix(rows: list[sqlite3.Row], col: str = "embedding") -> np.ndarray:
    return np.stack([from_blob(r[col]) for r in rows]) if rows else np.zeros((0, 0), np.float32)


def js(x) -> str:
    return json.dumps(x, ensure_ascii=False)
