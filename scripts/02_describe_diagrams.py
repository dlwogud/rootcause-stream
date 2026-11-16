#!/usr/bin/env python3
"""도면 페이지 → VLM 구조 서술 → 색인 (기술 #3 Multimodal RAG).

텍스트 RAG 로는 "V-203 밸브가 어느 실린더에 연결되는가" 를 영원히 답할 수 없다.
그 정보는 **선으로만** 그려져 있다. 그래서 도면을 VLM 에 보여 구조를 서술하게 하고,
그 서술을 색인한다. 조회 시에는 서술로 페이지를 찾은 뒤 **원본 이미지를 다시 VLM 에
투입**해 구체 질의에 답하게 한다(서술만 보고 답하면 세부 연결을 놓친다).

사용:
  python3 scripts/02_describe_diagrams.py                 # 우선 대상만
  python3 scripts/02_describe_diagrams.py --all --limit 60
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db import ROOT, connect, to_blob  # noqa: E402

EMB_MODEL = "BAAI/bge-small-en-v1.5"
PRIORITY_KW = ["schematic", "pneumatic", "cooling", "flowchart", "troubleshoot", "electrode"]

PROMPT = """Read the engineering diagram image at {path}.

This page is from a resistance spot welding machine manual. Describe it so that someone
searching a text index can FIND this page, and so that a later reader knows what questions
this diagram can answer.

Write 80-160 words of plain prose covering, where present:
- What kind of drawing it is (wiring/electrical schematic, pneumatic or air circuit,
  cooling water circuit, mechanical assembly, troubleshooting flowchart, parts diagram)
- Every component label and tag you can read, verbatim (e.g. TRF, CN1, TS1, MSW, S1)
- What connects to what, and the direction of flow or signal
- Any numeric setpoints, ranges, or units printed on the drawing
- What a maintenance technician could determine from this page

Do not speculate about parts you cannot see. If the page is mostly a photograph or a logo
rather than a diagram, say so in one sentence.

Respond with ONLY the prose description. No preamble, no markdown, no bullet list."""


def describe(image_rel: str, model: str) -> tuple[str, dict]:
    path = ROOT / image_rel
    r = subprocess.run(
        ["claude", "-p", "--model", model, "--allowedTools", "Read",
         "--output-format", "json", PROMPT.format(path=path)],
        capture_output=True, text=True, timeout=240)
    if r.returncode != 0:
        raise RuntimeError(f"claude exit {r.returncode}: {r.stderr[:160]}")
    env = json.loads(r.stdout)
    if env.get("is_error"):
        raise RuntimeError(f"claude error: {str(env.get('result'))[:160]}")
    return env["result"].strip(), {"ms": env.get("duration_ms", 0),
                                   "cost": env.get("total_cost_usd", 0.0)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--all", action="store_true", help="키워드 없는 도면도 포함")
    ap.add_argument("--redo", action="store_true", help="이미 서술된 페이지도 다시")
    a = ap.parse_args()

    con = connect()
    sql = ("SELECT id, doc, page_no, image_path, keywords FROM manual_pages"
           " WHERE page_kind='diagram' AND image_path IS NOT NULL")
    if not a.redo:
        sql += " AND (vlm_description IS NULL OR vlm_description='')"
    rows = con.execute(sql).fetchall()

    if not a.all:
        rows = [r for r in rows if any(k in (r["keywords"] or "") for k in PRIORITY_KW)]
    # 우선순위 키워드가 많은 페이지부터
    rows.sort(key=lambda r: -sum(k in (r["keywords"] or "") for k in PRIORITY_KW))
    rows = rows[: a.limit]

    if not rows:
        print("대상 없음."); return 0
    print(f"도면 {len(rows)}장 · model={a.model} · 동시 {a.workers}\n")

    done, cost, results = 0, 0.0, []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(describe, r["image_path"], a.model): r for r in rows}
        for fut in as_completed(futs):
            r = futs[fut]; done += 1
            try:
                desc, u = fut.result()
            except Exception as e:
                print(f"  [{done}/{len(rows)}] ! {r['doc']} p{r['page_no']}: {e}", file=sys.stderr)
                continue
            cost += u["cost"]
            results.append((r["id"], desc))
            print(f"  [{done}/{len(rows)}] {r['doc'][:22]:24s} p{r['page_no']:3d} "
                  f"{u['ms']/1000:5.1f}s  {desc[:64]}...")

    if not results:
        return 1
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMB_MODEL)
    vecs = model.encode([d for _, d in results], normalize_embeddings=True,
                        show_progress_bar=False)

    for (pid, desc), v in zip(results, vecs):
        con.execute("UPDATE manual_pages SET vlm_description=? WHERE id=?", (desc, pid))
        con.execute("DELETE FROM manual_chunks WHERE page_id=? AND source='vlm_description'", (pid,))
        cid = con.execute(
            "INSERT INTO manual_chunks (page_id, ord, heading, content, source, embedding)"
            " VALUES (?, 999, '[도면]', ?, 'vlm_description', ?)",
            (pid, desc, to_blob(v))).lastrowid
        con.execute("INSERT INTO manual_fts (rowid, content, heading) VALUES (?,?,?)",
                    (cid, desc, "[도면]"))
    con.commit()
    print(f"\n서술 {len(results)}장 색인 · 구독 사용량 환산 ${cost:.3f}"
          f"  ⚠️ Claude Code 오버헤드 포함, 서비스 비용 아님")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
