"""윈도우 집계 · 알람 생성 · 버스트 감지.

1단계는 순수 Python 으로 구현하고, 2단계(12/13)에서 동일 로직을 PyFlink Table API 로
이식한다. 그래서 이 모듈은 **상태를 명시적으로 들고 있고 프레임워크에 의존하지 않는다.**

탐지기는 `detectors.py` 의 것을 그대로 쓴다. 여기서 하는 일은 그것을
'작업일 단위 사후 분석' 에서 '윈도우 단위 온라인' 으로 돌리는 것뿐이다.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from app.stream.detectors import (
    F, FEATS, I, KNNDetector, STABLE_DAYS, T, V, load_genuine, physics,
)
from app.stream.replay import Event

# 알람 임계 — 선행 프로젝트의 운영 후보값
P_FLAG = 0.0038          # 컨포멀 p 임계 (팽창계수 반영). 명목 0.01 은 교차일에서 깨진다
CHART_LIMIT = 2.0        # 가압력 중앙값 2σ
BURST_MIN_ALARMS = 8     # 윈도우 내 알람 수가 이 이상이면 버스트


@dataclass(frozen=True, slots=True)
class Alarm:
    ts: datetime
    equipment_id: str
    detector: str          # knn | chart | residual
    tag: str               # 어떤 신호가 울렸나
    severity: int          # 1 낮음 ~ 3 높음
    value: float
    threshold: float
    point_seq: int
    is_dup: bool = False   # Tier C — 복제 구간에서 발생한 알람인가


# ── 사건 유형 2종 ──────────────────────────────────────────────
# 선행 프로젝트가 통계적으로 확정한 사실: 이 공정의 실제 이상은 **작업일 단위 수준 이동**
# 이지 점 단위 이상치가 아니다 (kNN+컨포멀+CUSUM 0/3 vs 관리도 3/3, permutation p=0.0179).
# 본 프로젝트의 측정도 같다 — 복제 제외 시 이상일 알람 32/45/39건으로 폭주가 없고,
# 폭주하는 쪽(1,060건)은 복제 구간이었다.
#
# 통계적 공정관리에서 원래 둘로 나뉘는 현상이고, 현장 의미와 대응이 다르므로
# Agent 의 추론 경로도 갈라진다 (docs/02-architecture.md).
#   burst       : 짧은 구간에 다수 발화. 첫 과제는 "어느 알람이 원인이고 어느 게 결과인가"
#   level_shift : 평균이 조용히 이동. 첫 과제는 "언제부터 바뀌었고 무엇이 함께 움직였나"
BURST = "burst"
LEVEL_SHIFT = "level_shift"


@dataclass
class Incident:
    id: int
    equipment_id: str
    opened_at: datetime
    window_start: datetime
    window_end: datetime
    alarms: list[Alarm] = field(default_factory=list)
    workday: str = ""
    kind: str = BURST
    shift: dict = field(default_factory=dict)   # level_shift 만

    @property
    def alarm_count(self) -> int:
        return len(self.alarms)

    def summary(self) -> dict:
        """Agent 1단계 입력. 유형에 따라 다른 것을 준다."""
        if self.kind == LEVEL_SHIFT:
            return {"incident_kind": LEVEL_SHIFT, "shift": self.shift,
                    "alarm_count": self.alarm_count,
                    "by_tag": dict(Counter(a.tag for a in self.alarms)),
                    "note": "이 사건은 알람 폭주가 아니다. 작업일 단위로 공정 수준이 이동했다."}
        c = self.cooccurrence()
        c["incident_kind"] = BURST
        return c

    def cooccurrence(self) -> dict:
        """어떤 탐지기·태그가 함께 울렸는지, 그리고 선후 관계.

        Agent 의 1단계 입력이 된다. 알람 원문 수백 건 대신 이 요약을 투입한다
        (기술 #1 — 끄면 토큰이 폭증하고 정확도가 떨어진다).
        """
        by_tag = Counter(a.tag for a in self.alarms)
        by_det = Counter(a.detector for a in self.alarms)
        first_seen = {}
        for a in sorted(self.alarms, key=lambda x: x.ts):
            first_seen.setdefault(a.tag, a.ts)
        order = [t for t, _ in sorted(first_seen.items(), key=lambda kv: kv[1])]
        return {
            "by_detector": dict(by_det),
            "by_tag": dict(by_tag),
            "first_seen_order": order,
            "lead_tag": order[0] if order else None,
            "span_s": (self.window_end - self.window_start).total_seconds(),
            "dup_fraction": round(
                sum(a.is_dup for a in self.alarms) / max(len(self.alarms), 1), 3),
        }


class StreamDetectors:
    """안정일로 적합한 탐지기 묶음. 이벤트를 받아 알람을 낸다."""

    def __init__(self, window: timedelta = timedelta(minutes=10)):
        self.window = window
        self._buf: list[Event] = []
        self._win_start: datetime | None = None

    # ── 적합 ────────────────────────────────────────────────────
    def fit(self) -> "StreamDetectors":
        stable = physics(load_genuine(stable_only=True))
        self.knn = KNNDetector().fit(stable[FEATS].to_numpy())
        # 교정셋 = 안정일 자신 (운영에서는 별도 분리가 맞지만 여기선 선행 설정을 따른다)
        self.knn.calibrate(stable[FEATS].to_numpy())

        # 관리도 한계 — 안정일 작업일 중앙값의 분포
        med = stable.groupby("d")[F].median()
        self.chart_center = float(med.mean())
        self.chart_sigma = float(med.std(ddof=1))

        # 정상운전 모델: 가압력 → 전류 (선행 LODO R² 0.509)
        x, y = stable[F].to_numpy(), stable[I].to_numpy()
        self.res_slope, self.res_icpt = np.polyfit(x, y, 1)
        resid = y - (self.res_slope * x + self.res_icpt)
        self.res_sigma = float(np.std(resid, ddof=1))
        return self

    # ── 윈도우 단위 처리 ─────────────────────────────────────────
    def reset(self) -> "StreamDetectors":
        """윈도우 버퍼를 비운다.

        적합(fit) 결과는 유지하고 스트림 상태만 지운다. 같은 탐지기로 여러 스트림을
        연달아 돌릴 때 이것을 빠뜨리면 **이전 실행의 꼬리가 다음 실행 첫 윈도우에
        섞인다.** 실제로 그 버그가 있었다 — Tier B 합성 케이스 4건이 전부 같은
        알람 수(76)와 이전 실행의 타임스탬프를 갖게 됐다.
        """
        self._buf = []
        self._win_start = None
        return self

    def push(self, e: Event) -> list[Alarm]:
        """이벤트를 넣고, 윈도우가 닫히면 그 윈도우의 알람을 반환한다."""
        if self._win_start is None:
            self._win_start = e.ts
        if e.ts - self._win_start >= self.window:
            out = self._close()
            self._buf = [e]
            self._win_start = e.ts
            return out
        self._buf.append(e)
        return []

    def flush(self) -> list[Alarm]:
        return self._close()

    def _close(self) -> list[Alarm]:
        if not self._buf:
            return []
        df = pd.DataFrame([{F: e.force, I: e.current, V: e.voltage, T: e.weld_time,
                            "ts": e.ts, "seq": e.point_seq, "dup": e.is_dup}
                           for e in self._buf])
        d = physics(df)
        alarms: list[Alarm] = []
        eq = self._buf[0].equipment_id

        # 1) kNN 컨포멀 — 점 단위
        p = self.knn.pvalue(d[FEATS].to_numpy())
        for pv, row in zip(p, d.itertuples()):
            if pv < P_FLAG:
                alarms.append(Alarm(ts=row.ts, equipment_id=eq, detector="knn",
                                    tag="knn_conformal",
                                    severity=3 if pv < P_FLAG / 2 else 2,
                                    value=float(pv), threshold=P_FLAG,
                                    point_seq=int(row.seq), is_dup=bool(row.dup)))

        # 2) 관리도 — 윈도우 중앙값
        m = float(d[F].median())
        lo = self.chart_center - CHART_LIMIT * self.chart_sigma
        hi = self.chart_center + CHART_LIMIT * self.chart_sigma
        if m < lo or m > hi:
            alarms.append(Alarm(ts=self._buf[-1].ts, equipment_id=eq, detector="chart",
                                tag="force_median_low" if m < lo else "force_median_high",
                                severity=3, value=m, threshold=lo if m < lo else hi,
                                point_seq=int(d["seq"].iloc[-1]),
                                is_dup=bool(d["dup"].mean() > 0.5)))

        # 3) 잔차 — 정상운전 모델 이탈
        pred = self.res_slope * d[F].to_numpy() + self.res_icpt
        z = (d[I].to_numpy() - pred) / max(self.res_sigma, 1e-9)
        for zz, row in zip(z, d.itertuples()):
            if abs(zz) > 3.0:
                alarms.append(Alarm(ts=row.ts, equipment_id=eq, detector="residual",
                                    tag="current_residual", severity=2,
                                    value=float(zz), threshold=3.0,
                                    point_seq=int(row.seq), is_dup=bool(row.dup)))
        return alarms


def detect_bursts(alarms: list[Alarm], window: timedelta = timedelta(minutes=10),
                  min_alarms: int = BURST_MIN_ALARMS) -> list[Incident]:
    """알람을 텀블링 윈도우로 묶고, 임계 이상이면 Incident 로 승격한다."""
    if not alarms:
        return []
    alarms = sorted(alarms, key=lambda a: a.ts)
    out, cur, start, nid = [], [], alarms[0].ts, 0
    for a in alarms:
        if a.ts - start >= window:
            if len(cur) >= min_alarms:
                nid += 1
                out.append(Incident(id=nid, equipment_id=cur[0].equipment_id,
                                    opened_at=cur[0].ts, window_start=start,
                                    window_end=start + window, alarms=list(cur)))
            cur, start = [], a.ts
        cur.append(a)
    if len(cur) >= min_alarms:
        nid += 1
        out.append(Incident(id=nid, equipment_id=cur[0].equipment_id, opened_at=cur[0].ts,
                            window_start=start, window_end=start + window, alarms=list(cur)))
    return out


def detect_level_shifts(df, alarms: list[Alarm], limit: float = CHART_LIMIT,
                        col: str = F, stat: str = "median",
                        stable_days: list[str] | None = None,
                        equipment_id: str = "RSW-01") -> list[Incident]:
    """작업일 단위 관리도 사건 — 선행 프로젝트가 3/3 으로 검증한 신호.

    `df` 는 **복제 제외 데이터**여야 한다. 복제 구간을 포함하면 수준 이동이 아니라
    중복 적재의 허상을 잡는다 (실제로 그 실수가 있었다 — Tier A 3건이 전부
    dup_fraction 1.0 으로 나와 Tier C 와 구별되지 않았다).
    """
    from app.stream.detectors import chart_summary, day_control_chart

    verdicts = day_control_chart(df, col=col, stat=stat, limit=limit,
                                 stable_days=stable_days)
    by_day: dict[str, list[Alarm]] = {}
    for a in alarms:
        by_day.setdefault(a.ts.date().isoformat(), []).append(a)

    out, nid = [], 0
    for v in verdicts:
        if not v.outside:
            continue
        day_alarms = sorted(by_day.get(v.day, []), key=lambda a: a.ts)
        if day_alarms:
            t0, t1 = day_alarms[0].ts, day_alarms[-1].ts
        else:
            d = df[df["d"].astype(str) == v.day]
            t0 = t1 = d["ts"].min() if "ts" in d.columns else datetime.fromisoformat(v.day + "T08:00:00")
        nid += 1
        out.append(Incident(
            id=10_000 + nid, equipment_id=equipment_id, opened_at=t0,
            window_start=t0, window_end=t1, alarms=day_alarms, workday=v.day,
            kind=LEVEL_SHIFT,
            shift={"variable": col, "statistic": stat, "day_value": round(v.value, 4),
                   "control_center": round(v.center, 4),
                   "control_limits": [round(v.center - limit * v.sigma, 4),
                                      round(v.center + limit * v.sigma, 4)],
                   "sigma": round(v.sigma, 5), "direction": v.direction,
                   "shift_in_sd": round((v.value - v.center) / v.sigma, 2) if v.sigma else None,
                   "limit_sigma": limit,
                   "basis": "안정일 leave-one-out 추정 관리한계"}))
    return out


def run_stream(events: list[Event], window: timedelta = timedelta(minutes=10),
               det: StreamDetectors | None = None) -> tuple[list[Alarm], list[Incident]]:
    d = (det or StreamDetectors(window=window).fit()).reset()
    alarms: list[Alarm] = []
    for e in events:
        alarms += d.push(e)
    alarms += d.flush()
    incidents = detect_bursts(alarms, window=window)
    for inc in incidents:
        inc.workday = inc.opened_at.date().isoformat()
    return alarms, incidents
