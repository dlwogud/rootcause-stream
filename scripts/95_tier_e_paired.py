"""9장(같은 시험 58문제) 비교에 짝 검정을 붙인다 — "67% 대 57%, 우연 아니냐?" 에 답한다.

같은 58문제를 네 방법이 모두 풀었으므로, 문제마다 '이쪽만 맞힘 / 저쪽만 맞힘'을 세어
McNemar 정확 검정(eval/report_tier_e.mcnemar, 다른 짝 비교와 같은 함수)을 한다.

  사진 요청   run #84 photo_ref        (outputs/tier_e_results_back_sonnet_fix.json)
  사진 없이   sonnet · none            (outputs/tier_e_results_sonnet.json)
  숫자 규칙   최대 전류 > 같은 설정 p90  (scripts/94_rule_baseline.py R3 와 같은 식)
  학습 AI     랜덤포레스트 5-fold 교차검증 예측 (94 와 같은 설정 · random_state=0)

규칙·학습 AI 는 LLM 호출 없이 다시 계산하고, rule_baseline.json 의 정답률과 같은지 먼저 확인한다.

사용: .venv/bin/python scripts/95_tier_e_paired.py → eval/results/tier_e_paired.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.report_tier_e import mcnemar  # noqa: E402
from eval.run_tier_e import DEV_CASES  # noqa: E402
from eval.tier_e import load as load_e  # noqa: E402

OUT = ROOT / "eval" / "results" / "tier_e_paired.json"


def agent(name: str, cond: str) -> dict:
    d = json.loads((ROOT / "outputs" / name).read_text())
    dev = set(d["dev_cases"])
    return {r["case_id"]: r for r in d["records"] if r["cond"] == cond and r["case_id"] not in dev}


def main() -> int:
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from eval.tier_e import SETPOINT, _welds, load_raw

    ecs = [c for c in load_e() if c.case_id not in DEV_CASES]

    w = _welds(load_raw())
    w = w[w["Comments"] != "Communication error"]
    X = w[SETPOINT + ["Thickness A (mm)", "Thickness B (mm)", "i_peak", "i_mean", "f_peak", "n_samples"]].copy()
    X["i_std"] = w["current"].apply(lambda v: pd.Series(v).std())
    X["f_mean"] = w["force"].apply(lambda v: pd.Series(v).mean())
    rf = pd.Series(cross_val_predict(RandomForestClassifier(300, random_state=0, class_weight="balanced"),
                                     X.fillna(0), w["Category"],
                                     cv=StratifiedKFold(5, shuffle=True, random_state=0)), index=w.index)

    photo = agent("tier_e_results_back_sonnet_fix.json", "photo_ref")
    none = agent("tier_e_results_sonnet.json", "none")

    R: dict = {}
    for c in ecs:
        lg, pop = c.cooccurrence["logged_during_weld"], c.cooccurrence["same_setpoint_population"]
        rule_says = "Explode" if lg["peak_current_A"] > pop["peak_current_A"]["p90"] else "Good"
        R[c.case_id] = {
            "photo": photo[c.case_id], "none": none[c.case_id],
            "rule": {"label": c.label, "m1": int(rule_says == c.label)},
            "rf": {"label": c.label, "m1": int(rf.loc[c.sample_id] == c.label)},
        }

    acc = {k: round(100 * sum(v[k]["m1"] for v in R.values()) / len(R), 1) for k in ("photo", "none", "rule", "rf")}
    rb = json.loads((ROOT / "eval" / "results" / "rule_baseline.json").read_text())["tier_e"]
    assert acc["rule"] == rb["rule_peak_current_p90"]["accuracy"], (acc["rule"], rb)
    assert acc["rf"] == rb["supervised_rf_reference"]["accuracy"], (acc["rf"], rb)

    out = {"n": len(R), "accuracy": acc, "tests": {}}
    for other in ("rf", "rule", "none"):
        out["tests"][f"photo_vs_{other}"] = mcnemar(R, "photo", other)
        out["tests"][f"photo_vs_{other}_explode"] = mcnemar(R, "photo", other, "Explode")
        out["tests"][f"photo_vs_{other}_good"] = mcnemar(R, "photo", other, "Good")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
