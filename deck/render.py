#!/usr/bin/env python3
"""PPTX → PNG 렌더러 (검수용). LibreOffice 없이 슬라이드를 눈으로 확인한다.

이 맥에는 LibreOffice 가 없고 설치도 막혀 있어, 이전 프로젝트(capstone pptcheck)처럼
도형을 직접 읽어 PIL 로 그린다. 그 렌더러에 없던 세 가지를 더했다.
  - 테마 색(schemeClr) 해석 — 없으면 테마 색 글자가 전부 검정으로 나온다
  - 표 그리기
  - **글자 넘침 자동 검출** — 상자보다 글이 길면 빨간 테두리 + 보고서에 기록

글꼴은 덱과 같은 Apple SD Gothic Neo 라 줄바꿈 위치는 PowerPoint 와 거의 같다.
그림자·그라디언트·애니메이션은 그리지 않는다.

  python3 deck/render.py deck/RootCause_Stream_발표자료.pptx deck/preview
"""
from __future__ import annotations

import sys
from pathlib import Path

from lxml import etree
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation

NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
TTC = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
FACE = {(False, False): 0, (True, False): 6, (False, True): 0, (True, True): 6}
EMU_IN = 914400
SCHEME_KEY = {"tx1": "dk1", "tx2": "dk2", "bg1": "lt1", "bg2": "lt2"}
_fc: dict = {}


def theme_colors(prs) -> dict:
    part = prs.slide_master.part
    for rel in part.rels.values():
        if "theme" in rel.reltype:
            root = etree.fromstring(rel.target_part.blob)
            cs = root.find(".//a:clrScheme", NS)
            out = {}
            for el in cs:
                tag = etree.QName(el).localname
                c = el.find("a:srgbClr", NS)
                if c is None:
                    c = el.find("a:sysClr", NS)
                    out[tag] = c.get("lastClr") if c is not None else "000000"
                else:
                    out[tag] = c.get("val")
            return out
    return {}


def color_of(el, theme, default=None):
    """a:solidFill 같은 요소 아래의 색을 hex 로."""
    if el is None:
        return default
    c = el.find("a:srgbClr", NS)
    if c is not None:
        return c.get("val")
    c = el.find("a:schemeClr", NS)
    if c is not None:
        v = c.get("val")
        return theme.get(SCHEME_KEY.get(v, v), default)
    return default


def rgb(h):
    return tuple(bytes.fromhex(h)) if h else None


def font(px, bold):
    key = (max(1, int(px)), bold)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(TTC, key[0], index=FACE[(bold, False)])
    return _fc[key]


def layout_defaults(slide, theme) -> dict:
    """레이아웃 placeholder 의 기본 글자 속성 (idx → {sz,b,color})."""
    out = {}
    for sh in slide.slide_layout.placeholders:
        el = sh._element
        d = el.find(".//a:lstStyle/a:lvl1pPr/a:defRPr", NS)
        if d is None:
            d = el.find(".//a:rPr", NS)
        props = {}
        if d is not None:
            if d.get("sz"):
                props["sz"] = int(d.get("sz")) / 100
            if d.get("b"):
                props["b"] = d.get("b") == "1"
            props["color"] = color_of(d.find("a:solidFill", NS), theme)
        bp = el.find(".//a:bodyPr", NS)
        props["anchor"] = bp.get("anchor") if bp is not None else None
        out[sh.placeholder_format.idx] = props
    return out


def wrap(text, f, maxw):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for ch in para:
            if f.getlength(cur + ch) <= maxw or not cur:
                cur += ch
            else:
                cut = cur.rfind(" ")
                if cut > 0 and ch != " ":
                    lines.append(cur[:cut]); cur = cur[cut + 1:] + ch
                else:
                    lines.append(cur.rstrip()); cur = ch.lstrip()
        lines.append(cur)
    return lines


