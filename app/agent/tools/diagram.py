"""lookup_diagram — 도면을 찾아 **원본 이미지를 VLM 에 다시 투입**해 질문에 답한다.

기술 #3(Multimodal RAG)의 핵심. 서술만 보고 답하면 세부 연결을 놓치므로,
서술로 페이지를 찾은 뒤 이미지를 직접 읽힌다.
"""
from __future__ import annotations

import json
import subprocess

from app.db import ROOT, connect
from app.retrieval.hybrid import search

PROMPT = """Read the engineering diagram at {path}
({doc} page {page}, from a resistance spot welding machine manual).

Answer this question using ONLY what is visibly drawn or labelled on the diagram:
  {question}

If the diagram does not contain the answer, say so plainly. Do not guess at connections
that are not drawn. Quote component tags verbatim when you refer to them.

Respond with ONLY this JSON object, no fence:
{{"answer": "<2-4 sentences>", "answerable_from_diagram": true|false,
  "components_referenced": ["<tag>", ...]}}"""


def lookup_diagram(question: str, model: str = "haiku", **_) -> dict:
    hits = [h for h in search(question, top_k=6, mode="hybrid_rerank")
            if h.source == "vlm_description" and h.image_path]
    if not hits:
        con = connect()
        row = con.execute(
            "SELECT doc, page_no, image_path FROM manual_pages"
            " WHERE page_kind='diagram' AND vlm_description IS NOT NULL"
            " AND vlm_description<>'' LIMIT 1").fetchone()
        con.close()
        if not row:
            return {"error": "서술된 도면이 없다. scripts/02_describe_diagrams.py 를 실행하라"}
        doc, page, img = row["doc"], row["page_no"], row["image_path"]
    else:
        h = hits[0]
        doc, page, img = h.doc, h.page_no, h.image_path

    r = subprocess.run(
        ["claude", "-p", "--model", model, "--allowedTools", "Read",
         "--output-format", "json",
         PROMPT.format(path=ROOT / img, doc=doc, page=page, question=question)],
        capture_output=True, text=True, timeout=240)
    if r.returncode != 0:
        return {"error": f"VLM 호출 실패: {r.stderr[:120]}"}
    env = json.loads(r.stdout)
    raw = (env.get("result") or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        out = {"answer": raw[:600], "answerable_from_diagram": None}
    out["cite"] = f"{doc} p.{page} [도면]"
    out["_cost_cc"] = env.get("total_cost_usd", 0.0)
    return out
