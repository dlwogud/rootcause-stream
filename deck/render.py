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


def _run_style(rpr, dflt, theme):
    sz = (int(rpr.get("sz")) / 100 if rpr is not None and rpr.get("sz") else dflt.get("sz", 18))
    bold = (rpr.get("b") == "1") if rpr is not None and rpr.get("b") else dflt.get("b", False)
    col = color_of(rpr.find("a:solidFill", NS), theme) if rpr is not None else None
    return sz, bold, col or dflt.get("color") or theme.get("dk1", "000000")


def _wrap_runs(segs, maxw):
    """segs: [(문자, font, color)] → 줄 목록. 공백에서 끊되, 못 끊으면 글자에서 끊는다 (글자별 스타일 유지)."""
    lines, cur, curw = [], [], 0.0
    for ch, f, col in segs:
        if ch == "\n":                                  # 강제 줄바꿈 (<a:br/>)
            lines.append(cur); cur, curw = [], 0.0
            continue
        cw = f.getlength(ch)
        if cur and curw + cw > maxw:
            cut = max((i for i, c in enumerate(cur) if c[0] == " "), default=-1)
            if cut > 0 and ch != " ":
                lines.append(cur[:cut]); cur = cur[cut + 1:]
            else:
                lines.append(cur); cur = []
            curw = sum(c[1].getlength(c[0]) for c in cur)
            if ch == " " and not cur:
                continue
        cur.append((ch, f, col)); curw += cw
    lines.append(cur)
    return lines


def draw_txbody(dr, txb, box, scale, theme, dflt, problems, label):
    x, y, w, h = box
    bp = txb.find("a:bodyPr", NS)
    ins = lambda k, d: int(bp.get(k)) / EMU_IN * scale if bp is not None and bp.get(k) else d * scale
    lI, rI, tI, bI = ins("lIns", .1), ins("rIns", .1), ins("tIns", .05), ins("bIns", .05)
    anchor = (bp.get("anchor") if bp is not None and bp.get("anchor") else dflt.get("anchor")) or "t"
    blocks, total, plain = [], 0.0, []
    for p in txb.findall("a:p", NS):
        segs, last = [], None
        for r in p:                                      # 순서대로 — 글자 묶음과 줄바꿈이 섞인다
            tag = etree.QName(r).localname
            if tag == "r":
                sz, bold, col = _run_style(r.find("a:rPr", NS), dflt, theme)
                f = font(sz * scale / 72, bold)
                last = (f, col)
                segs += [(ch, f, col) for ch in r.findtext("a:t", "", NS)]
            elif tag == "br":
                sz, bold, col = _run_style(r.find("a:rPr", NS), dflt, theme)
                f = font(sz * scale / 72, bold)
                segs.append(("\n", f, col))
        plain.append("".join(c[0] for c in segs if c[0] != "\n"))
        if segs:
            base = max(segs, key=lambda c: c[1].size)[1]
        else:
            sz, bold, _ = _run_style(p.find("a:endParaRPr", NS), dflt, theme)
            base = font(sz * scale / 72, bold)
        ppr = p.find("a:pPr", NS)
        bullet = ppr is not None and ppr.find("a:buChar", NS) is not None
        algn = ppr.get("algn") if ppr is not None and ppr.get("algn") else "l"
        spc = ppr.find("a:spcAft/a:spcPts", NS) if ppr is not None else None
        after = int(spc.get("val")) / 100 * scale / 72 if spc is not None else 0
        indent = base.size * 1.1 if bullet else 0
        lines = _wrap_runs(segs, max(1, w - lI - rI - indent)) if segs else [[]]
        lhs = [max([c[1].size for c in ln] or [base.size]) * 1.2 for ln in lines]
        if segs and segs[-1][0] == "\n" and lines and not lines[-1]:   # 끝의 줄바꿈 뒤 빈 줄
            pass
        blocks.append((lines, lhs, bullet, indent, algn, after, base))
        total += sum(lhs) + after
    avail = h - tI - bI
    cy = y + tI + {"ctr": (avail - total) / 2, "b": avail - total}.get(anchor, 0)
    for lines, lhs, bullet, indent, algn, after, base in blocks:
        for i, (ln, lh) in enumerate(zip(lines, lhs)):
            lw = sum(c[1].getlength(c[0]) for c in ln)
            lx = x + lI + indent
            if algn == "ctr":
                lx = x + (w - lw) / 2
            elif algn == "r":
                lx = x + w - rI - lw
            if bullet and i == 0 and ln:
                dr.text((x + lI, cy), "•", font=ln[0][1], fill=rgb(ln[0][2]))
            top = max([c[1].size for c in ln] or [base.size])
            for ch, f, col in ln:
                dr.text((lx, cy + (top - f.size) * 0.85), ch, font=f, fill=rgb(col))
                lx += f.getlength(ch)
            cy += lh
        cy += after
    if total > avail + 2:
        dr.rectangle([x, y, x + w, y + h], outline=(230, 0, 0), width=3)
        problems.append(f"{label}: 넘침 {total - avail:.0f}px — “{''.join(plain)[:30]}”")


