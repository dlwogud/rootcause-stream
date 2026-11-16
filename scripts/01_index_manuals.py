#!/usr/bin/env python3
"""매뉴얼 PDF → SQLite 색인 (텍스트 청크 + 도면 페이지 렌더).

페이지를 2종으로 가른다.
  text    : 청킹 → 임베딩 + FTS5(BM25)
  diagram : 200dpi PNG 렌더 → 별도 단계에서 VLM 구조 서술 생성 (02_describe_diagrams.py)

도면을 텍스트로 색인할 수 없는 것이 기술 #3(Multimodal RAG)의 존재 이유다.
배선도의 연결 관계는 선으로만 그려져 있어 pdftotext 로는 아무것도 나오지 않는다.

사용: python3 scripts/01_index_manuals.py [--reset]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db import connect, init_db, to_blob  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "data" / "manuals" / "pdf"
IMG_DIR = ROOT / "data" / "manuals" / "pages"
EMB_MODEL = "BAAI/bge-small-en-v1.5"   # 133MB. 매뉴얼이 영문이라 영어 전용으로 충분
RENDER_DPI = 200

# 도면 '렌더' 판정 — 이미지가 있고 텍스트가 희박하면 도면으로 보고 PNG 로 남긴다.
# 주의: 이것은 **배타 분류가 아니다.** 그림과 지시문이 함께 있는 페이지는 둘 다이므로
# 텍스트는 page_kind 와 무관하게 항상 색인한다.
# (실제로 그렇게 하지 않아 spotweldinc p.6 의 "air pressure gauge reads 0.5 MPa" 가
#  색인에서 빠졌다. 그 문장은 VLM 판독 결과를 대조할 기준값이라 반드시 필요하다.)
DIAGRAM_MAX_CHARS = 900
MIN_TEXT_CHARS = 150          # 이보다 짧으면 청킹하지 않는다
CHUNK_CHARS = 1200
CHUNK_OVERLAP = 150

KW = {
    "troubleshoot": r"troublesh|fault find|diagnos|symptom|remedy|probable cause|corrective action",
    "flowchart":    r"flow\s?chart|flow diagram|decision",
    "pneumatic":    r"pneumatic|air circuit|air supply|cylinder|regulator|solenoid valve",
    "cooling":      r"cooling water|coolant|water circuit|water flow|chiller",
    "schematic":    r"schematic|wiring diagram|circuit diagram|P&ID|piping",
    "electrode":    r"electrode|tip dress|mushroom|cap tip|tip wear|alignment",
    "errorcode":    r"error code|alarm code|fault code|E\d{2,3}\b",
}
KWC = {k: re.compile(v, re.I) for k, v in KW.items()}

HEADING = re.compile(r"^\s*(\d+(?:\.\d+)*)\s+([A-Z][A-Za-z0-9 \-/&,()']{3,70})\s*$", re.M)

# 문서 전체에서 이 비율 이상의 페이지에 나타나는 줄은 머리말/꼬리말로 본다.
# 제거하지 않으면 BM25 가 보일러플레이트를 상위로 올린다(실제로 그랬다).
BOILERPLATE_RATIO = 0.25
BOILERPLATE_MAX_LEN = 120


def find_boilerplate(pages: list[str]) -> set[str]:
    from collections import Counter
    c = Counter()
    for t in pages:
        seen = set()
        for line in t.splitlines():
            ln = re.sub(r"\s+", " ", line).strip()
            if 3 <= len(ln) <= BOILERPLATE_MAX_LEN and ln not in seen:
                seen.add(ln)
                c[ln] += 1
    cut = max(2, int(len(pages) * BOILERPLATE_RATIO))
    return {ln for ln, n in c.items() if n >= cut}


def strip_boilerplate(text: str, boiler: set[str]) -> str:
    keep = []
    for line in text.splitlines():
        ln = re.sub(r"\s+", " ", line).strip()
        if ln in boiler:
            continue
        # 페이지 번호만 있는 줄
        if re.fullmatch(r"[-–\s]*\d{1,4}[-–\s]*", ln):
            continue
        keep.append(line)
    return "\n".join(keep)


def split_chunks(text: str) -> list[tuple[str | None, str]]:
    """헤딩 경계를 우선하고, 길면 문자 수로 자른다."""
    text = re.sub(r"[ \t]+", " ", text).strip()
    if not text:
        return []
    marks = [(m.start(), f"{m.group(1)} {m.group(2)}".strip()) for m in HEADING.finditer(text)]
    segs: list[tuple[str | None, str]] = []
    if marks:
        bounds = [p for p, _ in marks] + [len(text)]
        if bounds[0] > 0:
            segs.append((None, text[:bounds[0]]))
        for (pos, head), end in zip(marks, bounds[1:]):
            segs.append((head, text[pos:end]))
    else:
        segs.append((None, text))

    out: list[tuple[str | None, str]] = []
    for head, body in segs:
        body = body.strip()
        if len(body) <= CHUNK_CHARS:
            if len(body) >= 40:
                out.append((head, body))
            continue
        i = 0
        while i < len(body):
            piece = body[i:i + CHUNK_CHARS]
            if len(piece) >= 40:
                out.append((head, piece.strip()))
            i += CHUNK_CHARS - CHUNK_OVERLAP
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="DB 를 새로 만든다")
    a = ap.parse_args()

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"PDF 가 없다: {PDF_DIR}\n  data/manuals/SOURCES.md 의 재수집 명령을 실행하라.",
              file=sys.stderr)
        return 2

    from sentence_transformers import SentenceTransformer
    print(f"임베딩 모델 적재: {EMB_MODEL}")
    model = SentenceTransformer(EMB_MODEL)
    dim = model.get_sentence_embedding_dimension()
    print(f"  dim={dim}")

    con = init_db(drop=a.reset) if a.reset else connect()
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    n_page = n_diag = n_chunk = 0
    for pdf in pdfs:
        doc = pymupdf.open(pdf)
        pend: list[tuple] = []
        raw_pages = [doc[i].get_text("text") for i in range(len(doc))]
        boiler = find_boilerplate(raw_pages)
        print(f"\n{pdf.name} — {len(doc)}p · 보일러플레이트 {len(boiler)}줄 제거")
        n_diag_doc = 0
        for pno in range(len(doc)):
            page = doc[pno]
            text = strip_boilerplate(raw_pages[pno], boiler)
            nimg = len(page.get_images(full=True))
            chars = len(text.strip())
            kinds = "|".join(k for k, rx in KWC.items() if rx.search(text))
            is_diagram = nimg >= 1 and chars < DIAGRAM_MAX_CHARS

            img_path = None
            if is_diagram:
                out = IMG_DIR / f"{pdf.stem}_p{pno + 1:03d}.png"
                if not out.exists():
                    page.get_pixmap(dpi=RENDER_DPI).save(out)
                img_path = str(out.relative_to(ROOT))
                n_diag += 1
                n_diag_doc += 1

            cur = con.execute(
                "INSERT OR REPLACE INTO manual_pages"
                " (doc, page_no, page_kind, n_images, n_chars, image_path, keywords)"
                " VALUES (?,?,?,?,?,?,?)",
                (pdf.name, pno + 1, "diagram" if is_diagram else "text",
                 nimg, chars, img_path, kinds))
            page_id = cur.lastrowid
            n_page += 1

            # 텍스트는 도면 페이지에서도 색인한다 (배타 분류가 아니다)
            if chars >= MIN_TEXT_CHARS:
                for ordi, (head, body) in enumerate(split_chunks(text)):
                    pend.append((page_id, ordi, head, body))

        if pend:
            vecs = model.encode([b for *_, b in pend], batch_size=32,
                                normalize_embeddings=True, show_progress_bar=False)
            for (page_id, ordi, head, body), v in zip(pend, vecs):
                cid = con.execute(
                    "INSERT INTO manual_chunks (page_id, ord, heading, content, source, embedding)"
                    " VALUES (?,?,?,?,'text',?)",
                    (page_id, ordi, head, body, to_blob(v))).lastrowid
                con.execute("INSERT INTO manual_fts (rowid, content, heading) VALUES (?,?,?)",
                            (cid, body, head or ""))
            n_chunk += len(pend)
        con.commit()
        print(f"  페이지 {len(doc)} · 도면 {n_diag_doc} · 청크 {len(pend)}")

    con.commit()
    print(f"\n색인 완료 — 페이지 {n_page} · 도면 {n_diag} · 청크 {n_chunk} · dim {dim}")
    print(f"도면 PNG: {IMG_DIR}")
    print("다음: python3 scripts/02_describe_diagrams.py  (VLM 구조 서술 생성)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
