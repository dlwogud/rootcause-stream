"""Tier E 참고선 — 사진 없이 공정 신호·설정값만으로 판정을 맞힐 수 있는가.

LLM 이 아니라 지도학습 분류기(랜덤포레스트)다. 판정 라벨을 학습에 쓰므로 Agent 보다
유리한 조건이다 — 그래도 날림을 못 잡으면 '센서로는 갈리지 않는다' 의 근거가 된다.

사용: .venv/bin/python scripts/92_tier_e_sensor_only.py → eval/results/tier_e_sensor_only.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold, cross_val_predict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eval.tier_e import SETPOINT, _welds, load_raw  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "eval" / "results" / "tier_e_sensor_only.json"


def main() -> None:
    w = _welds(load_raw())
    w = w[w["Comments"] != "Communication error"]
    X = w[SETPOINT + ["Thickness A (mm)", "Thickness B (mm)", "i_peak", "i_mean", "f_peak",
                      "n_samples"]].copy()
    X["i_std"] = w["current"].apply(lambda v: pd.Series(v).std())
    X["f_mean"] = w["force"].apply(lambda v: pd.Series(v).mean())
    y = w["Category"]
    labels = ["Good", "Explode", "Bad"]
    p = cross_val_predict(RandomForestClassifier(300, random_state=0, class_weight="balanced"),
                          X.fillna(0), y, cv=StratifiedKFold(5, shuffle=True, random_state=0))
    pr, rc, _, n = precision_recall_fscore_support(y, p, labels=labels, zero_division=0)
    out = {"model": "RandomForest(300, balanced) · 5-fold CV · 설정값+전류/가압력 요약",
           "n_welds": int(len(y)),
           "per_class": {l: {"precision": round(float(a) * 100, 1), "recall": round(float(b) * 100, 1),
                             "n": int(c)} for l, a, b, c in zip(labels, pr, rc, n)},
           "confusion_rows_true_cols_pred": {"labels": labels,
                                             "matrix": confusion_matrix(y, p, labels=labels).tolist()}}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    for l, v in out["per_class"].items():
        print(f"  {l:8s} 정밀도 {v['precision']:5.1f}%  재현율 {v['recall']:5.1f}%  (n={v['n']})")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
