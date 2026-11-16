"""평가 케이스 생성 — Tier A(실측) / B(합성) / C(데이터품질).

**정답 라벨의 출처가 이 프로젝트 바깥에 있다는 것이 평가의 전제다.**
Tier A 는 선행 프로젝트가 exact permutation test(p=0.0179)로 입증한 실제 공정 이동이고,
Tier C 는 행 해시 + 최장공통런으로 사전 임계 없이 발견된 복제 구간이다.
Tier B 만 주입한 것이며, 성과표에서 **항상 분리 표기**한다.

출처: docs/05-data.md
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from app.stream.detectors import (
    F, I, STABLE_DAYS, T, V, load_genuine, load_raw, mark_duplicates, physics,
)
from app.stream.replay import to_events
from app.stream.windows import Incident, StreamDetectors, run_stream

CASES_DIR = Path(__file__).resolve().parent / "cases"

ANOM_DAYS = ["2020-03-25", "2020-03-27", "2020-03-31"]
DUP_DAY = "2020-04-03"

# 선행 프로젝트의 7종 이상 모드 (src/14_final_model.py)
FAULT_MODES = {
    "A1_결합이탈":   "전류가 가압력과의 정상 결합에서 벗어났다",
    "A2_가압이탈":   "가압력이 정상 수준에서 이동했다",
    "A3_전압강하":   "용접 전압이 떨어졌다",
    "A4_통전단축":   "통전 시간이 짧아졌다",
    "A5_동시드리프트": "가압력과 전류가 반대 방향으로 함께 흘렀다",
    "A6_산포증가":   "가압력·전류의 산포가 커졌다",
    "A7_지속반복이상": "공정 변수가 한 값에 고정되어 반복됐다",
}

# ⚠️ Tier B 채점의 한계 (2026-11-16 하네스 1차 실행에서 확인)
#   Tier B 정답은 '무엇을 조작했는가'(통계적 조작)를 기술하는 반면, 진단 시스템은
#   '어떤 물리적 고장인가'를 답한다. 층위가 달라 M1 으로 채점하면 부당하게 0 이 나온다.
#   → **Tier B 의 주 지표는 M2(주 변수 식별)** 이고 M1 은 참고로만 보고한다.
#   Tier A/C 는 정답 자체가 물리적·공정적 원인이므로 M1 이 주 지표다.
TRUTH = {
    "A": "이질 운전 모드 혼입 — 주 레시피(약 2.3bar)와 다른 고압 운전이 섞여 "
         "작업일 가압력 수준이 이동했다. 설비 고장이 아니라 운전 조건의 문제다.",
    "C": "데이터 수집 계통 이상 — 동일한 공정 기록이 통째로 반복 적재됐다. "
         "설비는 정상이며 이상 신호는 중복 데이터가 만든 허상이다.",
}


@dataclass
class EvalCase:
    case_id: str
    tier: str                 # A | B | C
    truth: str                # 자연어 정답 (LLM-as-Judge 가 대조한다)
    truth_key: str            # 짧은 라벨
    source: str               # 라벨의 출처
    workday: str
    alarm_count: int
    window_start: str
    window_end: str
    cooccurrence: dict
    alarm_sample: list = field(default_factory=list)
    injected: str | None = None     # Tier B 만

    def to_dict(self) -> dict:
        return asdict(self)


def _from_incident(inc: Incident, tier: str, truth: str, truth_key: str,
                   source: str, cid: str, injected: str | None = None) -> EvalCase:
    return EvalCase(
        case_id=cid, tier=tier, truth=truth, truth_key=truth_key, source=source,
        workday=inc.workday or inc.opened_at.date().isoformat(),
        alarm_count=inc.alarm_count,
        window_start=inc.window_start.isoformat(), window_end=inc.window_end.isoformat(),
        cooccurrence=inc.cooccurrence(),
        alarm_sample=[{"ts": a.ts.isoformat(), "detector": a.detector, "tag": a.tag,
                       "severity": a.severity, "value": round(a.value, 6),
                       "threshold": a.threshold, "point_seq": a.point_seq}
                      for a in sorted(inc.alarms, key=lambda x: x.ts)[:25]],
        injected=injected)


def inject(te: pd.DataFrame, kind: str, sd: dict, k: float, rng) -> pd.DataFrame:
    """선행 프로젝트의 이상 주입 함수 (src/14_final_model.py). 로직 불변."""
    a = te.copy()
    f = a[F].to_numpy()
    dirn = np.sign(f - np.median(f)); dirn[dirn == 0] = 1
    if kind == "A1_결합이탈":
        a[I] = a[I].to_numpy() + dirn * k * sd[I]
    elif kind == "A2_가압이탈":
        a[F] = a[F].to_numpy() + dirn * k * sd[F]
    elif kind == "A3_전압강하":
        a[V] = a[V].to_numpy() - k * sd[V]
    elif kind == "A4_통전단축":
        a[T] = a[T].to_numpy() - k * sd[T]
    elif kind == "A5_동시드리프트":
        a[F] = a[F].to_numpy() + k * sd[F]
        a[I] = a[I].to_numpy() - k * sd[I] * 0.735
    elif kind == "A6_산포증가":
        a[F] = a[F].to_numpy() + rng.normal(0, k * sd[F], len(a))
        a[I] = a[I].to_numpy() + rng.normal(0, k * sd[I], len(a))
    elif kind == "A7_지속반복이상":
        a[F] = float(np.median(a[F].to_numpy()) + k * sd[F])
        a[I] = float(np.median(a[I].to_numpy()) - k * sd[I])
        a[V] = float(np.median(a[V].to_numpy()))
        a[T] = float(np.median(a[T].to_numpy()))
    return a


def build_real_cases(det: StreamDetectors) -> list[EvalCase]:
    """Tier A · C — 실제 데이터에서 가장 큰 Incident 를 작업일별로 1건씩."""
    df = mark_duplicates(load_raw())
    events = to_events(df)
    _, incidents = run_stream(events, det=det)
    by_day: dict[str, Incident] = {}
    for inc in incidents:
        d = inc.workday
        if d not in by_day or inc.alarm_count > by_day[d].alarm_count:
            by_day[d] = inc

    out = []
    for d in ANOM_DAYS:
        if d in by_day:
            out.append(_from_incident(
                by_day[d], "A", TRUTH["A"], "이질 운전 모드 혼입",
                "선행 프로젝트 exact permutation test p=0.0179 (kamp-welding)",
                f"A-{d}"))
    if DUP_DAY in by_day:
        out.append(_from_incident(
            by_day[DUP_DAY], "C", TRUTH["C"], "데이터 수집 계통 이상",
            "선행 프로젝트 행해시+최장공통런 복제 구간 탐지 (kamp-welding)",
            f"C-{DUP_DAY}"))
    return out


def build_synthetic_cases(det: StreamDetectors, severities=(2.0,), seed: int = 42) -> list[EvalCase]:
    """Tier B — 안정일 데이터에 7종 이상을 주입한다. **합성임을 항상 표기한다.**"""
    rng = np.random.default_rng(seed)
    stable = load_genuine(stable_only=True)
    sd = {c: float(stable[c].std(ddof=1)) for c in (F, I, V, T)}
    base_day = STABLE_DAYS[-1]
    base = stable[stable["d"].astype(str) == base_day].copy()

    out = []
    for kind, desc in FAULT_MODES.items():
        for k in severities:
            a = inject(base, kind, sd, k, rng)
            events = to_events(a)
            _, incs = run_stream(events, det=det)
            if not incs:
                continue
            inc = max(incs, key=lambda x: x.alarm_count)
            out.append(_from_incident(
                inc, "B", f"{desc} (주입 강도 {k}σ)", kind,
                "본 프로젝트가 주입 — 합성 라벨",
                f"B-{kind}-k{k:g}", injected=kind))
    return out


def build_all(seed: int = 42) -> list[EvalCase]:
    det = StreamDetectors().fit()
    return build_real_cases(det) + build_synthetic_cases(det, seed=seed)


def save(cases: list[EvalCase], path: Path | None = None) -> Path:
    p = path or (CASES_DIR / "cases.jsonl")
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
    return p


def load(path: Path | None = None) -> list[EvalCase]:
    p = path or (CASES_DIR / "cases.jsonl")
    return [EvalCase(**json.loads(l)) for l in open(p, encoding="utf-8")]


if __name__ == "__main__":
    cs = build_all()
    p = save(cs)
    import collections
    print(f"케이스 {len(cs)}건 → {p}")
    for t, n in sorted(collections.Counter(c.tier for c in cs).items()):
        print(f"  Tier {t}: {n}건")
    for c in cs:
        print(f"    {c.case_id:22s} 알람 {c.alarm_count:3d}  {c.truth_key}")