def draw_txbody(dr, txb, box, scale, theme, dflt, problems, label):
    x, y, w, h = box
    bp = txb.find("a:bodyPr", NS)
    ins = lambda k, d: int(bp.get(k)) / EMU_IN * scale if bp is not None and bp.get(k) else d * scale
    lI, rI, tI, bI = ins("lIns", .1), ins("rIns", .1), ins("tIns", .05), ins("bIns", .05)
    anchor = (bp.get("anchor") if bp is not None and bp.get("anchor") else dflt.get("anchor")) or "t"
    blocks, total = [], 0.0
    for p in txb.findall("a:p", NS):
        runs = p.findall("a:r", NS)
        txt = "".join((r.findtext("a:t", "", NS)) for r in runs)
        rpr = runs[0].find("a:rPr", NS) if runs else p.find("a:endParaRPr", NS)
        sz = (int(rpr.get("sz")) / 100 if rpr is not None and rpr.get("sz") else dflt.get("sz", 18))
        bold = (rpr.get("b") == "1") if rpr is not None and rpr.get("b") else dflt.get("b", False)
        col = color_of(rpr.find("a:solidFill", NS), theme) if rpr is not None else None
        col = col or dflt.get("color") or theme.get("dk1", "000000")
        ppr = p.find("a:pPr", NS)
        bullet = ppr is not None and ppr.find("a:buChar", NS) is not None
        algn = ppr.get("algn") if ppr is not None and ppr.get("algn") else "l"
        spc = ppr.find("a:spcAft/a:spcPts", NS) if ppr is not None else None
        after = int(spc.get("val")) / 100 * scale / 72 if spc is not None else 0
        px = sz * scale / 72
        f = font(px, bold)
        indent = px * 1.1 if bullet else 0
        lines = wrap(txt, f, max(1, w - lI - rI - indent)) if txt else [""]
        lh = px * 1.2
        blocks.append((lines, f, col, lh, bullet, indent, algn, after))
        total += lh * len(lines) + after
    avail = h - tI - bI
    cy = y + tI + {"ctr": (avail - total) / 2, "b": avail - total}.get(anchor, 0)
    for lines, f, col, lh, bullet, indent, algn, after in blocks:
        for i, ln in enumerate(lines):
            lx = x + lI + indent
            if algn == "ctr":
                lx = x + (w - f.getlength(ln)) / 2
            elif algn == "r":
                lx = x + w - rI - f.getlength(ln)
            if bullet and i == 0:
                dr.text((x + lI, cy), "•", font=f, fill=rgb(col))
            dr.text((lx, cy), ln, font=f, fill=rgb(col))
            cy += lh
        cy += after
    if total > avail + 2:
        dr.rectangle([x, y, x + w, y + h], outline=(230, 0, 0), width=3)
        problems.append(f"{label}: 넘침 {total - avail:.0f}px — “{''.join(blocks[0][0])[:30]}”")


