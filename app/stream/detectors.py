"""공정 이상 탐지기 — 선행 프로젝트(kamp-welding)에서 이식.

이식 원칙: **로직을 바꾸지 않는다.** 선행 프로젝트는 이 탐지기들의 성능을
실제 라벨로 검증했고(관리도 실제 shift 3/3·오경보 0/5, exact permutation p=0.0179),
그 수치가 이 프로젝트 정답 라벨(Tier A)의 출처다. 로직이 달라지면 라벨의 근거가 사라진다.

`tests/test_detectors_reproduction.py` 가 재현을 강제한다. 실패하면 이식이 틀린 것이다.

출처: ~/kamp-welding/src/{12_benchmark,14_final_model,17_operational_value}.py
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import RobustScaler

# ── 공정 변수 (원본 컬럼명 그대로) ──────────────────────────────────
F = "weld force(bar)"
I = "weld current(kA)"
V = "weld Voltage(v)"
T = "weld time(ms)"
PROC = [F, I, V, T]

# 물리 파생 공간 FS3 — 선행 벤치마크에서 1위
FEATS = [F, "R", "E"]

# 선행 프로젝트가 확정한 상수
N_NEIGHBORS = 3                       # 중첩 교차검증이 선택 (5개 폴드 모두 k=3)
STABLE_DAYS = ["2020-03-24", "2020-03-26", "2020-03-30", "2020-04-02", "2020-04-07"]
TEST_DATE = dt.date(2020, 3, 27)      # 라벨 없는 예측 대상일
RECIPE_EDGES = [0.0, 3.0, 5.0, 9.0, np.inf]
RECIPE_NAMES = ["A_주모드(~3bar)", "T_전이(3-5bar)", "B_고압(5-9bar)", "C_극고압(9bar+)"]
MAIN_RECIPE = RECIPE_NAMES[0]

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_XLSX = ROOT / "data" / "raw" / "Welding Data Set_01.xlsx"
DUP_INDEX = ROOT / "data" / "labels" / "duplicated_block_index.csv"


# ── 적재 ───────────────────────────────────────────────────────────
def load_raw(xlsx: Path | None = None) -> pd.DataFrame:
    """Raw data 시트 + 파생열 d(작업일), recipe.

    주의: `working time` 은 **날짜 단위**다(시:분 없음). 작업일보다 잘게 쪼갤 수 없으므로
    스트림 리플레이는 타점 순서로 의사 타임스탬프를 만든다(`replay.py`).
    """
    df = pd.read_excel(xlsx or DEFAULT_XLSX, sheet_name="Raw data")
    df.columns = [c.strip() for c in df.columns]
    df["d"] = pd.to_datetime(df["working time"]).dt.date
    df["recipe"] = pd.cut(df[F], bins=RECIPE_EDGES, labels=RECIPE_NAMES, right=False)
    return df


def physics(df: pd.DataFrame) -> pd.DataFrame:
    """동저항 R = V/I, 입열 E = V*I*t."""
    d = df.copy()
    amp = d[I] * 1000.0
    sec = d[T] / 1000.0
    d["R"] = d[V] / amp
    d["E"] = d[V] * amp * sec
    return d


# ── kNN 이상탐지 + 컨포멀 p값 ──────────────────────────────────────
class KNNDetector:
    """kNN 거리 기반 이상탐지.

    score(X)   : 평균 k-최근접 거리 (클수록 이상)
    pvalue(X)  : 컨포멀 p값. 교환가능한 교정에서만 FPR 제어가 성립한다
                 (선행 프로젝트가 교차일 운영에서 보장이 깨짐을 확인했다).
    """

    def __init__(self, k: int = N_NEIGHBORS):
        self.k = k
        self.cal_: np.ndarray | None = None

    def fit(self, X: np.ndarray) -> "KNNDetector":
        self.sc_ = RobustScaler().fit(X)
        self.nn_ = NearestNeighbors(n_neighbors=self.k).fit(self.sc_.transform(X))
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        dist, _ = self.nn_.kneighbors(self.sc_.transform(X))
        return dist.mean(axis=1)

    def calibrate(self, X_cal: np.ndarray) -> "KNNDetector":
        self.cal_ = np.sort(self.score(X_cal))
        return self

    def pvalue(self, X: np.ndarray) -> np.ndarray:
        if self.cal_ is None:
            raise RuntimeError("calibrate() 를 먼저 호출하라")
        s = self.score(X)
        ge = len(self.cal_) - np.searchsorted(self.cal_, s, side="left")
        return (1 + ge) / (len(self.cal_) + 1)


# ── 일 단위 관리도 ─────────────────────────────────────────────────
@dataclass
class ChartVerdict:
    day: str
    value: float
    center: float
    sigma: float
    outside: bool
    is_stable_day: bool

    @property
    def direction(self) -> str:
        if not self.outside:
            return "in_control"
        return "high" if self.value > self.center else "low"


def day_control_chart(df: pd.DataFrame, col: str = F, stat: str = "median",
                      limit: float = 2.0,
                      stable_days: list[str] | None = None) -> list[ChartVerdict]:
    """작업일 요약통계 관리도.

    관리한계는 **평가일을 제외한 안정일로만** 추정하고, 안정일 자신을 평가할 때는
    그 날을 뺀 나머지로 추정한다(leave-one-out). 자기 자신이 한계에 기여하면
    오경보율이 낙관적으로 나온다.
    """
    stable = stable_days if stable_days is not None else STABLE_DAYS
    day = df.groupby("d")[col].agg(stat)
    sta = {str(k): float(v) for k, v in day.items() if str(k) in stable}
    var = {str(k): float(v) for k, v in day.items() if str(k) not in stable}

    out: list[ChartVerdict] = []
    for k, v in {**sta, **var}.items():
        ref = [x for kk, x in sta.items() if kk != k]
        m, s = float(np.mean(ref)), float(np.std(ref, ddof=1))
        out.append(ChartVerdict(day=k, value=v, center=m, sigma=s,
                                outside=(v < m - limit * s) or (v > m + limit * s),
                                is_stable_day=k in sta))
    return sorted(out, key=lambda r: r.day)


def chart_summary(verdicts: list[ChartVerdict]) -> dict:
    """탐지/오경보 집계. 선행 프로젝트의 '3/3, 0/5' 가 여기서 재현되어야 한다."""
    var = [v for v in verdicts if not v.is_stable_day]
    sta = [v for v in verdicts if v.is_stable_day]
    return {
        "detected": sum(v.outside for v in var), "n_variable": len(var),
        "false_alarms": sum(v.outside for v in sta), "n_stable": len(sta),
    }


# ── 중복 블록 탐지 (Tier C 평가 케이스) ────────────────────────────
def load_dup_index(path: Path | None = None) -> set[tuple]:
    """복제 구간 인덱스 — 선행 프로젝트 산출물. `data/labels/README.md` 참조."""
    d = pd.read_csv(path or DUP_INDEX, encoding="utf-8-sig")
    d["d"] = pd.to_datetime(d["d"]).dt.date
    return set(zip(d["d"], d["idx"]))


def mark_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """`is_dup` 열을 붙인다. True 면 복제 구간(Tier C)에 속한 행."""
    key = load_dup_index()
    out = df.copy()
    out["is_dup"] = [(d, i) in key for d, i in zip(out["d"], out["idx"])]
    return out


def load_genuine(stable_only: bool = False, xlsx: Path | None = None) -> pd.DataFrame:
    """복제 구간을 제외한 실제 생산 데이터.

    2020-04-03 은 작업일 전체가 복제 구간이므로 여기서 완전히 사라진다.
    그 결과 평가 대상 이상일은 3일(03-25, 03-27, 03-31)이 되고,
    선행 프로젝트의 '탐지 3/3' 이 성립한다.
    """
    df = mark_duplicates(load_raw(xlsx))
    df = df[~df["is_dup"]]
    if stable_only:
        df = df[df["d"].astype(str).isin(STABLE_DAYS)]
    return df
