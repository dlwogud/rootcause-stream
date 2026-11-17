"""웹 서비스 라우트 — LLM 호출 없이 검증할 수 있는 것만."""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.main import SESSIONS, TOKENS, Session, app

client = TestClient(app)


def test_dashboard_lists_all_cases():
    r = client.get("/")
    assert r.status_code == 200
    assert r.text.count("onclick=\"start(") >= 11


def test_unknown_case_rejected():
    assert client.post("/api/sessions", json={"case_id": "없음"}).status_code == 404


@pytest.mark.parametrize("path", ["../../etc/passwd", "app/main.py", "data/rootcause.db",
                                  "data/photos/../../app/main.py"])
def test_photo_path_traversal_blocked(path):
    """사진 서빙은 data/photos 아래만 허용한다."""
    assert client.get("/photo", params={"path": path}).status_code == 404


def test_photo_served_from_allowed_dir():
    r = client.get("/photo", params={"path": "data/photos/tier_d/electrode_tip_clean.jpg"})
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"


def test_unknown_token_gone():
    assert client.get("/m/upload/없는토큰").status_code == 410
    assert client.get("/qr/없는토큰.png").status_code == 404


def test_expired_token_gone():
    """촬영 링크는 1회성이고 15분 뒤 만료된다."""
    s = Session(id="t-exp", case_id="D1-cooling-scaled")
    s.token, s.token_expires = "expired", time.time() - 1
    SESSIONS[s.id] = s
    TOKENS["expired"] = s.id
    try:
        assert client.get("/m/upload/expired").status_code == 410
    finally:
        SESSIONS.pop(s.id, None)
        TOKENS.pop("expired", None)


def test_demo_photo_requires_awaiting_state():
    """촬영 요청 대기 상태가 아니면 사진을 받지 않는다."""
    s = Session(id="t-idle", case_id="D1-cooling-scaled")
    SESSIONS[s.id] = s
    try:
        r = client.post(f"/api/sessions/{s.id}/demo_photo",
                        json={"path": "data/photos/tier_d/electrode_tip_clean.jpg"})
        assert r.status_code == 409
    finally:
        SESSIONS.pop(s.id, None)


# ── 녹화용 재생 ───────────────────────────────────────────────────
@pytest.mark.parametrize("name", ["../rootcause", "..%2F..%2Fapp", "a.b", "없는기록"])
def test_demo_run_rejects_bad_or_missing_name(name):
    """재생 기록은 data/demo_runs/<영숫자·-·_>.json 만 연다."""
    assert client.get(f"/api/demo_runs/{name}").status_code == 404


def test_demo_run_served_unchanged(tmp_path, monkeypatch):
    """재생은 기록을 그대로 돌려준다 — 서버가 내용을 바꾸지 않는다."""
    import json

    import app.main as m
    rec = {"meta": {"case_id": "A-2020-03-25"},
           "events": [{"type": "incident", "seq": 0, "t": 1.0},
                      {"type": "final", "seq": 1, "t": 9.0, "root_cause": "x"}]}
    (tmp_path / "t-run.json").write_text(json.dumps(rec, ensure_ascii=False))
    monkeypatch.setattr(m, "DEMO_RUNS", tmp_path)
    assert client.get("/api/demo_runs/t-run").json() == rec


def test_dashboard_has_replay_and_autostart_hooks():
    t = client.get("/").text
    assert "P.get('replay')" in t and "P.get('autostart')" in t
    assert "실제 실행 기록" in t              # 재생 화면은 기록임을 항상 표시한다
