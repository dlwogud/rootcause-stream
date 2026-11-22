"""Tier E 데이터 — 공개 RSW 데이터셋(공정 신호 + 실제 용접부 사진 + 제공자 분류)을 받는다.

출처: L. A. Dominguez Molina, "Resistance Spot Welding Insights: A Dataset Integrating
Process Parameters, Infrared, and Surface Imaging", Mendeley Data, V3, 2025.
DOI 10.17632/rwh8kjzdch.3 · 라이선스 CC BY 4.0 (출처 표시 시 재배포 가능)

받는 것: Data_RSW.csv(용접 495회의 설정값·전류/가압력 샘플·인장강도·너깃 지름·분류)와 앞면 RGB 사진.
→ data/external/rsw_insights/ (전체, git 제외) — 사건에 쓰는 사진만 data/photos/tier_e/ 로 복사해 커밋

사용: .venv/bin/python scripts/04_fetch_rsw_insights.py [--workers 8]
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "external" / "rsw_insights"
API = "https://data.mendeley.com/public-api/datasets/rwh8kjzdch"
VERSION = 3
UA = {"User-Agent": "Mozilla/5.0"}


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def listing(folder: str = "root") -> list[dict]:
    return json.loads(get(f"{API}/files?folder_id={folder}&version={VERSION}"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    (OUT / "rgb").mkdir(parents=True, exist_ok=True)

    for f in listing():
        if f["filename"] == "Data_RSW.csv":
            (OUT / "Data_RSW.csv").write_bytes(get(f["content_details"]["download_url"]))
    folders = {x["name"]: x["id"] for x in json.loads(get(f"{API}/folders/{VERSION}"))}
    rgb = [f for f in listing(folders["Images_RGB"]) if f["filename"].endswith("F.jpg")]

    def fetch(f: dict) -> None:
        p = OUT / "rgb" / f["filename"]
        if not p.exists() or p.stat().st_size != f["size"]:
            p.write_bytes(get(f["content_details"]["download_url"]))

    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(fetch, rgb))
    print(f"→ {OUT}  CSV + 앞면 사진 {len(rgb)}장")


if __name__ == "__main__":
    main()
