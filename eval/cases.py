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
from app.stream.replay import add_pseudo_timestamps, to_events
from app.stream.windows import (
    BURST, LEVEL_SHIFT, Incident, StreamDetectors, detect_level_shifts, run_stream,
)

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
# ⚠️ Tier A 정답 수정 (2026-11-17) — 원래 라벨이 데이터와 맞지 않았다.
#
#   선행 프로젝트의 '혼입일' 라벨은 **원본(복제 포함)** 기준 ">3bar 가 1% 이상인 날"
#   로 정의됐다. 그런데 복제 구간을 제외하면 이상일의 >3bar 비율이 **0.00%** 가 되고
#   (원본에서는 16~21%), 가압력 분포가 안정일과 사실상 같아진다
#   (중앙값 2.31 vs 2.33~2.35, 최대 2.39 vs 2.40).
#   즉 '고압 모드 혼입' 이라는 현상은 전부 복제 기록 안에 있었다.
#
#   남는 사실은 두 개다.
#     (1) 그 작업일들은 안정일과 통계적으로 다르다 — 복제 제외 후에도
#         exact permutation p=0.0179 (선행 프로젝트가 순환성까지 검증했다)
#     (2) 그 차이는 가압력 중앙값이 0.02~0.04 bar 낮은 쪽으로 이동한 것이고,
#         전류는 따라 움직이지 않았다
#
#   공정 데이터만으로는 '실제로 낮은 힘으로 운전됐다' 와 '힘 측정이 낮게 읽혔다' 를
#   **가를 수 없다.** 그러므로 Tier A 의 정답은 특정 원인이 아니라
#   **"센서로는 결론 낼 수 없으니 독립적인 추가 관측이 필요하다"** 는 판단이다.
#   Agent 가 이 한계를 인식하고 가르는 관측을 요청하는지를 본다.
TRUTH = {
    "A": "공정 데이터만으로는 결론을 낼 수 없는 사건이다. 가압력 수준이 안정일 대비 "
         "낮은 쪽으로 이동했으나(중앙값 0.02~0.04 bar), 전류는 따라 움직이지 않았고 "
         "설비 고장의 징후도 없다. '실제로 낮은 힘으로 운전됐다'와 '힘 측정이 낮게 "
         "읽혔다'는 이 데이터로 구별되지 않는다. 올바른 결론은 측정 경로와 독립적인 "
         "추가 관측(설정값 표시 확인, 독립 압력 측정 등)을 요청하는 것이다.",
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
    cooccurrence: dict              # Agent 1단계 입력 (유형에 따라 내용이 다르다)
    kind: str = BURST               # burst | level_shift
    data_ref: str | None = None     # 합성 케이스의 공정 데이터 파일 (Tier B)
    alarm_sample: list = field(default_factory=list)
    injected: str | None = None     # Tier B 만

    def to_dict(self) -> dict:
        return asdict(self)


DATA_DIR = CASES_DIR / "data"


def _from_incident(inc: Incident, tier: str, truth: str, truth_key: str,
                   source: str, cid: str, injected: str | None = None,
                   data_ref: str | None = None) -> EvalCase:
    return EvalCase(
        case_id=cid, tier=tier, truth=truth, truth_key=truth_key, source=source,
        workday=inc.workday or inc.opened_at.date().isoformat(),
        alarm_count=inc.alarm_count,
        window_start=inc.window_start.isoformat(), window_end=inc.window_end.isoformat(),
        cooccurrence=inc.summary(), kind=inc.kind,
        alarm_sample=[{"ts": a.ts.isoformat(), "detector": a.detector, "tag": a.tag,
                       "severity": a.severity, "value": round(a.value, 6),
                       "threshold": a.threshold, "point_seq": a.point_seq}
                      for a in sorted(inc.alarms, key=lambda x: x.ts)[:25]],
        injected=injected, data_ref=data_ref)


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
    """Tier A(수준 이동) · Tier C(버스트).

    ⚠️ Tier A 는 **복제 제외 데이터**에서 만든다. 복제를 포함하면 이상일의 최대 버스트가
    복제 구간 안에 들어가 Tier A 와 Tier C 가 구별되지 않는다 (실제로 그 버그가 있었다 —
    Tier A 3건이 전부 dup_fraction 1.0 이었다).

    그리고 Tier A 는 버스트가 아니다. 복제 제외 시 이상일 알람은 32/45/39건으로
    어떤 임계로도 폭주가 아니다. 실제 신호는 작업일 단위 수준 이동이다
    (선행 프로젝트: 관리도 3/3, permutation p=0.0179).
    """
    out: list[EvalCase] = []

    # Tier A — 복제 제외 데이터의 관리도 사건
    #
    # 이상일에는 복제 구간도 함께 존재한다(실제 데이터의 성질이다). 두 현상이 같은 날
    # 겹쳐 있으므로 **각 사건에 해당 현상의 기록을 전달한다** — 수준 이동 사건에는
    # 그 작업일의 실제 생산 기록을, 복제 사건(Tier C)에는 복제 구간을.
    # 섞어서 주면 Agent 가 어느 현상을 설명해야 하는지 알 수 없고 채점도 무의미해진다.
    genuine = add_pseudo_timestamps(load_genuine())
    alarms_g, _ = run_stream(to_events(genuine), det=det)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for inc in detect_level_shifts(genuine, alarms_g):
        if inc.workday not in ANOM_DAYS:
            continue
        cid = f"A-{inc.workday}"
        ref = DATA_DIR / f"{cid}.csv"
        day = genuine[genuine["d"].astype(str) == inc.workday]
        day.to_csv(ref, index=False, encoding="utf-8")
        out.append(_from_incident(
            inc, "A", TRUTH["A"], "센서로 결론 불가 — 추가 관측 필요",
            "선행 프로젝트 permutation p=0.0179(차이의 존재) + 본 프로젝트 분석"
            "(복제 제외 시 >3bar 0.00% — 원인 특정 불가)",
            cid, data_ref=str(ref.relative_to(CASES_DIR.parent.parent))))

    # Tier C — 복제 구간의 버스트, 작업일마다 2구간씩 (2026-11-17 확장: 1건 → 8건)
    #
    # 1건일 때는 실행 한 번이 곧 0% 아니면 100% 였다. 같은 조건을 다시 돌리면 결과가
    # 뒤집혀 조건 간 비교가 불가능했다. 복제 구간이 95%+ 인 버스트가 87건 있으므로
    # 복제가 나타나는 4개 작업일에서 서로 다른 시간대 2구간씩 뽑는다.
    # ⚠️ 8건은 같은 복제 수열의 다른 구간이다. 서로 다른 8개 고장이 아니다.
    full = mark_duplicates(load_raw())
    _, incidents = run_stream(to_events(full), det=det)
    dup = [i for i in incidents if i.cooccurrence()["dup_fraction"] >= 0.95]
    for day in sorted({i.workday for i in dup}):
        cands = sorted((i for i in dup if i.workday == day), key=lambda x: x.window_start)
        picks = [cands[0], cands[len(cands) // 2]] if len(cands) > 1 else cands
        ref = DATA_DIR / f"C-{day}.csv"
        full[full["d"].astype(str) == day].pipe(add_pseudo_timestamps).to_csv(
            ref, index=False, encoding="utf-8")
        for inc in picks:
            out.append(_from_incident(
                inc, "C", TRUTH["C"], "데이터 수집 계통 이상",
                "선행 프로젝트 행해시+최장공통런 복제 구간 탐지 (kamp-welding)",
                f"C-{day}-{inc.window_start:%H%M}",
                data_ref=str(ref.relative_to(CASES_DIR.parent.parent))))
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
            cid = f"B-{kind}-k{k:g}"
            # 주입된 프레임을 저장한다. 저장하지 않으면 query_timeseries 가
            # 타임스탬프로 **원본(주입 전)** 데이터를 조회해 버린다.
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            ref = DATA_DIR / f"{cid}.csv"
            events[0]  # noqa: B018  (events 가 비어 있지 않음을 보장)
            frame = add_pseudo_timestamps(a)
            frame.to_csv(ref, index=False, encoding="utf-8")
            out.append(_from_incident(
                inc, "B", f"{desc} (주입 강도 {k}σ)", kind,
                "본 프로젝트가 주입 — 합성 라벨", cid, injected=kind,
                data_ref=str(ref.relative_to(CASES_DIR.parent.parent))))
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
        print(f"    {c.case_id:22s} [{c.kind:11s}] 알람 {c.alarm_count:3d}  {c.truth_key}")
