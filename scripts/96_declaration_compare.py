#!/usr/bin/env python3
"""사전 선언 대조(app/agent/declaration.py) 전후 비교 — 같은 58건, 사건별로 짝지어.

  이전: run #73 (sonnet, photo_ref) · run #74 (haiku, photo_ref · swap_ref) — 장치 없음
  이후: --tag decl_sonnet · decl_haiku — 장치 켬. 나머지 조건(판독 haiku, 채점 opus)은 같다

주의: 같은 58건을 여러 설계 반복에 썼다. 이 비교는 '시험 문제를 이미 본' 상태의 측정이다.
또 LLM 출력은 매번 조금씩 다르므로 전후 차이에는 실행 간 변동이 섞인다.

사용: .venv/bin/python scripts/96_declaration_compare.py → eval/results/declaration_compare.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.report_tier_e import mcnemar  # noqa: E402

O = ROOT / "outputs"
OUT = ROOT / "eval" / "results" / "declaration_compare.json"
PAIRS = {"sonnet": ("tier_e_results_ref_sonnet.json", "tier_e_results_decl_sonnet.json"),
         "haiku": ("tier_e_results_ref_haiku.json", "tier_e_results_decl_haiku.json")}


def _load(name: str) -> tuple[dict, set]:
    d = json.loads((O / name).read_text())
    return {(r["case_id"], r["cond"]): r for r in d["records"]}, set(d["dev_cases"])


def _rate(rs, key="m1"):
    return round(100 * sum(bool(r[key]) for r in rs) / len(rs), 1) if rs else None


def _flagged(r) -> bool:
    rd = r.get("reading") or {}
    return rd.get("differs_from_reference") is True or rd.get("fault_present") is True


def main() -> int:
    out = {}
    for model, (before_f, after_f) in PAIRS.items():
        if not (O / after_f).exists():
            continue
        B, dev = _load(before_f)
        A, _ = _load(after_f)
        for cond in ("photo_ref", "swap_ref"):
            keys = sorted(k for k in A if k[1] == cond and k in B and k[0] not in dev)
            if not keys:
                continue
            R = {k[0]: {"before": B[k], "after": A[k]} for k in keys}
            row = {"n": len(keys)}
            for tag, src in (("before", B), ("after", A)):
                rs = [src[k] for k in keys]
                row[tag] = {"accuracy": _rate(rs),
                            "explode_recall": _rate([r for r in rs if r["label"] == "Explode"]),
                            "good_recall": _rate([r for r in rs if r["label"] == "Good"])}
            row["mcnemar_all"] = mcnemar(R, "after", "before")
            row["mcnemar_explode"] = mcnemar(R, "after", "before", "Explode")
            row["mcnemar_good"] = mcnemar(R, "after", "before", "Good")
            after = [A[k] for k in keys]
            ch = [r for r in after if r.get("challenged")]
            row["challenged"] = len(ch)
            row["challenged_correct"] = sum(int(r["m1"]) for r in ch)
            row["challenged_by_label"] = {lb: sum(r["label"] == lb for r in ch) for lb in ("Explode", "Good")}
            # 판독기가 '이상' 이라고 한 날림 사진 → Agent 가 날림으로 결론 낸 비율 (병목 지표)
            for tag, src in (("before", B), ("after", A)):
                fl = [src[k] for k in keys if src[k]["label"] == "Explode" and _flagged(src[k])]
                row[f"flagged_explode_{tag}"] = {"n": len(fl), "correct": sum(int(r["m1"]) for r in fl)}
            out[f"{model}|{cond}"] = row
            b, a = row["before"], row["after"]
            print(f"{model:6s} {cond:9s} n={len(keys)}  정확도 {b['accuracy']}→{a['accuracy']}  "
                  f"날림 {b['explode_recall']}→{a['explode_recall']}  정상 {b['good_recall']}→{a['good_recall']}  "
                  f"p={row['mcnemar_all']['p_two_sided']}  되물음 {len(ch)}건(맞힘 {row['challenged_correct']})  "
                  f"판독'이상' 날림 맞힘 {row['flagged_explode_before']['correct']}/{row['flagged_explode_before']['n']}"
                  f"→{row['flagged_explode_after']['correct']}/{row['flagged_explode_after']['n']}")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"→ {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
