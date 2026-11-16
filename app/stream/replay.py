"""CSV 리플레이어 — 1단계(11/28)의 이벤트 소스.

2단계(12/13)에서 Kafka Producer 로 교체한다. 그때 `Event` 스키마와
`replay()` 의 시그니처를 유지하면 소비자 코드는 바뀌지 않는다.

의사 타임스탬프
    원본 `working time` 은 **날짜 단위**다(시:분 없음). 작업일보다 잘게 쪼갤 수 없으므로
    각 작업일의 타점을 교대 시간(기본 08:00~16:00)에 균등 배치한다.
    이것은 가정이며 보고서에 명시한다 — 타점 간 실제 간격은 알 수 없다.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from datetime import datetime, time as dtime, timedelta
from typing import Iterator

import pandas as pd

from app.stream.detectors import F, I, T, V, load_raw, mark_duplicates

SHIFT_START = dtime(8, 0)
SHIFT_HOURS = 8.0


@dataclass(frozen=True, slots=True)
class Event:
    ts: datetime
    equipment_id: str
    point_seq: int
    force: float
    current: float
    voltage: float
    weld_time: float
    workday: str
    is_dup: bool          # Tier C 평가용 플래그. 제거하지 않고 표시만 한다

    def as_dict(self) -> dict:
        d = asdict(self)
        d["ts"] = self.ts.isoformat()
        return d


def add_pseudo_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """작업일 안에서 타점을 교대 시간에 균등 배치한다."""
    out = df.sort_values(["d", "idx"]).copy()
    parts = []
    for day, g in out.groupby("d", sort=True):
        n = len(g)
        base = datetime.combine(day, SHIFT_START)
        step = timedelta(hours=SHIFT_HOURS) / max(n, 1)
        g = g.copy()
        g["ts"] = [base + step * k for k in range(n)]
        parts.append(g)
    return pd.concat(parts).sort_values("ts").reset_index(drop=True)


def to_events(df: pd.DataFrame, equipment_id: str = "RSW-01") -> list[Event]:
    if "ts" not in df.columns:
        df = add_pseudo_timestamps(df)
    if "is_dup" not in df.columns:
        df = mark_duplicates(df)
    return [
        Event(ts=r.ts.to_pydatetime() if hasattr(r.ts, "to_pydatetime") else r.ts,
              equipment_id=equipment_id, point_seq=int(r.idx),
              force=float(getattr(r, "c_force")), current=float(getattr(r, "c_current")),
              voltage=float(getattr(r, "c_voltage")), weld_time=float(getattr(r, "c_weldtime")),
              workday=str(r.d), is_dup=bool(r.is_dup))
        for r in df.rename(columns={F: "c_force", I: "c_current",
                                    V: "c_voltage", T: "c_weldtime"}).itertuples()
    ]


def replay(events: list[Event], speed: float = 0.0) -> Iterator[Event]:
    """이벤트를 순서대로 흘린다.

    speed=0 이면 지연 없이 즉시(평가·배치용). speed=60 이면 실시간의 60배로 재생한다
    (시연용 — 8시간 교대가 8분에 지나간다).
    """
    if speed <= 0:
        yield from events
        return
    t0_wall = time.monotonic()
    t0_evt = events[0].ts
    for e in events:
        target = (e.ts - t0_evt).total_seconds() / speed
        drift = target - (time.monotonic() - t0_wall)
        if drift > 0:
            time.sleep(drift)
        yield e


def load_stream(days: list[str] | None = None, equipment_id: str = "RSW-01") -> list[Event]:
    """원본에서 이벤트 스트림을 만든다. 복제 구간은 **제거하지 않고 표시만** 한다."""
    df = mark_duplicates(load_raw())
    if days:
        df = df[df["d"].astype(str).isin(days)]
    return to_events(add_pseudo_timestamps(df), equipment_id)
