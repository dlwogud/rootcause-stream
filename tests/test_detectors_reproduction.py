"""선행 프로젝트 수치 재현 테스트.

이 테스트가 실패하면 탐지기 이식이 틀린 것이다. 이 프로젝트의 정답 라벨(Tier A/C)은
선행 프로젝트가 통계적으로 검증한 결과에 근거하므로, 탐지기가 달라지면 라벨의 근거가
사라진다. 수치를 맞추려고 라벨을 고치지 말 것 — 코드를 고쳐야 한다.

출처: ~/kamp-welding · outputs/tables/t55b_day_control_chart.csv
"""
from __future__ import annotations

import pytest

from app.stream.detectors import (
    F, I, STABLE_DAYS, chart_summary, day_control_chart, load_genuine, load_raw,
    mark_duplicates,
)


@pytest.fixture(scope="module")
def raw():
    return load_raw()


@pytest.fixture(scope="module")
def genuine():
    return load_genuine()


def test_raw_shape(raw):
    """용접점 11,939개 · 작업일 9일."""
    assert len(raw) == 11939
    assert raw["d"].nunique() == 9


def test_duplicate_ratio(raw):
    """복제 구간이 전체의 26.8%."""
    m = mark_duplicates(raw)
    ratio = m["is_dup"].mean()
    assert ratio == pytest.approx(0.268, abs=0.002), f"복제 비율 {ratio:.3%}"


def test_april3_entirely_duplicate(raw):
    """2020-04-03 은 작업일 전체가 복제 구간 → genuine 에서 사라진다."""
    m = mark_duplicates(raw)
    apr3 = m[m["d"].astype(str) == "2020-04-03"]
    assert len(apr3) > 0
    assert apr3["is_dup"].all(), "04-03 에 복제 아닌 행이 남았다"


def test_genuine_days(genuine):
    """복제 제외 후 8개 작업일 (04-03 소멸). 이상일은 3일."""
    days = sorted(str(x) for x in genuine["d"].unique())
    assert "2020-04-03" not in days
    assert len(days) == 8
    variable = [d for d in days if d not in STABLE_DAYS]
    assert variable == ["2020-03-25", "2020-03-27", "2020-03-31"]


@pytest.mark.parametrize("limit,expect", [(2.0, (3, 0)), (2.5, (3, 0)), (3.0, (0, 0))])
def test_force_median_control_chart(genuine, limit, expect):
    """가압력 중앙값 관리도 — 선행 프로젝트 t55b 표의 재현.

    2σ·2.5σ 에서 탐지 3/3·오경보 0/5, 3σ 에서는 0/3.
    """
    s = chart_summary(day_control_chart(genuine, col=F, stat="median", limit=limit))
    assert (s["detected"], s["false_alarms"]) == expect
    assert (s["n_variable"], s["n_stable"]) == (3, 5)


def test_current_median_is_not_a_detector(genuine):
    """전류 중앙값은 2σ 에서 0/3 — 가압력이 신호를 가진 변수임을 확인한다."""
    s = chart_summary(day_control_chart(genuine, col=I, stat="median", limit=2.0))
    assert s["detected"] == 0


def test_force_mean_weaker_than_median(genuine):
    """가압력 '평균' 은 2σ 에서 2/3 — 중앙값이 더 민감하다는 선행 결론."""
    s = chart_summary(day_control_chart(genuine, col=F, stat="mean", limit=2.0))
    assert s["detected"] == 2 and s["false_alarms"] == 0
