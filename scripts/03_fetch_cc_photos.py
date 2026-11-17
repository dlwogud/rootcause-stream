#!/usr/bin/env python3
"""Wikimedia Commons에서 판독 스파이크용 이미지를 라이선스 확인 후 수집한다.

레포에 커밋 가능한 것만 받는다 (CC / Public domain).
결과: data/photos/public/<task>/<file>  +  MANIFEST.csv (출처·저작자·라이선스)

사용: python3 scripts/03_fetch_cc_photos.py [--per-cat 12]
"""
from __future__ import annotations
import argparse, csv, json, re, sys, time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://commons.wikimedia.org/w/api.php"
UA = "RootCauseStream-research/0.1 (university project; contact via repo)"

# 판독 과제 4종 ← docs/04-llm-techniques.md 의 분류
TASKS: dict[str, list[str]] = {
    # ③ 게이지 구간 판정
    "gauge_zone": [
        "Category:Bourdon gauge",
        "Category:Manometers",
        "Category:Pressure gauges",
    ],
    # ① 디지털 표시기 · 에러코드 문자 판독
    "digital_readout": [
        "Category:Digital clocks",
        "Category:LED displays",
        "Category:Multimeters",
        "Category:Gas meters",
        "Category:Water meters",
        "Category:Digital thermometers",
    ],
    # ② 상태 표시등 색 분류
    "indicator_light": [
        "Category:Light-emitting diodes",
        "Category:Push buttons",
        "Category:Control panels",
        "Category:Switchgear",
        "Category:Circuit breakers",
    ],
    # ④ 정성 이상 판정 (마모·부식·균열·파손)
    "qualitative_fault": [
        "Category:Corrosion",
        "Category:Rust",
        "Category:Cracks",
        "Category:Broken machinery",
    ],
    # ⑤ 도메인 사진 — Tier D(시각 정보가 결정적인 사건) 재료.
    #    앞의 4종은 판독 '능력' 측정용이고, 이것은 '용접 설비처럼 보이는' 사진이
    #    필요해서 따로 모은다. 범용 사진으로 설비 점검을 시연하면 설득되지 않는다.
    "welding_equipment": [
        "Category:Resistance welding",
        "Category:Spot welding",
        "Category:Welding electrodes",
        "Category:Welding machines",
    ],
    "pipe_condition": [
        "Category:Rusty pipes",
        "Category:Pipelines",
    ],
}

ALLOW = re.compile(r"\b(cc[ -]?(by|zero|0)|public domain|pd[ -]|cc0)", re.I)
BAD_EXT = {".svg", ".tif", ".tiff", ".pdf", ".webm", ".ogv", ".gif"}


def _get(url: str, timeout: int = 30, tries: int = 5) -> bytes:
    """429/일시 오류에 지수 백오프로 재시도한다."""
    import urllib.error
    for i in range(tries):
        try:
            with urlopen(Request(url, headers={"User-Agent": UA}), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < tries - 1:
                time.sleep(3 * (i + 1))
                continue
            raise
        except Exception:
            if i < tries - 1:
                time.sleep(2 * (i + 1))
                continue
            raise
    raise RuntimeError("retries exhausted")


def api(params: dict) -> dict:
    params = {**params, "format": "json", "formatversion": "2"}
    return json.loads(_get(f"{API}?{urlencode(params)}"))


def category_files(cat: str, limit: int) -> list[str]:
    out, cont = [], None
    while len(out) < limit:
        p = {"action": "query", "list": "categorymembers", "cmtitle": cat,
             "cmtype": "file", "cmlimit": "50"}
        if cont:
            p["cmcontinue"] = cont
        d = api(p)
        out += [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
        cont = d.get("continue", {}).get("cmcontinue")
        if not cont:
            break
    return out[: limit * 3]  # 라이선스 필터로 줄어들 것을 감안해 넉넉히


def image_meta(titles: list[str]) -> list[dict]:
    rows = []
    for i in range(0, len(titles), 20):
        d = api({"action": "query", "titles": "|".join(titles[i:i + 20]),
                 "prop": "imageinfo",
                 "iiprop": "url|extmetadata|mime|size",
                 "iiurlwidth": "1280"})
        for pg in d.get("query", {}).get("pages", []):
            ii = (pg.get("imageinfo") or [{}])[0]
            em = ii.get("extmetadata", {})
            rows.append({
                "title": pg.get("title", ""),
                "url": ii.get("thumburl") or ii.get("url", ""),
                "descurl": ii.get("descriptionurl", ""),
                "mime": ii.get("mime", ""),
                "license": (em.get("LicenseShortName", {}) or {}).get("value", ""),
                "artist": re.sub(r"<[^>]+>", "", (em.get("Artist", {}) or {}).get("value", ""))[:120],
            })
        time.sleep(0.6)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-cat", type=int, default=12)
    ap.add_argument("--out", default="data/photos/public")
    a = ap.parse_args()

    root = Path(a.out)
    root.mkdir(parents=True, exist_ok=True)
    manifest, n_ok, n_skip = [], 0, 0

    for task, cats in TASKS.items():
        (root / task).mkdir(exist_ok=True)
        for cat in cats:
            try:
                titles = category_files(cat, a.per_cat)
            except Exception as e:
                print(f"  ! {cat}: {e}", file=sys.stderr)
                continue
            got = 0
            for m in image_meta(titles):
                if got >= a.per_cat:
                    break
                name = m["title"].removeprefix("File:")
                if Path(name).suffix.lower() in BAD_EXT or not m["url"]:
                    continue
                if not ALLOW.search(m["license"]):
                    n_skip += 1
                    continue
                safe = re.sub(r"[^\w.\-]+", "_", name)[:90]
                dest = root / task / safe
                if not dest.exists():
                    try:
                        dest.write_bytes(_get(m["url"], timeout=60))
                        time.sleep(0.4)
                    except Exception as e:
                        print(f"  ! {name}: {e}", file=sys.stderr)
                        continue
                manifest.append({"task": task, "file": str(dest.relative_to(root)),
                                 "category": cat, "license": m["license"],
                                 "artist": m["artist"], "source": m["descurl"]})
                got += 1
                n_ok += 1
            print(f"  {task:18s} {cat:40s} {got:2d}장")

    with open(root / "MANIFEST.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["task", "file", "category", "license", "artist", "source"])
        w.writeheader()
        w.writerows(manifest)

    print(f"\n수집 {n_ok}장 · 라이선스 미달 제외 {n_skip}건 · MANIFEST.csv 작성")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
