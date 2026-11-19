"""사진 판독기만 따로 잰다 — 기준 사진(③)이 날림/정상 판별을 돕는가.

Agent 없이 판독기만 본다. 요청 문구는 고정(Agent 의 요청을 흉내 내지 않는다):
  "Close-up of the finished spot weld on the coupon face."
날림 사진과 정상 사진에 '이상 있음'(fault_present 또는 differs_from_reference)이라고 답한 비율을 본다.
두 비율의 차이가 판별력이다. 개발용 4건(run_tier_e.DEV_CASES)은 따로 보고한다.

사용: .venv/bin/python scripts/95_reader_eval.py [--models haiku sonnet] [--dev-only]
→ eval/results/reader_eval.json
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agent.tools.photo import read_photo  # noqa: E402
from eval.run_tier_e import DEV_CASES  # noqa: E402
from eval.tier_e import load  # noqa: E402

OUT = ROOT / "eval" / "results" / "reader_eval.json"
REQ = "Close-up of the finished spot weld on the coupon face."


def flag(r: dict, with_ref: bool) -> bool:
    if with_ref and r.get("differs_from_reference") is True:
        return True
    return r.get("fault_present") is True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=["haiku", "sonnet"])
    ap.add_argument("--dev-only", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    cases = [c for c in load() if (c.case_id in DEV_CASES) == a.dev_only or not a.dev_only]
    jobs = [(c, m, ref) for c in cases for m in a.models for ref in (False, True)]

    def one(j):
        c, m, ref = j
        r = read_photo(c.photo, REQ, model=m, reference=c.reference_photo if ref else None)
        return {"case_id": c.case_id, "label": c.label, "dev": c.case_id in DEV_CASES, "model": m,
                "ref": ref, "flag": flag(r, ref), "fault_present": r.get("fault_present"),
                "differs": r.get("differs_from_reference"), "obs": str(r.get("observation", ""))[:200],
                "diff": str(r.get("reference_difference", ""))[:200]}

    with ThreadPoolExecutor(a.workers) as ex:
        rows = list(ex.map(one, jobs))

    summary = {}
    for dev in (True, False):
        for m in a.models:
            for ref in (False, True):
                rs = [r for r in rows if r["dev"] == dev and r["model"] == m and r["ref"] == ref]
                if not rs:
                    continue
                ex_ = [r["flag"] for r in rs if r["label"] == "Explode"]
                gd = [r["flag"] for r in rs if r["label"] == "Good"]
                k = f"{'dev' if dev else 'test'}|{m}|{'ref' if ref else 'noref'}"
                summary[k] = {"explode_flagged_pct": round(100 * sum(ex_) / len(ex_), 1),
                              "good_flagged_pct": round(100 * sum(gd) / len(gd), 1),
                              "gap_pp": round(100 * (sum(ex_) / len(ex_) - sum(gd) / len(gd)), 1),
                              "n": len(rs)}
                print(f"  {k:22s} 날림→이상 {summary[k]['explode_flagged_pct']:5.1f}%  "
                      f"정상→이상 {summary[k]['good_flagged_pct']:5.1f}%  차이 {summary[k]['gap_pp']:+.1f}%p  (n={len(rs)})")
    OUT.write_text(json.dumps({"request": REQ, "summary": summary, "rows": rows}, ensure_ascii=False, indent=1))
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
