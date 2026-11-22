#!/usr/bin/env python3
"""발표자료에 들어갈 수치를 평가 DB 에서 뽑는다 → deck/numbers.json (파일명이 numbers.py 면 표준 모듈 numbers 를 가린다)

**슬라이드에 숫자를 손으로 적지 않는다.** 덱 생성기(build.js)는 이 JSON 만 읽는다.
같은 조건을 여러 번 돌렸으면 실행별 평균의 평균과 최소·최대를 낸다 — LLM 은
비결정적이라 단일 실행 수치는 믿을 수 없다(같은 베이스라인이 28.6% / 57.1% 로 갈린 적이 있다).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db import connect  # noqa: E402

ALIAS = {"agent(full)": "full", "baseline(알람요약만)": "baseline"}
PRIMARY = {"A": "M1_match", "B": "M2_primary_variable", "C": "M1_match"}   # A: 2026-11-17 정답 정정 후 M1
EXTRA = {"A": ["M1_partial"], "B": ["M1_partial"], "C": ["M1_partial"]}
SKIP = {"tier_d", "tier_e"}   # 별도 실행기 — 아래에서 따로 읽는다
# 이 run 이전의 결과는 세지 않는다.
#   A: 2026-11-17 정답 정정(docs/14) — 그 전은 옛 정답 기준
#   B·C: 2026-11-19 사건 요약의 정답 라벨(dup_fraction) 누출 제거 — 그 전은 누출 상태
FROM_RUN = {"A": 30, "B": 56, "C": 56}   # 55 는 중단된 실행


def _cond(rs: list, cond: str) -> dict:
    x = [r for r in rs if r["cond"] == cond]
    ex = [r for r in x if r["label"] == "Explode"]
    gd = [r for r in x if r["label"] == "Good"]
    pct = lambda v: round(100 * sum(r["m1"] for r in v) / len(v), 1) if v else None
    return {"n": len(x), "accuracy": pct(x), "explode_recall": pct(ex), "good_recall": pct(gd),
            "explode_hit": int(sum(r["m1"] for r in ex)), "explode_n": len(ex),
            "good_hit": int(sum(r["m1"] for r in gd)), "good_n": len(gd)}


def tier_e_final() -> dict:
    """Tier E 최종 설계(run #84: sonnet · 정상 샘플 · 선언 대조 · 뒷면 요청 가능)와 비교 대상.
    2026-11-22 버그 수정(새 증거 중 마지막 것만 보이던 문제) 뒤의 측정만 '최종'으로 쓴다."""
    from eval.report_tier_e import mcnemar
    root = Path(__file__).resolve().parents[1]
    def load(name):
        f = root / "outputs" / name
        if not f.exists():
            return None, set()
        d = json.loads(f.read_text())
        return [r for r in d["records"] if r["case_id"] not in set(d["dev_cases"])], set(d["dev_cases"])
    fin, _ = load("tier_e_results_back_sonnet_fix.json")
    front, _ = load("tier_e_results_decl_sonnet.json")
    if not fin:
        return {}
    out = {"run": 84, "photo": _cond(fin, "photo_ref"), "swap": _cond(fin, "swap_ref")}
    R: dict = {}
    for r in fin:
        R.setdefault(r["case_id"], {})[r["cond"]] = r
    both = {k: v for k, v in R.items() if "photo_ref" in v and "swap_ref" in v}
    out["photo_vs_swap"] = mcnemar(both, "photo_ref", "swap_ref")
    out["photo_vs_swap_explode"] = mcnemar(both, "photo_ref", "swap_ref", "Explode")
    P = [v["photo_ref"] for v in R.values() if "photo_ref" in v]
    out["asked_back"] = [sum("B" in r.get("given_sides", []) for r in P), len(P)]
    fl = lambda x: x.get("differs_from_reference") is True or x.get("fault_present") is True
    ex = [r for r in P if r["label"] == "Explode"]
    seen = [r for r in ex if any(fl(x) for x in r.get("readings", []))]
    out["explode_funnel"] = {"total": len(ex), "reader_flagged": len(seen),
                             "flagged_and_concluded": int(sum(r["m1"] for r in seen)),
                             "reader_saw_nothing": len(ex) - len(seen)}
    if front:
        out["front_only"] = {"run": 76, **_cond(front, "photo_ref")}
        F = {r["case_id"]: r for r in front if r["cond"] == "photo_ref"}
        pair = {k: {"final": v["photo_ref"], "front": F[k]} for k, v in R.items()
                if "photo_ref" in v and k in F}
        out["final_vs_front"] = mcnemar(pair, "final", "front")
    return out


def main() -> int:
    con = connect()
    # 현재 케이스 집합에 있는 결과만 센다. Tier C 를 1건 → 8건으로 바꿨으므로
    # 옛 사건 id(C-2020-04-03) 결과가 평균에 섞이면 안 된다.
    from eval.cases import load as load_cases
    current = {c.case_id for c in load_cases()}
    runs = con.execute("SELECT id, config, git_sha FROM eval_runs ORDER BY id").fetchall()
    # label → tier → metric → [run 평균, ...]
    agg: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    ncase: dict = defaultdict(lambda: defaultdict(int))
    run_ids: dict = defaultdict(list)
    for r in runs:
        cfg = json.loads(r["config"])
        label = ALIAS.get(cfg.get("label"), cfg.get("label"))
        if label in SKIP or str(label).startswith("tier_e"):
            continue
        run_ids[label].append(r["id"])
        qs = ",".join("?" * len(current))
        rows = con.execute("SELECT tier, metric, AVG(value) v, COUNT(*) n FROM eval_results"
                           f" WHERE run_id=? AND case_id IN ({qs}) GROUP BY tier, metric",
                           (r["id"], *current)).fetchall()
        for x in rows:
            if r["id"] < FROM_RUN.get(x["tier"], 0):
                continue
            agg[label][x["tier"]][x["metric"]].append(x["v"])
            ncase[label][x["tier"]] = max(ncase[label][x["tier"]], x["n"])

    out = {"conditions": {}, "runs": dict(run_ids)}
    from collections import Counter as _C
    out["case_counts"] = dict(_C(c.tier for c in load_cases()))
    for label, tiers in agg.items():
        out["conditions"][label] = {}
        for t, metrics in tiers.items():
            d = {}
            for m in [PRIMARY.get(t)] + EXTRA.get(t, []):
                vs = metrics.get(m)
                if vs:
                    d[m] = {"mean": round(sum(vs) / len(vs) * 100, 1),
                            "min": round(min(vs) * 100, 1), "max": round(max(vs) * 100, 1),
                            "n_runs": len(vs)}
            d["n_cases"] = ncase[label][t]
            out["conditions"][label][t] = d

    # Tier D (음성 결과)
    td = Path(__file__).resolve().parents[1] / "outputs" / "tier_d_results.json"
    if td.exists():
        rs = json.loads(td.read_text())
        out["tier_d"] = {c: {"n": len([x for x in rs if x["cond"] == c]),
                             "m1": round(100 * sum(x["m1"] for x in rs if x["cond"] == c)
                                         / max(1, len([x for x in rs if x["cond"] == c])), 1)}
                         for c in ("agent_photo", "random_photo", "no_photo")}

    # 설계 검증
    vd = Path(__file__).resolve().parents[1] / "outputs" / "verify_design.json"
    if vd.exists():
        v = json.loads(vd.read_text())
        out["verify"] = {"pass": sum(1 for x in v if x["pass"]), "total": len(v)}

    # ── 사실 수치 — 계산 가능한 것은 계산하고, 1회 실측값은 출처를 적는다 ──
    from app.stream.detectors import (chart_summary, day_control_chart, load_genuine,
                                      load_raw, mark_duplicates)
    raw = mark_duplicates(load_raw())
    chart = chart_summary(day_control_chart(load_genuine()))
    pages = con.execute("SELECT COUNT(*) FROM manual_pages").fetchone()[0]
    diagrams = con.execute("SELECT COUNT(*) FROM manual_pages WHERE page_kind='diagram'").fetchone()[0]
    described = con.execute("SELECT COUNT(*) FROM manual_chunks WHERE source='vlm_description'").fetchone()[0]
    out["facts"] = {
        "weld_points": int(len(raw)), "workdays": int(raw["d"].nunique()),
        "dup_ratio_pct": round(float(raw["is_dup"].mean()) * 100, 1),
        "chart_detect": f"{chart['detected']}/{chart['n_variable']}",
        "chart_false_alarm": f"{chart['false_alarms']}/{chart['n_stable']}",
        "permutation_p": 0.0179,                    # 선행 프로젝트 t59 (kamp-welding)
        "manual_docs": 5, "manual_pages": pages, "diagram_pages": diagrams,
        "diagrams_described": described,
        "resume_tokens": [4893, 155],               # 2026-11-17 실측 (docs/99 결정 로그)
        "resume_latency_s": [3.6, 1.0],
        "step_time": ["~7분", "~40초"],
        "spike_calls": 168,                         # spike/RESULTS.md
        "spike_fault_binary_pct": 91.7, "spike_gauge_binary_pct": 50.0,
        "spike_choices_low": "83~100", "spike_choices_high": "42",
        "_source": "계산값은 데이터·DB 에서 산출. 상수는 주석의 출처 참조",
    }
    # 사건 유형 2종의 근거 — 복제 제외 시 이상일에는 폭주가 없다
    from app.stream.detectors import F
    from app.stream.replay import add_pseudo_timestamps, to_events
    from app.stream.windows import StreamDetectors, run_stream
    det = StreamDetectors().fit()
    anom = ["2020-03-25", "2020-03-27", "2020-03-31"]
    g = add_pseudo_timestamps(load_genuine())
    al_g, burst_g = run_stream(to_events(g), det=det)
    al_f, _ = run_stream(to_events(add_pseudo_timestamps(raw)), det=det)
    gen = load_genuine()
    v25 = next(v for v in day_control_chart(gen) if v.day == "2020-03-25")
    out["facts"]["a25_force_drop_bar"] = round(v25.center - v25.value, 3)
    out["facts"].update({
        "anom_alarms_genuine": [sum(1 for a in al_g if a.ts.date().isoformat() == d) for d in anom],
        "anom_bursts_genuine": sum(1 for i in burst_g if i.opened_at.date().isoformat() in anom),
        "dup_day_alarms": sum(1 for a in al_f if a.ts.date().isoformat() == "2020-04-03"),
        "over3bar_raw_pct": [round(float((raw[raw["d"].astype(str) == d][F] > 3).mean()) * 100, 1)
                             for d in anom],
        "over3bar_genuine_pct": [round(float((gen[gen["d"].astype(str) == d][F] > 3).mean()) * 100, 1)
                                 for d in anom],
    })
    # Tier E — 실제 용접 · 실제 사진 (eval/RESULTS_TIER_E.md)
    te = Path(__file__).resolve().parents[1] / "eval" / "results" / "tier_e_summary.json"
    if te.exists():
        out["tier_e"] = json.loads(te.read_text())
    for key, fn in (("rule_baseline", "rule_baseline.json"), ("model_comparison", "model_comparison.json")):
        f = Path(__file__).resolve().parents[1] / "eval" / "results" / fn
        if f.exists():
            out[key] = json.loads(f.read_text())
    so = Path(__file__).resolve().parents[1] / "eval" / "results" / "tier_e_sensor_only.json"
    if so.exists():
        out["tier_e_sensor_only"] = json.loads(so.read_text())
    out["tier_e_final"] = tier_e_final()
    # 데이터셋 분류별 인장강도 · 너깃 지름 — '정답은 어떻게 정했나' 질문용 (분류 기준은 데이터셋에 없다)
    src = Path(__file__).resolve().parents[1] / "data" / "external" / "rsw_insights" / "Data_RSW.csv"
    if src.exists():
        import pandas as pd
        g = pd.read_csv(src, encoding="utf-8-sig").groupby("Sample ID").first()
        out["rsw_classes"] = {c: {"n": int((g.Category == c).sum()),
                                  "pull_mean": round(float(g[g.Category == c]["PullTest (N)"].mean())),
                                  "nugget_mean": round(float(g[g.Category == c]["NuggetDiameter (mm)"].mean()), 1)}
                              for c in ("Good", "Explode", "Bad")}
    # 기록 재활용 감사 (docs/14) — scripts/91_cross_day_audit.py 의 산출물
    au = Path(__file__).resolve().parents[1] / "eval" / "results" / "cross_day_audit_summary.json"
    if au.exists():
        out["facts"]["audit"] = json.loads(au.read_text())
    import subprocess
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"],
                       capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1])
    out["facts"]["tests"] = sum(1 for ln in r.stdout.splitlines() if "::" in ln)
    p = Path(__file__).with_name("numbers.json")
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for label in ["baseline", "full", "no_photo", "no_signal_guide", "no_tools", "no_diagram"]:
        c = out["conditions"].get(label, {})
        cells = []
        for t in "ACB":
            m = c.get(t, {}).get(PRIMARY[t])
            cells.append(f"{t}:{m['mean']:5.1f}%(r{m['n_runs']})" if m else f"{t}:   –   ")
        print(f"  {label:16s} " + "  ".join(cells))
    print(f"→ {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