def draw_bar_chart(dr, chart, box, scale, theme, problems, label):
    """가로·세로 막대 차트(쌓기 포함)를 대략 그린다 — 배치·라벨 겹침 검수용."""
    x, y, w, h = box
    plot = chart.plots[0]
    cats = list(plot.categories)
    series = list(plot.series)
    horiz = plot._element.find("{http://schemas.openxmlformats.org/drawingml/2006/chart}barDir").get("val") == "bar"
    stacked = "stacked" in (plot._element.find("{http://schemas.openxmlformats.org/drawingml/2006/chart}grouping").get("val") or "")
    cols = []
    for se in series:
        c = se._element.find(".//{http://schemas.openxmlformats.org/drawingml/2006/chart}spPr/a:solidFill", NS)
        cols.append(color_of(c, theme, "888888"))
    vals = [[v or 0 for v in se.values] for se in series]
    tot = [sum(col) for col in zip(*vals)] if stacked else [max(col) for col in zip(*vals)]
    vmax = max(tot + [1])
    try:
        vmax = max(vmax, chart.value_axis.maximum_scale or 0)
    except Exception:
        pass
    f = font(int(12 / 72 * scale), False)
    pad_l = (max(dr.textlength(str(c), font=f) for c in cats) + 12) if horiz else 10
    pad_b = 10 if horiz else 30
    px, py, pw, ph = x + pad_l, y + 10, w - pad_l - 50, h - 20 - pad_b
    n = len(cats)
    for i, c in enumerate(cats):
        acc = 0
        for j, v in enumerate(vals):
            val = v[i]
            if not val:
                continue
            if horiz:
                slot = ph / n
                by = py + i * slot + slot * .2
                x0 = px + pw * acc / vmax
                x1 = px + pw * (acc + val) / vmax
                dr.rectangle([x0, by, x1, by + slot * .6], fill=rgb(cols[j]))
                dr.text((x1 + 6, by + slot * .3), f"{val:g}", fill=(60, 60, 60), font=f, anchor="lm")
            else:
                slot = pw / n
                bx = px + i * slot + slot * .2
                y1 = py + ph - ph * acc / vmax
                y0 = py + ph - ph * (acc + val) / vmax
                dr.rectangle([bx, y0, bx + slot * .6, y1], fill=rgb(cols[j]))
                dr.text((bx + slot * .3, y0 - 4), f"{val:g}", fill=(60, 60, 60), font=f, anchor="md")
            acc += val if stacked else 0
        if horiz:
            dr.text((px - 8, py + i * (ph / n) + (ph / n) / 2), str(c), fill=(60, 60, 60), font=f, anchor="rm")
        else:
            for k, part in enumerate(str(c).split("\n")):
                dr.text((px + i * (pw / n) + (pw / n) / 2, py + ph + 8 + k * f.size * 1.2), part,
                        fill=(60, 60, 60), font=f, anchor="mt")


def render(path, outdir, width=1600):
    prs = Presentation(path)
    theme = theme_colors(prs)
    scale = width / (prs.slide_width / EMU_IN)
    H = int(prs.slide_height / EMU_IN * scale)
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    report = []
    for n, slide in enumerate(prs.slides, start=1):
        bgc, bgimg = "FFFFFF", None
        for src in (slide, slide.slide_layout, slide.slide_layout.slide_master):
            blip = src._element.find(".//p:bg/p:bgPr/a:blipFill/a:blip", NS)
            if blip is not None:                       # 배경 그림 (빛 번짐 등)
                import io
                rid = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                bgimg = Image.open(io.BytesIO(src.part.related_part(rid).blob)).convert("RGB").resize((width, H))
                break
            bg = src._element.find(".//p:bg/p:bgPr/a:solidFill", NS)
            if bg is not None:
                bgc = color_of(bg, theme, "FFFFFF"); break
        img = bgimg if bgimg is not None else Image.new("RGB", (width, H), rgb(bgc))
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
            if getattr(sh, "has_chart", False):          # 막대 차트 — 값·범주·색을 읽어 그린다
                draw_bar_chart(dr, sh.chart, (x, y, w, h), scale, theme, problems, label)
                continue
            if getattr(sh, "shape_type", None) == 13:     # PICTURE — 실제 이미지를 그려 배치를 검수한다
                import io
                pic = Image.open(io.BytesIO(sh.image.blob)).convert("RGBA")
                # 잘라 넣기(srcRect)를 반영한다 — sizing cover 로 넣은 화면 캡처
                src = el.find(".//a:srcRect", NS)
                if src is not None:
                    W0, H0 = pic.size
                    l, t, r, b = (int(src.get(k, 0)) / 100000 for k in ("l", "t", "r", "b"))
                    pic = pic.crop((int(W0 * l), int(H0 * t), int(W0 * (1 - r)), int(H0 * (1 - b))))
                pic = pic.resize((max(1, int(w)), max(1, int(h))))
                img.paste(pic, (int(x), int(y)), pic)              # 투명 배경(아이콘)을 살린다
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
            elif g == "line" and lcol:
                xfrm = el.find(".//a:xfrm", NS)
                fh, fv = xfrm is not None and xfrm.get("flipH") == "1", xfrm is not None and xfrm.get("flipV") == "1"
                x0, x1 = (x + w, x) if fh else (x, x + w)
                y0, y1 = (y + h, y) if fv else (y, y + h)
                dr.line([x0, y0, x1, y1], fill=rgb(lcol), width=max(2, lw))
            elif g in ("rightArrow", "chevron", "triangle") and fill:
                if g == "rightArrow":
                    pts = [(x, y + h * .25), (x + w * .6, y + h * .25), (x + w * .6, y), (x + w, y + h / 2),
                           (x + w * .6, y + h), (x + w * .6, y + h * .75), (x, y + h * .75)]
                elif g == "chevron":
                    pts = [(x, y), (x + w * .7, y), (x + w, y + h / 2), (x + w * .7, y + h), (x, y + h), (x + w * .3, y + h / 2)]
                else:
                    pts = [(x + w / 2, y), (x + w, y + h), (x, y + h)]
                dr.polygon(pts, fill=rgb(fill))
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
