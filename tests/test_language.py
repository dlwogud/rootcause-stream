"""웹 서비스의 한국어 출력 — 평가(영어)와 같은 코드 경로에서 지시 한 줄만 다르다."""
import json
from types import SimpleNamespace

from app.agent import loop
from app.agent.tools import photo


def _case():
    return SimpleNamespace(case_id="T-1", kind="weld_quality", alarm_count=1, window_start="",
                           window_end="", cooccurrence={}, alarm_sample=[], data_ref=None)


def test_korean_instruction_only_when_asked():
    st = loop.initial_state(_case())
    en = loop._render_first(st, 9, loop.Ablation())
    ko = loop._render_first(st, 9, loop.Ablation(language="ko"))
    assert loop.KOREAN_OUTPUT not in en and loop.KOREAN_OUTPUT in ko
    assert "search queries" in loop.KOREAN_OUTPUT and "in English" in loop.KOREAN_OUTPUT   # 매뉴얼은 영어
    assert loop.Ablation(language="ko").label().endswith("lang_ko")


def test_photo_reader_korean(monkeypatch, tmp_path):
    img = tmp_path / "x.jpg"; img.write_bytes(b"\xff\xd8\xff")
    seen = []

    class R:
        returncode = 0
        stdout = json.dumps({"result": "{\"observation\": \"가운데 금속 돌기\"}", "modelUsage": {"m": 1}})
        stderr = ""
    monkeypatch.setattr(photo.subprocess, "run", lambda cmd, **k: seen.append(cmd[-1]) or R())
    photo.read_photo(img, "weld", language="ko")
    photo.read_photo(img, "weld")
    assert photo.KOREAN in seen[0] and photo.KOREAN not in seen[1]