def render(path, outdir, width=1600):
    prs = Presentation(path)
    theme = theme_colors(prs)
    scale = width / (prs.slide_width / EMU_IN)
    H = int(prs.slide_height / EMU_IN * scale)
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    report = []
    for n, slide in enumerate(prs.slides, start=1):
        bgc = "FFFFFF"
        for src in (slide, slide.slide_layout, slide.slide_layout.slide_master):
            bg = src._element.find(".//p:bg/p:bgPr/a:solidFill", NS)
            if bg is not None:
                bgc = color_of(bg, theme, "FFFFFF"); break
        img = Image.new("RGB", (width, H), rgb(bgc))
        dr = ImageDraw.Draw(img)
        dflt = layout_defaults(slide, theme)
        problems = []
        shapes = list(slide.slide_layout.shapes) + list(slide.shapes)
        for sh in shapes:
            if sh in slide.slide_layout.shapes and sh.is_placeholder:
                continue                                   # 레이아웃의 빈 placeholder 는 그리지 않는다
            if sh.left is None:
                continue
            x, y = sh.left / EMU_IN * scale, sh.top / EMU_IN * scale
            w, h = sh.width / EMU_IN * scale, sh.height / EMU_IN * scale
            el = sh._element
            label = f"#{n} {sh.name}"
            if sh.shape_type is not None and sh.has_table if hasattr(sh, "has_table") else False:
                tbl = el.find(".//a:tbl", NS)
                cols = [int(g.get("w")) / EMU_IN * scale for g in tbl.findall("a:tblGrid/a:gridCol", NS)]
                cy = y
                for tr in tbl.findall("a:tr", NS):
                    rh = int(tr.get("h")) / EMU_IN * scale
                    cx = x
                    for cw, tc in zip(cols, tr.findall("a:tc", NS)):
                        fill = color_of(tc.find("a:tcPr/a:solidFill", NS), theme)
                        dr.rectangle([cx, cy, cx + cw, cy + rh], fill=rgb(fill) if fill else None,
                                     outline=(215, 218, 223))
                        tx = tc.find("a:txBody", NS)
                        if tx is not None:
                            tcpr = tc.find("a:tcPr", NS)
                            mar = lambda k, d: int(tcpr.get(k)) / EMU_IN * scale if tcpr is not None and tcpr.get(k) else d * scale
                            fake = etree.fromstring(etree.tostring(tx))
                            bp = fake.find("a:bodyPr", NS)
                            bp.set("lIns", str(int(mar("marL", .1) / scale * EMU_IN)))
                            bp.set("rIns", str(int(mar("marR", .1) / scale * EMU_IN)))
                            bp.set("anchor", (tcpr.get("anchor") if tcpr is not None and tcpr.get("anchor") else "ctr"))
                            draw_txbody(dr, fake, (cx, cy, cw, rh), scale, theme, {}, problems, label + " 표")
                        cx += cw
                    cy += rh
                continue
            if getattr(sh, "shape_type", None) == 13:     # PICTURE — 실제 이미지를 그려 배치를 검수한다
                import io
                pic = Image.open(io.BytesIO(sh.image.blob)).convert("RGB")
                img.paste(pic.resize((max(1, int(w)), max(1, int(h)))), (int(x), int(y)))
                if x + w > width + 1 or y + h > H + 1:
                    problems.append(f"{label}: 슬라이드 밖으로 나감")
                continue
            geom = el.find(".//a:prstGeom", NS)
            g = geom.get("prst") if geom is not None else None
            spPr = el.find("p:spPr", NS)
            fill = color_of(spPr.find("a:solidFill", NS), theme) if spPr is not None else None
            ln = spPr.find("a:ln", NS) if spPr is not None else None
            lcol = color_of(ln.find("a:solidFill", NS), theme) if ln is not None else None
            lw = max(1, int(int(ln.get("w")) / 12700 * scale / 96)) if ln is not None and ln.get("w") else 1
            if g in ("roundRect",):
                dr.rounded_rectangle([x, y, x + w, y + h], radius=min(0.12 * scale, min(w, h) / 2),
                                     fill=rgb(fill), outline=rgb(lcol), width=lw if lcol else 0)
            elif g in ("ellipse",):
                dr.ellipse([x, y, x + w, y + h], fill=rgb(fill), outline=rgb(lcol))
            elif g in ("rect",) and (fill or lcol):
                dr.rectangle([x, y, x + w, y + h], fill=rgb(fill), outline=rgb(lcol))
            txb = el.find("p:txBody", NS)
            if txb is not None and "".join(txb.itertext()).strip():
                d = dflt.get(sh.placeholder_format.idx, {}) if sh.is_placeholder else {}
                draw_txbody(dr, txb, (x, y, w, h), scale, theme, d, problems, label)
            if x + w > width + 1 or y + h > H + 1 or x < -1 or y < -1:
                problems.append(f"{label}: 슬라이드 밖으로 나감")
        out = outdir / f"slide-{n:02d}.png"
        img.save(out)
        report.append((n, problems))
    print(f"렌더 {len(report)}장 → {outdir}")
    bad = [(n, p) for n, p in report if p]
    for n, ps in bad:
        for p in ps:
            print(f"  ⚠ {p}")
    if not bad:
        print("  넘침·이탈 없음")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(render(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "deck/preview"))
