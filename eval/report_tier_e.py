#!/usr/bin/env python3
"""Tier E 결과 분석 — 짝지은 비교(McNemar 정확검정)와 판독기 성능.

같은 사건을 세 조건으로 돌렸으므로 조건 간 비교는 **사건별로 짝지어** 한다.
개발용 사건(run_tier_e.DEV_CASES)은 제외한다.

사용: .venv/bin/python -m eval.report_tier_e → eval/results/tier_e_summary.json
"""
from __future__ import annotations

import json
from math import comb
from pathlib import Path

SRC = Path("outputs/tier_e_results.json")
OUT = Path("eval/results/tier_e_summary.json")


def mcnemar(R: dict, a: str, b: str, label: str | None = None) -> dict:
    """a 만 맞힌 사건 수, b 만 맞힌 사건 수, 양측 정확 p."""
    only_a = only_b = 0
    for x in R.values():
        if a not in x or b not in x or (label and x[a]["label"] != label):
            continue
        only_a += int(x[a]["m1"] and not x[b]["m1"])
        only_b += int(x[b]["m1"] and not x[a]["m1"])
    n, k = only_a + only_b, min(only_a, only_b)
    p = min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n) if n else 1.0
    return {"only_" + a: only_a, "only_" + b: only_b, "p_two_sided": round(p, 4)}


def main() -> int:
    d = json.loads(SRC.read_text())
    dev = set(d["dev_cases"])
    R: dict = {}
    for r in d["records"]:
        if r["case_id"] not in dev:
            R.setdefault(r["case_id"], {})[r["cond"]] = r

    tests = {
        "photo_vs_none": mcnemar(R, "photo", "none"),
        "photo_vs_none_explode": mcnemar(R, "photo", "none", "Explode"),
        "photo_vs_swap": mcnemar(R, "photo", "swap"),
    }
    # 판독기: 받은 사진이 실제로 날림인가 정상인가에 따라 '이상 있음' 이라고 한 비율
    reader = {"Explode": [0, 0], "Good": [0, 0]}      # [이상 있음, 판독 수]
    for x in R.values():
        for cond in ("photo", "swap"):
            r = x.get(cond)
            if not r or not r["reading"]:
                continue
            shown = r["label"] if cond == "photo" else ("Good" if r["label"] == "Explode" else "Explode")
            reader[shown][0] += int(r["reading"].get("fault_present") is True)
            reader[shown][1] += 1
    out = {"run_id": d["run_id"], "n_cases": len(R), "dev_cases_excluded": sorted(dev),
           "summary": d["summary"], "paired_tests": tests,
           "reader_fault_flag_pct": {k: {"pct": round(100 * a / b, 1) if b else None, "n": b}
                                     for k, (a, b) in reader.items()}}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    for r in d["summary"]:
        print(f"  {r['cond']:5s} 정확도 {r['accuracy']:5.1f}%  날림 {r['explode_recall']:5.1f}%  정상 {r['good_recall']:5.1f}%")
    for k, v in tests.items():
        print(f"  {k:24s} {v}")
    print(f"  판독기가 '이상 있음' 이라 한 비율: {out['reader_fault_flag_pct']}")
    print(f"→ {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
