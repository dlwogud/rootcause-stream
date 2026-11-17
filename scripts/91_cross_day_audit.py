"""기록 재활용 감사 — 작업일을 건너뛰어 '연속된 수열 그대로' 재현되는 기록을 센다.

선행 프로젝트(kamp-welding)는 800행짜리 복제 덩어리 하나(전체 26.8%)를 찾았다.
2026-11-17 시연 실행에서 Agent 가 Tier A(3/25) 기록의 절반이 다른 날과 같다고 지적했고,
이 스크립트로 확인한 결과 **복제를 제외한 기록도 대부분 재활용**이었다.

판정 기준: 한 행이 길이 L(기본 30) 이상의 연속 수열에 속하고, 그 수열이 **다른 작업일에도
연속·동일하게** 나타나면 '재활용'으로 본다. 4개 공정값(가압력·전류·전압·시간)의 튜플은
1,574종이고 최빈 튜플이 0.5% 이므로 우연 일치는 짧다 — 대조군(작업일 안에서 순서를
무작위로 섞음)으로 우연히 생기는 최장 길이를 함께 보고한다.

사용: .venv/bin/python scripts/91_cross_day_audit.py [--L 30]
→ eval/results/cross_day_audit.csv (작업일별), 콘솔 요약
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.stream.detectors import F, I, T, V, load_raw, mark_duplicates  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "eval" / "results" / "cross_day_audit.csv"


def keys(df: pd.DataFrame) -> np.ndarray:
    return df[[F, I, V, T]].round(9).astype(str).agg("|".join, axis=1).to_numpy()


def flag_shared(days: np.ndarray, k: np.ndarray, L: int) -> np.ndarray:
    """길이 L 의 연속 수열이 다른 작업일에도 있으면 그 L 행을 True 로."""
    grams: dict[tuple, set] = {}
    idx = {d: np.flatnonzero(days == d) for d in np.unique(days)}
    for d, ii in idx.items():
        ks = k[ii]
        for i in range(len(ks) - L + 1):
            grams.setdefault(tuple(ks[i:i + L]), set()).add(d)
    out = np.zeros(len(k), bool)
    for d, ii in idx.items():
        ks = k[ii]
        for i in range(len(ks) - L + 1):
            if len(grams[tuple(ks[i:i + L])]) > 1:
                out[ii[i:i + L]] = True
    return out


def longest_shared(days: np.ndarray, k: np.ndarray, cap: int = 400) -> int:
    lo, hi, best = 1, cap, 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if flag_shared(days, k, mid).any():
            best, lo = mid, mid + 1
        else:
            hi = mid - 1
    return best


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, default=30)
    a = ap.parse_args()

    df = mark_duplicates(load_raw()).reset_index(drop=True)
    days, k = df["d"].astype(str).to_numpy(), keys(df)
    df["reused"] = flag_shared(days, k, a.L)

    rng = np.random.default_rng(0)
    ks = k.copy()
    for d in np.unique(days):
        m = days == d
        ks[m] = rng.permutation(ks[m])
    chance = longest_shared(days, ks, cap=50)
    actual = longest_shared(days, k)

    g = df.groupby(df["d"].astype(str))
    s = pd.DataFrame({
        "rows": g.size(),
        "dup_index_frac": g["is_dup"].mean().round(3),
        "reused_frac": g["reused"].mean().round(3),
        "genuine_rows": df[~df.is_dup].groupby(df["d"].astype(str)).size(),
        "genuine_reused_frac": df[~df.is_dup].groupby(df["d"].astype(str))["reused"].mean().round(3),
    })
    clean = df[~df.is_dup & ~df.reused]
    s["clean_rows"] = clean.groupby(clean["d"].astype(str)).size()
    s = s.fillna({"genuine_rows": 0, "clean_rows": 0}).astype({"genuine_rows": int, "clean_rows": int})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    s.to_csv(OUT, encoding="utf-8")

    print(s.to_string())
    print(f"\n전체 {len(df):,}행 · 4-튜플 {pd.Series(k).nunique():,}종")
    print(f"선행 복제 라벨(800행 덩어리)      {df.is_dup.mean():.1%}")
    print(f"다른 작업일과 {a.L}행+ 연속 일치     {df.reused.mean():.1%}")
    print(f"둘 다 아닌 '깨끗한' 행             {len(clean):,}행 ({len(clean)/len(df):.1%})")
    print(f"다른 작업일과 공유되는 최장 연속   실제 {actual}행{' 이상(탐색 상한)' if actual >= 400 else ''}  vs  순서 섞은 대조 {chance}행")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
