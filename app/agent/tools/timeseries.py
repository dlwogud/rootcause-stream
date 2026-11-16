"""query_timeseries — 사건 구간의 공정 변수를 안정일 기준과 대조한다.

**원시 시계열을 반환하지 않는다.** 수천 개 숫자를 컨텍스트에 넣으면 토큰이 폭증하고
정확도도 떨어진다. 요약 통계 + 기준 대비 이동량 + 임계 초과 구간만 돌려준다.
(docs/07-api.md 의 설계 결정)
"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache

import numpy as np
import pandas as pd

from app.stream.detectors import F, I, T, V, load_genuine, load_raw, mark_duplicates
from app.stream.replay import add_pseudo_timestamps

VARS = {"force": F, "current": I, "voltage": V, "time": T}


@lru_cache(maxsize=1)
def _frames():
    df = add_pseudo_timestamps(mark_duplicates(load_raw()))
    stable = load_genuine(stable_only=True)
    return df, stable


@lru_cache(maxsize=16)
def _case_frame(ref: str):
    """합성 케이스의 주입된 공정 데이터. 없으면 원본을 쓴다."""
    from pathlib import Path
    p = Path(ref)
    if not p.is_absolute():
        from app.db import ROOT
        p = ROOT / ref
    d = pd.read_csv(p)
    d["ts"] = pd.to_datetime(d["ts"])
    if "is_dup" not in d.columns:
        d["is_dup"] = False
    return d


def query_timeseries(window_start: str, window_end: str,
                     variable: str = "all", data_ref: str | None = None, **_) -> dict:
    """data_ref 가 주어지면 그 프레임을 본다.

    주지 않으면 원본 전체를 타임스탬프로 조회한다. 합성 케이스에 data_ref 를
    빠뜨리면 **주입 전 데이터**를 보게 되어 평가가 무의미해진다.
    """
    full, stable = _frames()
    df = _case_frame(data_ref) if data_ref else full
    t0, t1 = datetime.fromisoformat(window_start), datetime.fromisoformat(window_end)
    w = df[(df["ts"] >= t0) & (df["ts"] <= t1)]
    if w.empty:
        return {"error": "해당 구간에 데이터가 없다", "window": [window_start, window_end]}

    names = list(VARS) if variable in ("all", "", None) else [variable]
    # ⚠️ `is_dup` 를 노출하지 않는다. 그것은 Tier C 의 **정답 라벨**이고,
    #    노출하면 Agent 가 추론 대신 답을 읽는다. 대신 아래 cross_day_repeat 처럼
    #    실제 운영 시스템도 데이터만으로 계산할 수 있는 신호를 준다.
    out: dict = {"window": [window_start, window_end], "n_points": int(len(w)),
                 "variables": {}}
    for name in names:
        col = VARS.get(name)
        if col is None:
            out["variables"][name] = {"error": f"알 수 없는 변수. 가능: {list(VARS)}"}
            continue
        x, b = w[col].to_numpy(), stable[col].to_numpy()
        bmed, bsd = float(np.median(b)), float(np.std(b, ddof=1))
        med = float(np.median(x))
        out["variables"][name] = {
            "unit": col,
            "window_median": round(med, 4),
            "window_sd": round(float(np.std(x, ddof=1)), 5),
            "stable_median": round(bmed, 4),
            "stable_sd": round(bsd, 5),
            "shift_in_sd": round((med - bmed) / bsd, 2) if bsd else None,
            "sd_ratio_vs_stable": round(float(np.std(x, ddof=1)) / bsd, 2) if bsd else None,
            "n_distinct_values": int(pd.unique(np.round(x, 6)).size),
            "trend": _trend(w["ts"].to_numpy(), x),
        }
    # 반복 적재 신호 — 라벨이 아니라 데이터에서 계산한다.
    #   within_window : 같은 구간 안에서 공정 기록이 반복되는 비율
    #   cross_day     : 이 구간의 기록이 **다른 작업일에도 그대로** 나타나는 비율.
    #                   설비가 같은 값을 우연히 반복할 수는 있어도, 작업일을 건너뛰어
    #                   동일한 수열이 재현되는 것은 수집 계통을 의심할 근거다.
    key = w[[F, I, V, T]].round(9).astype(str).agg("|".join, axis=1)
    out["repeat_signals"] = {
        "within_window_repeat_fraction": round(float(1 - key.nunique() / len(key)), 3),
        **_cross_day_run(full, w, key),   # 비교 대상은 항상 원본 전체
        "n_distinct_rows": int(key.nunique()),
    }
    return out


def _cross_day_run(full: pd.DataFrame, w: pd.DataFrame, key: pd.Series) -> dict:
    """이 구간의 기록이 **다른 작업일에 연속된 수열 그대로** 재현되는 최장 길이.

    개별 행이 다른 날에도 나타나는 것은 우연이다 — 공정 변수가 이산값이라
    4-튜플 일치는 흔하다. 그러나 **연속 수열**이 작업일을 건너뛰어 재현되는 것은
    설비가 만들 수 있는 현상이 아니다. 수집 계통을 의심할 근거다.
    (선행 프로젝트가 26.8% 복제 구간을 찾은 방법 — 행 해시 + 최장공통런)
    """
    days_here = set(w["d"].astype(str))
    other = full[~full["d"].astype(str).isin(days_here)]
    if other.empty or len(key) < 2:
        return {"longest_cross_day_run": 0, "cross_day_run_fraction": 0.0}

    seq = list(key)
    others = [list(g[[F, I, V, T]].round(9).astype(str).agg("|".join, axis=1))
              for _, g in other.groupby("d", sort=True)]

    def has_run(k: int) -> bool:
        if k > len(seq):
            return False
        grams = {tuple(seq[i:i + k]) for i in range(len(seq) - k + 1)}
        for o in others:
            if k > len(o):
                continue
            for i in range(len(o) - k + 1):
                if tuple(o[i:i + k]) in grams:
                    return True
        return False

    lo, hi, best = 1, min(len(seq), 400), 0
    while lo <= hi:                      # 이분 탐색
        mid = (lo + hi) // 2
        if has_run(mid):
            best, lo = mid, mid + 1
        else:
            hi = mid - 1
    return {"longest_cross_day_run": best,
            "cross_day_run_fraction": round(best / len(seq), 3)}


def _trend(ts, x) -> str:
    if len(x) < 6:
        return "too_short"
    h = len(x) // 2
    a, b = float(np.median(x[:h])), float(np.median(x[h:]))
    sd = float(np.std(x, ddof=1)) or 1e-9
    d = (b - a) / sd
    return "rising" if d > 0.5 else "falling" if d < -0.5 else "flat"
