"""리플레이어 · 윈도우 처리 · 버스트 감지."""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.stream.detectors import STABLE_DAYS
from app.stream.replay import Event, add_pseudo_timestamps, load_stream, replay
from app.stream.windows import StreamDetectors, detect_bursts, run_stream

DUP_DAY = "2020-04-03"
ANOM_DAYS = ["2020-03-25", "2020-03-27", "2020-03-31"]


@pytest.fixture(scope="module")
def events():
    return load_stream()


@pytest.fixture(scope="module")
def result(events):
    return run_stream(events)


def test_event_count(events):
    assert len(events) == 11939


def test_timestamps_are_monotonic(events):
    ts = [e.ts for e in events]
    assert ts == sorted(ts)


def test_pseudo_timestamps_stay_within_workday(events):
    """의사 타임스탬프가 작업일을 넘지 않는다 (교대 08:00~16:00 가정)."""
    for e in events:
        assert e.ts.date().isoformat() == e.workday
        assert 8 <= e.ts.hour < 16


def test_dup_flag_preserved(events):
    """복제 구간은 제거하지 않고 표시만 한다 — Tier C 평가에 필요하다."""
    assert sum(e.is_dup for e in events) == 3200
    assert all(e.is_dup for e in events if e.workday == DUP_DAY)


def test_replay_without_delay_yields_all(events):
    assert len(list(replay(events[:100], speed=0))) == 100


def test_alarms_concentrate_on_anomalous_days(result):
    """이상일·복제일의 알람이 안정일보다 한 자릿수 이상 많아야 한다."""
    alarms, _ = result
    per_day = {}
    for a in alarms:
        per_day.setdefault(a.ts.date().isoformat(), 0)
        per_day[a.ts.date().isoformat()] += 1
    worst_stable = max(per_day.get(d, 0) for d in STABLE_DAYS)
    best_anom = min(per_day.get(d, 0) for d in ANOM_DAYS)
    assert best_anom > worst_stable * 5, f"안정일 최대 {worst_stable} vs 이상일 최소 {best_anom}"


def test_duplicate_day_produces_most_incidents(result):
    """Tier C — 복제일이 Incident 가 가장 많다.

    알람이 가장 많이 터지는 날이 설비 고장이 아니라 데이터 수집 이상이라는 것이
    이 평가 케이스의 핵심이다. Agent 가 '설비 이상 아님' 을 판정해야 한다.
    """
    _, incidents = result
    per_day = {}
    for i in incidents:
        per_day[i.workday] = per_day.get(i.workday, 0) + 1
    assert per_day.get(DUP_DAY, 0) == max(per_day.values())


def test_incident_cooccurrence_shape(result):
    _, incidents = result
    assert incidents
    c = incidents[0].cooccurrence()
    assert set(c) >= {"by_detector", "by_tag", "first_seen_order", "lead_tag",
                      "span_s", "dup_fraction"}
    assert c["lead_tag"] in c["by_tag"]
    assert 0.0 <= c["dup_fraction"] <= 1.0


def test_burst_threshold_respected():
    """알람 수가 임계 미만이면 Incident 가 생기지 않는다."""
    from datetime import datetime
    from app.stream.windows import Alarm
    base = datetime(2020, 3, 24, 8, 0)
    few = [Alarm(ts=base + timedelta(seconds=i), equipment_id="RSW-01", detector="knn",
                 tag="knn_conformal", severity=2, value=0.001, threshold=0.0038,
                 point_seq=i) for i in range(3)]
    assert detect_bursts(few, min_alarms=8) == []
    many = [Alarm(ts=base + timedelta(seconds=i), equipment_id="RSW-01", detector="knn",
                  tag="knn_conformal", severity=2, value=0.001, threshold=0.0038,
                  point_seq=i) for i in range(12)]
    assert len(detect_bursts(many, min_alarms=8)) == 1
