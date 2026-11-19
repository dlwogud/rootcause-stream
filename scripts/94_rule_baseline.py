"""규칙 기반 비교선 — "그 신호면 규칙 한 줄로 되는 거 아니야?" 에 숫자로 답한다.

규칙은 **결과를 보기 전에** 아래처럼 정했다 (2026-11-19). 임계를 바꿔 가며 고르지 않는다.
대신 임계 민감도를 함께 보고한다.

KAMP 사건 (A·C·B) — Agent 가 query_timeseries 로 받는 것과 **같은 출력**만 쓴다.
  R1  cross_day_run_fraction ≥ 0.3  또는 within_window_repeat_fraction ≥ 0.9
        → "데이터 수집 계통 이상: 다른 작업일 기록이 연속 그대로 반복 적재됨"
  R2  아니면 |shift_in_sd| 가 가장 큰 변수의 설비 이상. 그 변수의 sd_ratio_vs_stable ≥ 2 이면 '산포 증가'
  채점: A·C 는 Agent 와 같은 LLM-as-Judge(M1), B 는 같은 주 변수 규칙(M2)

Tier E (실험실 용접) — 라벨 없이 쓸 수 있는 규칙
  R3  최대 전류가 같은 설정값 모집단의 p90 초과 → "날림", 아니면 "정상"
  참고: 판정 라벨로 학습한 랜덤포레스트(5-fold 교차검증 예측) — 규칙보다 유리한 조건

사용: .venv/bin/python scripts/94_rule_baseline.py [--judge opus]
→ eval/results/rule_baseline.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.tools.timeseries import query_timeseries  # noqa: E402
from eval.cases import load as load_cases  # noqa: E402
from eval.judge import judge  # noqa: E402
from eval.metrics.m2_variable import m2_primary_variable  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "eval" / "results" / "rule_baseline.json"
THETA = 0.3
NAMES = {"force": "가압력", "current": "전류", "voltage": "전압", "time": "통전 시간"}


def rule_kamp(case, theta: float = THETA) -> tuple[str, bool]:
    r = query_timeseries(case.window_start, case.window_end, "all", case.data_ref)
    rep = r.get("repeat_signals", {})
    if rep.get("cross_day_run_fraction", 0) >= theta or rep.get("within_window_repeat_fraction", 0) >= 0.9:
        return ("데이터 수집 계통 이상이다. 이 구간의 공정 기록이 다른 작업일 기록과 연속 그대로 "
                "일치하거나 같은 값이 반복 기록되어, 설비가 아니라 기록이 반복 적재된 것이다."), True
    vs = {k: v for k, v in r["variables"].items() if isinstance(v, dict) and v.get("shift_in_sd") is not None}
    var = max(vs, key=lambda k: abs(vs[k]["shift_in_sd"]))
    v = vs[var]
    if (v.get("sd_ratio_vs_stable") or 0) >= 2:
        return f"설비 이상이다. {NAMES[var]}({var})의 산포(variance)가 평소의 {v['sd_ratio_vs_stable']}배로 증가했다.", False
    d = "높아" if v["shift_in_sd"] > 0 else "낮아"
    return f"설비 이상이다. {NAMES[var]}({var})이 평소보다 {abs(v['shift_in_sd'])} 표준편차 {d}졌다.", False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", default="opus")
    a = ap.parse_args()
    out: dict = {"theta": THETA, "judge": a.judge, "kamp": {}, "sensitivity": {}, "tier_e": {}}

    cases = [c for c in load_cases() if c.tier in "ACB"]
    rows = []
    for c in cases:
        text, data = rule_kamp(c)
        rec = {"case_id": c.case_id, "tier": c.tier, "rule_says_data_issue": data, "text": text}
        if c.tier in "AC":
            v = judge(c.truth, text, model=a.judge)
            rec["M1_match"] = 1.0 if v.get("match") else 0.0
            rec["judge_reason"] = v.get("reason", "")
        else:
            rec["M2_primary_variable"] = m2_primary_variable(c, {"root_cause": text})["M2_primary_variable"]
        rows.append(rec)
        print(f"  {c.tier} {c.case_id:24s} {rec.get('M1_match', rec.get('M2_primary_variable'))}  {text[:60]}")
    for t, m in (("A", "M1_match"), ("C", "M1_match"), ("B", "M2_primary_variable")):
        xs = [r[m] for r in rows if r["tier"] == t]
        out["kamp"][t] = {"metric": m, "pct": round(100 * sum(xs) / len(xs), 1), "n": len(xs)}
    out["kamp_cases"] = rows

    # 임계 민감도 — '데이터 이상' 판정이 맞는 비율 (A·C 는 데이터 이상, B 는 아님)
    for th in (0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9):
        ok = {"A": 0, "C": 0, "B": 0}
        for c in cases:
            _, data = rule_kamp(c, th)
            ok[c.tier] += int(data == (c.tier in "AC"))
        out["sensitivity"][str(th)] = {t: f"{ok[t]}/{sum(1 for c in cases if c.tier == t)}" for t in ok}

    # Tier E
    from eval.run_tier_e import DEV_CASES
    from eval.tier_e import load as load_e
    ecs = [c for c in load_e() if c.case_id not in DEV_CASES]
    hit = {"Explode": [0, 0], "Good": [0, 0]}
    for c in ecs:
        lg, pop = c.cooccurrence["logged_during_weld"], c.cooccurrence["same_setpoint_population"]
        says = lg["peak_current_A"] > pop["peak_current_A"]["p90"]
        hit[c.label][0] += int(says == (c.label == "Explode"))
        hit[c.label][1] += 1
    acc = (hit["Explode"][0] + hit["Good"][0]) / len(ecs)
    out["tier_e"]["rule_peak_current_p90"] = {
        "accuracy": round(100 * acc, 1),
        "explode_recall": round(100 * hit["Explode"][0] / hit["Explode"][1], 1),
        "good_recall": round(100 * hit["Good"][0] / hit["Good"][1], 1), "n": len(ecs)}

    # 참고: 지도학습 (라벨 사용) — 같은 58건에 대한 교차검증 예측
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from eval.tier_e import SETPOINT, _welds, load_raw
    w = _welds(load_raw())
    w = w[w["Comments"] != "Communication error"]
    X = w[SETPOINT + ["Thickness A (mm)", "Thickness B (mm)", "i_peak", "i_mean", "f_peak", "n_samples"]].copy()
    X["i_std"] = w["current"].apply(lambda v: pd.Series(v).std())
    X["f_mean"] = w["force"].apply(lambda v: pd.Series(v).mean())
    pred = pd.Series(cross_val_predict(RandomForestClassifier(300, random_state=0, class_weight="balanced"),
                                       X.fillna(0), w["Category"],
                                       cv=StratifiedKFold(5, shuffle=True, random_state=0)), index=w.index)
    sub = [(c.label, pred.loc[c.sample_id]) for c in ecs]
    ex = [p == "Explode" for l, p in sub if l == "Explode"]
    gd = [p == "Good" for l, p in sub if l == "Good"]
    out["tier_e"]["supervised_rf_reference"] = {
        "accuracy": round(100 * (sum(ex) + sum(gd)) / len(sub), 1),
        "explode_recall": round(100 * sum(ex) / len(ex), 1), "good_recall": round(100 * sum(gd) / len(gd), 1),
        "note": "판정 라벨 수백 개로 학습 — Agent·규칙은 라벨을 쓰지 않는다"}

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("\nKAMP:", out["kamp"])
    print("임계 민감도:", out["sensitivity"])
    print("Tier E:", out["tier_e"])
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
