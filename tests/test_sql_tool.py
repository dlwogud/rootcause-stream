"""query_sql — 읽기만 되고, 라벨이 없고, 사건 데이터가 반영되는가."""
from __future__ import annotations

import pytest

from app.agent.tools.sql import query_sql


def test_basic_select():
    r = query_sql("SELECT workday, COUNT(*) FROM records GROUP BY workday ORDER BY workday")
    assert "error" not in r and len(r["rows"]) == 9
    assert sum(n for _, n in r["rows"]) == 11939


def test_no_label_column():
    r = query_sql("SELECT * FROM records LIMIT 1")
    assert r["columns"] == ["workday", "seq", "ts", "force", "current", "voltage", "weld_time"]


@pytest.mark.parametrize("sql", [
    "DELETE FROM records",
    "UPDATE records SET force = 0",
    "INSERT INTO records (workday) VALUES ('x')",
    "DROP TABLE records",
    "CREATE TABLE t (a)",
    "ATTACH DATABASE '/tmp/x.db' AS x",
    "PRAGMA table_info(records)",
    "SELECT 1; DELETE FROM records",
])
def test_write_and_escape_denied(sql):
    assert "error" in query_sql(sql)


def test_timeout():
    r = query_sql("WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c) SELECT max(x) FROM c")
    assert "error" in r


def test_row_limit():
    r = query_sql("SELECT * FROM records")
    assert len(r["rows"]) == 40 and r["truncated"]


def test_case_data_replaces_its_workday():
    """Tier A 사건 데이터(복제 라벨 제외 기록)를 주면 그 작업일은 그 데이터로 바뀐다."""
    from eval.cases import load
    a = next(c for c in load() if c.case_id == "A-2020-03-25")
    r = query_sql("SELECT COUNT(*) FROM records WHERE workday = '2020-03-25'", data_ref=a.data_ref)
    assert r["rows"][0][0] == 552
