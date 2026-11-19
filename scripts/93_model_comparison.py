"""모델 비교 — 진단 모델만 haiku → sonnet 으로 바꿨을 때.

공정성: 채점자는 둘 다 **opus** 다. sonnet 이 자기 답을 채점하지 않도록 기존 채점자(sonnet)를
쓰지 않고, haiku 의 저장된 결론 원문도 opus 로 다시 채점한다. 사진 판독은 두 경우 모두 haiku.

  Tier A : haiku run #31·#37·#43 (full) vs sonnet run #52·#53·#54 — 3건 × 3회
  Tier E : haiku run #50 vs sonnet run #51 — photo / none, 개발용 4건 제외 58건

사용: .venv/bin/python scripts/93_model_comparison.py → eval/results/model_comparison.json
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import connect  # noqa: E402
from eval.cases import load as load_cases  # noqa: E402
from eval.judge import judge  # noqa: E402
from eval.run_tier_e import DEV_CASES  # noqa: E402
from eval.tier_e import load as load_e  # noqa: E402

OUT = ROOT / "eval" / "results" / "model_comparison.json"
JUDGE = "opus"
A_RUNS = {"haiku": (31, 37, 43), "sonnet": (52, 53, 54)}


def pct(xs):
    return round(100 * sum(xs) / len(xs), 1) if xs else None


def mcnemar(pairs):
    a = sum(1 for x, y in pairs if x and not y)
    b = sum(1 for x, y in pairs if y and not x)
    n, k = a + b, min(a, b)
    return {"only_first": a, "only_second": b,
            "p_two_sided": round(min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n), 4) if n else 1.0}


def main() -> None:
    con = connect()
    truth_a = {c.case_id: c.truth for c in load_cases() if c.tier == "A"}
    jobs = []        # (model, tier, key, truth, answer)
    for m, runs in A_RUNS.items():
        for rid in runs:
            for r in con.execute("SELECT case_id, detail FROM eval_results WHERE run_id=? AND tier='A'"
                                 " GROUP BY case_id", (rid,)):
                d = json.loads(r["detail"] or "{}")
                jobs.append((m, "A", f"{r['case_id']}|{rid}", truth_a[r["case_id"]], d.get("_root_cause", "")))
    ecase = {c.case_id: c for c in load_e()}
    for m, f in (("haiku", "outputs/tier_e_results.json"), ("sonnet", "outputs/tier_e_results_sonnet.json")):
        for r in json.loads((ROOT / f).read_text())["records"]:
            if r["case_id"] in DEV_CASES or r["cond"] not in ("photo", "none"):
                continue
            jobs.append((m, f"E-{r['cond']}", r["case_id"], ecase[r["case_id"]].truth, r["root_cause"]))

    def grade(j):
        m, t, k, truth, ans = j
        return m, t, k, 1.0 if judge(truth, ans, model=JUDGE).get("match") else 0.0

    res: dict = {}
    with ThreadPoolExecutor(6) as ex:
        for m, t, k, v in ex.map(grade, jobs):
            res.setdefault(t, {}).setdefault(m, {})[k] = v

    out = {"judge": JUDGE, "vlm": "haiku", "tiers": {}}
    for t, by in sorted(res.items()):
        out["tiers"][t] = {m: {"pct": pct(list(v.values())), "n": len(v)} for m, v in by.items()}
        if t.startswith("E"):
            lab = {k: ecase[k].label for k in by["haiku"]}
            for m, v in by.items():
                out["tiers"][t][m]["explode_recall"] = pct([v[k] for k in v if lab[k] == "Explode"])
                out["tiers"][t][m]["good_recall"] = pct([v[k] for k in v if lab[k] == "Good"])
    # 사진 효과 (모델별, 짝비교) — 날림 사건
    for m in ("haiku", "sonnet"):
        ph, no = res["E-photo"][m], res["E-none"][m]
        ex = [k for k in ph if ecase[k].label == "Explode" and k in no]
        out[f"photo_vs_none_explode_{m}"] = mcnemar([(ph[k], no[k]) for k in ex])
        out[f"photo_vs_none_all_{m}"] = mcnemar([(ph[k], no[k]) for k in ph if k in no])
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
