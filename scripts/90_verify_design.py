#!/usr/bin/env python3
"""설계 의도 전수 검증 — 각 항목이 **의도한 대로** 동작하는지 실제 데이터로 확인한다.

단위 테스트(tests/)가 '코드가 깨지지 않았는가' 를 보는 반면, 여기서는
'설계 주장이 데이터에서 성립하는가' 를 본다. 보고서와 발표자료가 인용할 수치가
전부 여기서 재생산되므로, 하나라도 실패하면 비영 종료한다.

선행 프로젝트(kamp-welding)가 산출물 진위 검사를 파이프라인 종료 조건으로 걸었던
방식을 따른다.

사용: python3 scripts/90_verify_design.py [--skip-llm]
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

RESULTS: list[tuple[str, str, bool, str]] = []   # (구역, 항목, 통과, 비고)


def check(section: str, name: str, fn):
    try:
        ok, note = fn()
    except Exception as e:
        ok, note = False, f"{type(e).__name__}: {e}"
        if "-v" in sys.argv:
            traceback.print_exc()
    RESULTS.append((section, name, bool(ok), str(note)))
    mark = "✅" if ok else "❌"
    print(f"  {mark} {name:52s} {note}")


# ══════════════════════════════════════════════════════════════════
def verify_data():
    print("\n[1] 원본 데이터와 라벨")
    from app.stream.detectors import load_raw, load_genuine, mark_duplicates

    raw = load_raw()
    check("데이터", "용접점 11,939개 · 작업일 9일",
          lambda: (len(raw) == 11939 and raw["d"].nunique() == 9,
                   f"{len(raw):,}행 / {raw['d'].nunique()}일"))
    m = mark_duplicates(raw)
    r = m["is_dup"].mean()
    check("데이터", "복제 비율 26.8% (선행 프로젝트 보고값)",
          lambda: (abs(r - 0.268) < 0.002, f"{r:.3%}"))
    apr3 = m[m["d"].astype(str) == "2020-04-03"]
    check("데이터", "2020-04-03 은 작업일 전체가 복제",
          lambda: (len(apr3) > 0 and bool(apr3["is_dup"].all()),
                   f"{apr3['is_dup'].sum()}/{len(apr3)}"))
    g = load_genuine()
    days = sorted(str(x) for x in g["d"].unique())
    check("데이터", "복제 제외 후 8일, 04-03 소멸, 이상일 3일",
          lambda: ("2020-04-03" not in days and len(days) == 8,
                   f"{len(days)}일 {days[:3]}…"))
    return g


def verify_detectors(g):
    print("\n[2] 탐지기 — 선행 프로젝트 수치 재현")
    from app.stream.detectors import F, I, chart_summary, day_control_chart

    for lim, exp in [(2.0, (3, 0)), (2.5, (3, 0)), (3.0, (0, 0))]:
        s = chart_summary(day_control_chart(g, col=F, stat="median", limit=lim))
        check("탐지기", f"가압력 중앙값 {lim}σ → 탐지 {exp[0]}/3 · 오경보 {exp[1]}/5",
              lambda s=s, exp=exp: ((s["detected"], s["false_alarms"]) == exp
                                    and (s["n_variable"], s["n_stable"]) == (3, 5),
                                    f"{s['detected']}/{s['n_variable']} · {s['false_alarms']}/{s['n_stable']}"))
    s = chart_summary(day_control_chart(g, col=I, stat="median", limit=2.0))
    check("탐지기", "전류 중앙값 2σ → 0/3 (가압력만 신호를 가진다)",
          lambda: (s["detected"] == 0, f"{s['detected']}/{s['n_variable']}"))
    s2 = chart_summary(day_control_chart(g, col=F, stat="mean", limit=2.0))
    check("탐지기", "가압력 평균 2σ → 2/3 (중앙값이 더 민감)",
          lambda: ((s2["detected"], s2["false_alarms"]) == (2, 0),
                   f"{s2['detected']}/{s2['n_variable']}"))


def verify_stream(g):
    print("\n[3] 스트림 — 리플레이 · 사건 유형 2종")
    from app.stream.detectors import STABLE_DAYS
    from app.stream.replay import add_pseudo_timestamps, load_stream, to_events
    from app.stream.windows import (BURST, LEVEL_SHIFT, StreamDetectors,
                                    detect_level_shifts, run_stream)

    ev = load_stream()
    check("스트림", "이벤트 11,939개 · 타임스탬프 단조증가",
          lambda: (len(ev) == 11939 and [e.ts for e in ev] == sorted(e.ts for e in ev),
                   f"{len(ev):,}개"))
    check("스트림", "의사 타임스탬프가 작업일·교대(08~16시) 안",
          lambda: (all(e.ts.date().isoformat() == e.workday and 8 <= e.ts.hour < 16
                       for e in ev), "전부 준수"))
    check("스트림", "복제 구간은 제거하지 않고 표시만 (3,200건)",
          lambda: (sum(e.is_dup for e in ev) == 3200, f"{sum(e.is_dup for e in ev)}건"))

    det = StreamDetectors().fit()
    gt = add_pseudo_timestamps(g)
    al_g, burst_g = run_stream(to_events(gt), det=det)
    shifts = detect_level_shifts(gt, al_g)
    anom = {"2020-03-25", "2020-03-27", "2020-03-31"}
    check("스트림", "수준이동 사건 = 이상일 3건과 정확히 일치",
          lambda: ({i.workday for i in shifts} == anom,
                   f"{sorted(i.workday for i in shifts)}"))
    check("스트림", "복제 제외 시 이상일에 버스트 없음 (설계 변경의 근거)",
          lambda: (not any(i.workday in anom for i in burst_g),
                   f"이상일 버스트 {sum(1 for i in burst_g if i.workday in anom)}건"))

    al_f, burst_f = run_stream(ev, det=det)
    per = {}
    for i in burst_f:
        per[i.workday] = per.get(i.workday, 0) + 1
    check("스트림", "전체 데이터에서는 복제일이 버스트 최다 (Tier C)",
          lambda: (per.get("2020-04-03", 0) == max(per.values()),
                   f"04-03 {per.get('2020-04-03')}건 / 최대 {max(per.values())}건"))

    # 상태 격리 회귀
    d1 = add_pseudo_timestamps(g[g["d"].astype(str) == STABLE_DAYS[0]])
    d2 = add_pseudo_timestamps(g[g["d"].astype(str) == STABLE_DAYS[-1]])
    solo, _ = run_stream(to_events(d2), det=StreamDetectors().fit())
    det2 = StreamDetectors().fit()
    run_stream(to_events(d1), det=det2)
    after, _ = run_stream(to_events(d2), det=det2)
    check("스트림", "탐지기 상태 격리 (이전 실행이 다음에 섞이지 않음)",
          lambda: (len(solo) == len(after), f"단독 {len(solo)} vs 연속 {len(after)}"))


def verify_cases():
    print("\n[4] 평가 케이스 — Tier 와 사건 유형")
    from eval.cases import load
    from app.agent.tools import query_timeseries
    from app.agent.tools.timeseries import _case_frame
    _case_frame.cache_clear()

    cs = load()
    byt = {}
    for c in cs:
        byt.setdefault(c.tier, []).append(c)
    check("케이스", "Tier A 3 · B 7 · C 8 = 18건",
          lambda: ({t: len(v) for t, v in byt.items()} == {"A": 3, "B": 7, "C": 8},
                   {t: len(v) for t, v in sorted(byt.items())}))
    check("케이스", "Tier C 는 4개 작업일에 2구간씩 (한 날에 몰리지 않음)",
          lambda: (len({c.workday for c in byt["C"]}) == 4, sorted({c.workday for c in byt["C"]})))
    check("케이스", "Tier A 는 level_shift, B·C 는 burst",
          lambda: (all(c.kind == "level_shift" for c in byt["A"])
                   and all(c.kind == "burst" for c in byt["B"] + byt["C"]), "유형 일치"))
    check("케이스", "모든 케이스에 data_ref (합성이 원본을 조회하지 않도록)",
          lambda: (all(c.data_ref for c in cs),
                   f"{sum(1 for c in cs if c.data_ref)}/{len(cs)}"))
    check("케이스", "Tier C 라벨은 전적으로 외부(선행 프로젝트) 출처",
          lambda: (all("kamp-welding" in c.source for c in byt["C"]), "외부 출처"))
    check("케이스", "Tier A 라벨은 '차이의 존재'(외부) + '원인 특정 불가'(본 프로젝트 분석)",
          lambda: (all("선행 프로젝트" in c.source and "본 프로젝트" in c.source
                       for c in byt["A"]), "출처 이원 표기"))
    check("케이스", "Tier A 정답은 특정 원인이 아니라 '추가 관측 필요'",
          lambda: (all("구별되지 않" in c.truth and "추가 관측" in c.truth
                       for c in byt["A"]), "보류형 정답"))
    check("케이스", "Tier B 는 합성임이 출처에 명시",
          lambda: (all("합성" in c.source for c in byt["B"]), "명시됨"))

    # 정답 누출
    r = query_timeseries(cs[0].window_start, cs[0].window_end, "all", data_ref=cs[0].data_ref)
    blob = json.dumps(r, ensure_ascii=False)
    check("케이스", "도구 출력에 정답 라벨(is_dup/duplicate_fraction) 미노출",
          lambda: ("duplicate_fraction" not in blob and "is_dup" not in blob, "누출 없음"))

    # 판별력
    runs = {}
    for c in cs:
        q = query_timeseries(c.window_start, c.window_end, "all", data_ref=c.data_ref)
        runs[c.case_id] = q["repeat_signals"]["cross_day_run_fraction"]
    cfrac = min(runs[c.case_id] for c in byt["C"])
    afrac = max(runs[c.case_id] for c in byt["A"])
    bfrac = max(runs[c.case_id] for c in byt["B"])
    check("케이스", "최장공통런이 C > A > B 를 가른다",
          lambda: (cfrac > afrac > bfrac, f"C≥{cfrac} A≤{afrac} B≤{bfrac}"))

    # Tier B 주입 변수가 실제로 움직였는가
    VAR = {"A1_결합이탈": "current", "A2_가압이탈": "force",
           "A4_통전단축": "current", "A5_동시드리프트": "force"}
    bad = []
    for c in byt["B"]:
        v = VAR.get(c.injected)
        if not v:
            continue
        q = query_timeseries(c.window_start, c.window_end, v, data_ref=c.data_ref)
        sh = q["variables"][v]["shift_in_sd"]
        if sh is None or abs(sh) < 0.5:
            bad.append((c.injected, sh))
    check("케이스", "Tier B 주입 변수가 데이터에서 실제로 이동",
          lambda: (not bad, f"미달 {bad}" if bad else "전부 0.5σ 이상"))


def verify_retrieval():
    print("\n[5] 매뉴얼 색인과 검색")
    from app.db import DB_PATH, ROOT, connect
    from app.retrieval.hybrid import MODES, search

    if not DB_PATH.exists():
        check("검색", "색인 DB 존재", lambda: (False, "없음 — 01_index_manuals.py 실행 필요"))
        return
    con = connect()
    n = con.execute("SELECT COUNT(*) FROM manual_pages").fetchone()[0]
    check("검색", "매뉴얼 5종 415페이지 색인",
          lambda: (n == 415, f"{n}p"))
    d = con.execute("SELECT COUNT(*) FROM manual_pages WHERE page_kind='diagram'").fetchone()[0]
    check("검색", "도면 페이지 렌더 (≥50장)", lambda: (d >= 50, f"{d}장"))
    miss = [r["image_path"] for r in con.execute(
        "SELECT image_path FROM manual_pages WHERE page_kind='diagram'").fetchall()
        if not (ROOT / r["image_path"]).exists()]
    check("검색", "렌더된 PNG 가 실제로 존재", lambda: (not miss, f"누락 {len(miss)}장"))
    sp = con.execute("SELECT COUNT(*) FROM manual_chunks WHERE content LIKE '%0.5 MPa%'").fetchone()[0]
    check("검색", "공압 기준값 0.5 MPa 색인 (작업자 질문의 근거)",
          lambda: (sp >= 1, f"{sp}개 청크"))
    dt = con.execute("SELECT COUNT(*) FROM manual_chunks c JOIN manual_pages p"
                     " ON p.id=c.page_id WHERE p.page_kind='diagram'").fetchone()[0]
    check("검색", "도면 페이지의 텍스트도 색인 (배타 분류 아님)",
          lambda: (dt > 0, f"{dt}개 청크"))
    vd = con.execute("SELECT COUNT(*) FROM manual_chunks WHERE source='vlm_description'").fetchone()[0]
    check("검색", "도면 VLM 서술 색인 (Multimodal RAG)", lambda: (vd >= 20, f"{vd}장"))

    for m in MODES:
        h = search("electrode tip maintenance", top_k=3, mode=m)
        check("검색", f"mode={m} 동작", lambda h=h: (len(h) > 0, f"{len(h)}건"))
    bm = search("air pressure gauge setting for the cylinder", top_k=3, mode="bm25")
    check("검색", "BM25 상위에 보일러플레이트 없음",
          lambda: (all("Resistance  Welding  Equipment" not in x.content for x in bm), "정상"))
    dh = search("air circuit from the regulator to the welding cylinder",
                top_k=3, mode="hybrid_rerank")
    check("검색", "연결관계 질의에 도면이 상위 진입",
          lambda: (any(x.source == "vlm_description" for x in dh),
                   f"{sum(1 for x in dh if x.source=='vlm_description')}/3"))
    con.close()


def verify_agent():
    print("\n[6] Agent — 스키마 강제와 도구")
    from app.agent.schemas import SchemaError, TOOLS, validate_step
    from app.agent.tools import REGISTRY

    good = {"hypotheses": [{"id": "H1", "statement": "x", "score": 0.5,
                            "cited_evidence_ids": ["E1"]}],
            "action": {"type": "use_tool", "tool": "search_manual", "args": {"query": "q"}}}
    check("Agent", "정상 응답 통과", lambda: (bool(validate_step(dict(good), {"E1"})), "OK"))

    def rejects(d, ev={"E1"}):
        try:
            validate_step(d, ev); return False
        except (SchemaError, ValueError):
            return True

    check("Agent", "유령 증거 인용 거부 (환각 방어)",
          lambda: (rejects({"hypotheses": [{"id": "H1", "statement": "x", "score": .5,
                                            "cited_evidence_ids": ["E9"]}],
                            "action": {"type": "use_tool", "tool": "search_manual"}}), "거부"))
    check("Agent", "인용 없는 finalize 거부",
          lambda: (rejects({"hypotheses": [{"id": "H1", "statement": "x", "score": .5}],
                            "action": {"type": "finalize", "root_cause": "y"}}), "거부"))
    check("Agent", "빈 가설 거부",
          lambda: (rejects({"hypotheses": [], "action": {"type": "finalize"}}), "거부"))
    check("Agent", "알 수 없는 도구 거부",
          lambda: (rejects({"hypotheses": [{"id": "H1", "statement": "x", "score": .5}],
                            "action": {"type": "use_tool", "tool": "rm_rf"}}), "거부"))
    check("Agent", "촬영 요청에 if_observed 필수 (M4 정보이득의 전제)",
          lambda: (rejects({"hypotheses": [{"id": "H1", "statement": "x", "score": .5}],
                            "action": {"type": "request_photo",
                                       "requests": [{"target": "t", "how_to_shoot": "h"}]}}),
                   "거부"))
    check("Agent", "도구 레지스트리와 프롬프트 목록 일치",
          lambda: (set(REGISTRY) == set(TOOLS), f"{sorted(REGISTRY)}"))

    pdir = Path(__file__).resolve().parents[1] / "app" / "agent" / "prompts"
    check("Agent", "유형별 킥오프 프롬프트 2종 존재",
          lambda: (all((pdir / f"kickoff_{k}.md").exists() for k in ("burst", "level_shift")),
                   "burst · level_shift"))


def verify_harness():
    print("\n[7] 평가 하네스")
    from app.db import DB_PATH, connect
    if not DB_PATH.exists():
        check("하네스", "DB 존재", lambda: (False, "없음"))
        return
    con = connect()
    runs = con.execute("SELECT id, git_sha, config FROM eval_runs ORDER BY id DESC").fetchall()
    check("하네스", "eval_runs 기록 존재", lambda: (len(runs) > 0, f"{len(runs)}건"))
    if runs:
        check("하네스", "모든 run 에 git_sha (성과표 재현 가능성)",
              lambda: (all(r["git_sha"] and r["git_sha"] != "unknown" for r in runs),
                       f"최신 {runs[0]['git_sha']}"))
        check("하네스", "모든 run 에 config (ablation 조건)",
              lambda: (all(json.loads(r["config"]) for r in runs), "기록됨"))
    from eval.metrics import ALL_METRICS
    check("하네스", "지표 함수 등록", lambda: (len(ALL_METRICS) >= 3,
                                           f"{[f.__name__ for f in ALL_METRICS]}"))
    con.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-llm", action="store_true", help="LLM 호출이 필요한 항목 건너뜀")
    a = ap.parse_args()

    print("=" * 72)
    print("설계 의도 전수 검증 — scripts/90_verify_design.py")
    print("=" * 72)

    g = verify_data()
    verify_detectors(g)
    verify_stream(g)
    verify_cases()
    verify_retrieval()
    verify_agent()
    verify_harness()

    n = len(RESULTS)
    ok = sum(1 for *_, p, _ in RESULTS if p)
    print("\n" + "=" * 72)
    print(f"검증 {ok}/{n} 통과")
    fails = [(s, nm, note) for s, nm, p, note in RESULTS if not p]
    if fails:
        print("\n실패 항목:")
        for s, nm, note in fails:
            print(f"  ❌ [{s}] {nm} — {note}")
    print("=" * 72)

    out = Path(__file__).resolve().parents[1] / "outputs" / "verify_design.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        [{"section": s, "item": nm, "pass": p, "note": note} for s, nm, p, note in RESULTS],
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ {out}")
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
