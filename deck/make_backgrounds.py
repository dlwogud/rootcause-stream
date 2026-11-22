"""발표자료 배경 그림 — 어두운 바탕 + 빛 번짐(주황 · 보라) + 은은한 격자, 그리고 큰 숫자 뒤에 까는 빛.

PowerPoint 는 방사형 그라데이션을 pptxgenjs 로 만들 수 없어 그림으로 만든다.
참고 디자인 (Behance 2026-11-22): Cybersecurity(빛 번짐) · ECO Mine · Orbit(어두운 바탕) · ORYN(격자)
사용: .venv/bin/python deck/make_backgrounds.py → deck/assets/bg_*.png, glow_*.png
"""
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parent / "assets"
W, H = 2560, 1440
BASE = np.array([14, 17, 22], float)          # 0E1116


def radial(cx, cy, r, color, alpha):
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - cx * W) / (r * W)) ** 2 + ((y - cy * H) / (r * W)) ** 2)
    a = np.clip(1 - d, 0, 1) ** 2.2 * alpha
    return a[..., None] * (np.array(color, float) - BASE)


def background(name, o_alpha, p_alpha, grid=True):
    img = np.tile(BASE, (H, W, 1))
    img += radial(0.10, -0.10, 0.62, (255, 106, 43), o_alpha)
    img += radial(1.02, 1.10, 0.55, (109, 93, 246), p_alpha)
    if grid:
        step = 64
        img[::step, :, :] += 7
        img[:, ::step, :] += 7
    Image.fromarray(np.clip(img, 0, 255).astype("uint8")).save(OUT / name, optimize=True)


def glow(name, color, size=900):
    y, x = np.mgrid[0:size, 0:size]
    d = np.sqrt((x - size / 2) ** 2 + (y - size / 2) ** 2) / (size / 2)
    a = (np.clip(1 - d, 0, 1) ** 2.4 * 200).astype("uint8")
    rgba = np.zeros((size, size, 4), "uint8"); rgba[..., :3] = color; rgba[..., 3] = a
    Image.fromarray(rgba, "RGBA").save(OUT / name, optimize=True)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    background("bg_content.png", 0.20, 0.16)
    background("bg_cover.png", 0.42, 0.26)
    glow("glow_orange.png", (255, 106, 43))
    glow("glow_purple.png", (109, 93, 246))
    for f in sorted(OUT.glob("bg_*.png")) + sorted(OUT.glob("glow_*.png")):
        print(f.name, f"{f.stat().st_size / 1024:.0f} KB")
