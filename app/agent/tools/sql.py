"""query_sql — Agent 가 **직접 질의를 써서** 공정 기록을 조사한다.

왜 만들었나 (2026-11-19, docs/15-agent-writes-sql.md)
  query_timeseries 는 '다른 작업일과 연속 일치하는 비율' 같은 결정적 신호를 **코드가 미리
  계산해서** 준다. 그러면 Agent 는 그 숫자를 읽기만 하고, 같은 숫자에 규칙 한 줄을 적용해도
  똑같이 맞힌다(scripts/94_rule_baseline.py). 무엇을 셀지를 사람이 정해 준 셈이다.
  이 도구는 계산된 신호 없이 **원시 기록 테이블과 SQL** 만 준다. 무엇을 확인할지는 Agent 가 정한다.

테이블  records(workday TEXT, seq INTEGER, ts TEXT, force REAL, current REAL, voltage REAL, weld_time REAL)
  - 모든 작업일의 모든 용접 기록. seq 는 작업일 안에서의 순서, ts 는 의사 타임스탬프
  - 사건 데이터(data_ref)가 있으면 그 작업일의 행을 사건 데이터로 바꿔 넣는다 (query_timeseries 와 같은 규칙)
  - **정답 라벨(is_dup 등)은 넣지 않는다**

안전 — Agent 가 쓴 질의를 실행하므로
  - 사건마다 새 **메모리 DB** (파일·네트워크 없음)
  - authorizer 로 읽기(SELECT·READ·FUNCTION·RECURSIVE)만 허용 — ATTACH·PRAGMA·쓰기 거부
  - 한 문장만, 실행 5초 제한, 결과 40행·셀 80자로 자른다
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pandas as pd

from app.stream.detectors import F, I, T, V

MAX_ROWS = 40
MAX_CELL = 80
TIME_LIMIT_S = 5.0
SCHEMA = ("records(workday TEXT, seq INTEGER, ts TEXT, force REAL, current REAL, "
          "voltage REAL, weld_time REAL)")

_ALLOWED = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
if hasattr(sqlite3, "SQLITE_RECURSIVE"):
    _ALLOWED.add(sqlite3.SQLITE_RECURSIVE)


def _frame(data_ref: str | None) -> pd.DataFrame:
    from app.agent.tools.timeseries import _case_frame, _frames
    full, _ = _frames()
    df = full
    if data_ref:
        case = _case_frame(data_ref)
        days = set(case["d"].astype(str))
        df = pd.concat([full[~full["d"].astype(str).isin(days)], case], ignore_index=True)
    out = pd.DataFrame({
        "workday": df["d"].astype(str), "seq": df["idx"].astype(int),
        "ts": pd.to_datetime(df["ts"]).dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "force": df[F].astype(float), "current": df[I].astype(float),
        "voltage": df[V].astype(float), "weld_time": df[T].astype(float)})
    return out.sort_values(["workday", "seq"]).reset_index(drop=True)


def _connect(data_ref: str | None) -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    _frame(data_ref).to_sql("records", con, index=False)
    con.execute("CREATE INDEX ix_day_seq ON records(workday, seq)")
    con.execute("CREATE INDEX ix_tuple ON records(force, current, voltage, weld_time)")
    con.commit()

    def auth(action, *_):
        return sqlite3.SQLITE_OK if action in _ALLOWED else sqlite3.SQLITE_DENY
    con.set_authorizer(auth)
    return con


def query_sql(sql: str = "", data_ref: str | None = None, **_) -> dict:
    sql = (sql or "").strip().rstrip(";").strip()
    if not sql:
        return {"error": "sql 이 비어 있다", "schema": SCHEMA}
    if ";" in sql:
        return {"error": "한 번에 한 문장만 실행한다", "schema": SCHEMA}
    con = _connect(data_ref)
    t0 = time.monotonic()
    con.set_progress_handler(lambda: int(time.monotonic() - t0 > TIME_LIMIT_S), 10_000)
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description or []]
        rows = cur.fetchmany(MAX_ROWS + 1)
    except sqlite3.DatabaseError as e:
        msg = str(e)
        if "interrupted" in msg:
            msg = f"{TIME_LIMIT_S:.0f}초 안에 끝나지 않았다 — 범위를 좁히거나 인덱스(workday, seq / 네 값)를 쓰는 조인으로 바꿔라"
        return {"error": msg[:300], "schema": SCHEMA}
    finally:
        con.close()
    clip = lambda v: (v[:MAX_CELL] + "…") if isinstance(v, str) and len(v) > MAX_CELL else (
        round(v, 6) if isinstance(v, float) else v)
    return {"columns": cols, "rows": [[clip(v) for v in r] for r in rows[:MAX_ROWS]],
            "truncated": len(rows) > MAX_ROWS, "ms": int((time.monotonic() - t0) * 1000)}


TOOL_DESCRIPTION = (f"공정 기록 전체에 읽기 전용 SQL(SQLite) 한 문장을 실행한다. 테이블 {SCHEMA} — "
                    "모든 작업일의 모든 용접 기록, seq 는 작업일 안의 순서. 결과는 최대 "
                    f"{MAX_ROWS}행. args: {{sql: str}}")
