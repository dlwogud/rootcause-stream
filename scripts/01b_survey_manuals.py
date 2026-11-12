#!/usr/bin/env python3
"""매뉴얼 PDF를 페이지 단위로 조사해 도면/플로우차트/트러블슈팅 페이지를 찾는다.

docs/05-data.md 의 D2 게이트 판정용. pdftotext/pdfimages(poppler)만 사용.
출력: data/manuals/SURVEY.md  +  data/manuals/survey.csv
"""
from __future__ import annotations
import csv, re, subprocess, sys
from pathlib import Path

PDF_DIR = Path("data/manuals/pdf")
OUT_DIR = Path("data/manuals")

KW = {
    "troubleshoot": r"troublesh|fault find|diagnos|symptom|remedy|probable cause|corrective action",
    "flowchart":    r"flow\s?chart|flow diagram|decision|if\s+yes|if\s+no|go to step",
    "pneumatic":    r"pneumatic|air circuit|air supply|cylinder|regulator|solenoid valve|FRL",
    "cooling":      r"cooling water|coolant|water circuit|water flow|chiller|hose",
    "schematic":    r"schematic|wiring diagram|circuit diagram|P&ID|piping|layout drawing",
    "electrode":    r"electrode|tip dress|mushroom|cap tip|tip wear|alignment",
    "errorcode":    r"error code|alarm code|fault code|E\d{2,3}\b|err\s*\d",
}
KWC = {k: re.compile(v, re.I) for k, v in KW.items()}


def page_texts(pdf: Path) -> list[str]:
    n = int(subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True)
            .stdout.split("Pages:")[1].split()[0])
    out = []
    for p in range(1, n + 1):
        r = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), "-layout", str(pdf), "-"],
                           capture_output=True, text=True)
        out.append(r.stdout)
    return out


def page_image_count(pdf: Path, n: int) -> list[int]:
    r = subprocess.run(["pdfimages", "-list", str(pdf)], capture_output=True, text=True)
    counts = [0] * (n + 1)
    for line in r.stdout.splitlines()[2:]:
        f = line.split()
        if f and f[0].isdigit():
            pg = int(f[0])
            if 0 < pg <= n:
                counts[pg] += 1
    return counts[1:]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows, summary = [], []

    for pdf in sorted(PDF_DIR.glob("*.pdf")):
        texts = page_texts(pdf)
        imgs = page_image_count(pdf, len(texts))
        hits = {k: [] for k in KW}
        diagram_pages = []

        for i, (t, nimg) in enumerate(zip(texts, imgs), start=1):
            chars = len(t.strip())
            for k, rx in KWC.items():
                if rx.search(t):
                    hits[k].append(i)
            # 도면 후보: 이미지가 있고 텍스트가 희박한 페이지
            is_diag = nimg >= 1 and chars < 900
            if is_diag:
                diagram_pages.append(i)
            rows.append({"pdf": pdf.name, "page": i, "chars": chars,
                         "images": nimg, "diagram_candidate": int(is_diag),
                         "keywords": "|".join(k for k, rx in KWC.items() if rx.search(t))})

        summary.append({
            "pdf": pdf.name, "pages": len(texts),
            "diagram_candidates": len(diagram_pages),
            "diagram_pages": diagram_pages[:25],
            **{k: v[:12] for k, v in hits.items()},
        })

    with open(OUT_DIR / "survey.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["pdf", "page", "chars", "images",
                                          "diagram_candidate", "keywords"])
        w.writeheader(); w.writerows(rows)

    lines = ["# 매뉴얼 조사 결과 (자동 생성: scripts/01b_survey_manuals.py)", "",
             "> D2 게이트 판정용. `diagram_candidate` = 이미지가 있고 텍스트가 희박한 페이지.", ""]
    tot_diag = 0
    for s in summary:
        tot_diag += s["diagram_candidates"]
        lines += [f"## {s['pdf']} — {s['pages']}p",
                  "", f"- 도면 후보 페이지 **{s['diagram_candidates']}장**: {s['diagram_pages']}", ""]
        for k in KW:
            if s[k]:
                lines.append(f"- `{k}` → p{s[k]}")
        lines.append("")
    lines += ["---", "", f"**합계 도면 후보 {tot_diag}장**", "",
              "게이트 기준: 도면 3장 + 플로우차트 2개 → "
              + ("✅ 통과" if tot_diag >= 5 else "⬜ 미달, 수동 확인 필요")]
    (OUT_DIR / "SURVEY.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[-6:]))
    print(f"\n→ {OUT_DIR/'SURVEY.md'} / survey.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
