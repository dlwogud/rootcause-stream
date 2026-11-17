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
