"""Tier E — 실제 공정 데이터 + 실제 용접부 사진 + 외부 판정. 사진 루프의 효과를 잰다.

Tier D 가 실패한 이유(eval/RESULTS_TIER_D.md)를 하나씩 막는다.
  ① 설계자가 정한 가설을 Agent 가 떠올리지 않았다
       → 정답이 '날림(expulsion) 발생 / 정상 용접' 이다. 용접 품질 판정에서 Agent 가 가장 먼저
         떠올리는 범주이고, 설계자가 고른 메커니즘이 아니다
  ② 공개 사진이 '이 설비의 사진' 이 아니었다
       → 사진이 **그 용접 자체**를 찍은 것이다 (데이터셋 제공자가 용접마다 촬영)
  ③ 지표 정의가 잘못됐다
       → 정답 일치(M1)만 본다. 대조군은 '사진 없음' 과 '반대 판정 용접의 사진(바꿔치기)'

데이터: scripts/04_fetch_rsw_insights.py — Dominguez Molina, Mendeley Data V3 (CC BY 4.0).
용접 495회, 분류 Good 441 / Explode 31 / Bad 21 (데이터셋 제공자의 분류 — 기준은 공개되지 않았다.
날림의 인장강도는 정상과 비슷하므로 강도 미달 판정이 아니다. RESULTS_TIER_E.md '판정 기준' 참고).

**센서로는 갈리지 않는가** — 공정 신호·설정값만으로 분류기(랜덤포레스트, 5-fold)를 학습하면
Explode 재현율 26% · 정밀도 22% (scripts/92_tier_e_sensor_only.py). 같은 설정값에서도 대부분
정상이고 일부만 날린다. Bad 는 설정값으로 81% 식별되므로 이 Tier 에서 제외한다.

사건: Explode 31건 각각에 **같은 설정값의 Good 1건**을 짝지어 62건. Agent 에게는 설정값과
전류·가압력 샘플, 같은 설정값 모집단의 분포만 준다. 인장강도·너깃 지름은 용접 결과(정답 쪽 정보)이므로 주지 않는다.
"""
from __future__ import annotations

import json
import random
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "external" / "rsw_insights"
PHOTO_DIR = ROOT / "data" / "photos" / "tier_e"
CASES_PATH = Path(__file__).resolve().parent / "cases" / "tier_e.jsonl"

TRUTH = {
    "Explode": "날림(expulsion) 결함이다. 용접 중 녹은 금속이 접합부 밖으로 튀어나가 용접부 중심이 "
               "찢기거나 패였다. 정상 용접이 아니다.",
    "Good": "정상 용접이다. 날림(expulsion)이나 용융 부족 같은 결함이 없다.",
}
TRUTH_KEY = {"Explode": "날림 발생", "Good": "정상 용접"}

SETPOINT = ["Pressure (PSI)", "Welding Time (ms)", "Angle (Deg)"]
# Agent 가 사진을 요청할 때 이 단어 중 하나가 대상에 있으면 '용접부를 찍어 달라' 는 요청으로 본다
WELD_WORDS = ("weld", "nugget", "spot", "coupon", "joint", "sheet", "surface", "workpiece",
              "specimen", "sample", "plate", "용접", "너깃", "시편")

# 뒷면 사진 (2026-11-20, 방향 A): 작업자는 시편의 어느 면이든 찍을 수 있다.
# Agent 의 요청 대상·촬영 방법에 이 말이 있으면 뒷면을, 양면을 말하면 둘 다 준다.
BACK_WORDS = ("back", "reverse", "underside", "bottom", "rear", "other side", "opposite side",
              "opposite face", "other face", "far side", "flip", "turn over", "뒷면", "반대면", "뒤집")
BOTH_WORDS = ("both sides", "both faces", "each side", "each face", "front and back",
              "both surfaces", "two faces", "two sides", "양면", "앞뒤", "앞면과 뒷면")


def back_of(path: str | None) -> str | None:
    """앞면 사진 경로(RGB_<id>F.jpg) → 같은 용접의 뒷면 사진 경로(RGB_<id>B.jpg)."""
    return path[:-5] + "B.jpg" if path and path.endswith("F.jpg") else None


# 한국어 요청 (2026-11-22, 웹·시연의 한국어 출력): "윗면과 반대면 두 면 모두" 처럼 앞·뒤를 함께 말하면 양면이다.
# 이전 규칙은 '반대면' 만 보고 뒷면 한 장만 줬다. 영어 규칙은 바꾸지 않는다 (run #84 재현).
KO_FRONT = ("앞면", "윗면", "상면", "위쪽 면", "위쪽면", "전극 접촉면", "전극 쪽", "상판")
KO_BACK = ("뒷면", "아랫면", "아래면", "아래쪽 면", "아래쪽면", "반대면", "반대쪽 면", "반대쪽면", "이면", "하판")
KO_BOTH = ("두 면", "양쪽 면", "양쪽면", "양면", "앞뒤", "위아래", "상면과 하면")


def requested_sides(r: dict) -> list[str]:
    """촬영 요청이 원하는 면. 'F'(앞면, 기본) · 'B'(뒷면)."""
    t = f"{r.get('target', '')} {r.get('how_to_shoot', '')}".lower()
    if any(w in t for w in BOTH_WORDS) or any(w in t for w in KO_BOTH):
        return ["F", "B"]
    if any(w in t for w in KO_FRONT) and any(w in t for w in KO_BACK):
        return ["F", "B"]
    return ["B"] if any(w in t for w in BACK_WORDS) else ["F"]


@dataclass
class TierECase:
    case_id: str
    sample_id: int
    label: str                # Explode | Good (데이터셋 판정)
    truth: str
    truth_key: str
    photo: str                # 이 용접의 앞면 사진
    swap_photo: str           # 반대 판정, 가능하면 같은 설정값인 다른 용접의 사진
    swap_sample_id: int
    cooccurrence: dict        # Agent 입력 (설정값 · 샘플 · 같은 설정값 모집단)
    # ③ 기준 사진 (2026-11-19): 같은 설정값의 정상 용접 — 사건·바꿔치기에 쓰지 않은 것 중에서
    reference_photo: str | None = None
    reference_sample_id: int | None = None
    reference_same_setpoint: bool | None = None
    kind: str = "weld_quality"
    tier: str = "E"
    alarm_count: int = 1
    window_start: str = ""
    window_end: str = ""
    alarm_sample: list = field(default_factory=list)
    data_ref: str | None = None
    source: str = ("Dominguez Molina, RSW Insights, Mendeley Data V3 (CC BY 4.0) — "
                   "실제 용접 · 실제 사진 · 제공자 판정")

    def to_dict(self) -> dict:
        return asdict(self)


def load_raw() -> pd.DataFrame:
    d = pd.read_csv(SRC / "Data_RSW.csv", encoding="utf-8-sig")
    d["Comments"] = d["Comments"].fillna("")
    return d


def _welds(d: pd.DataFrame) -> pd.DataFrame:
    """용접 1회 = 1행. 샘플 열은 리스트로 묶는다."""
    g = d.groupby("Sample ID", sort=True)
    w = g.agg(**{c: (c, "first") for c in SETPOINT + ["Thickness A (mm)", "Thickness B (mm)",
                                                     "Material", "Category", "Comments"]})
    w["current"] = g["Current (A)"].apply(list)
    w["force"] = g["Force (N)"].apply(list)
    w["i_peak"] = g["Current (A)"].max()
    w["i_mean"] = g["Current (A)"].mean()
    w["f_peak"] = g["Force (N)"].max()
    w["n_samples"] = g.size()
    return w


def _record(w: pd.DataFrame, sid: int) -> dict:
    """Agent 가 보는 것. 판정·인장강도·너깃 지름은 없다."""
    r = w.loc[sid]
    same = w[(w[SETPOINT] == r[SETPOINT]).all(axis=1) & (w.index != sid)]

    def dist(col: str) -> dict:
        s = same[col]
        return {"median": round(float(s.median()), 1), "p10": round(float(s.quantile(.1)), 1),
                "p90": round(float(s.quantile(.9)), 1)} if len(s) else {}

    return {
        "machine": "RSW-LAB (laboratory pedestal spot welder) — not RSW-01",
        "material": r["Material"],
        "setpoints": {"air_pressure_psi": float(r[SETPOINT[0]]),
                      "weld_time_ms": float(r[SETPOINT[1]]),
                      "electrode_angle_deg": float(r[SETPOINT[2]]),
                      "thickness_mm": [float(r["Thickness A (mm)"]), float(r["Thickness B (mm)"])]},
        "logged_during_weld": {
            "current_A": [round(float(x), 1) for x in r["current"]],
            "electrode_force_N": [round(float(x), 2) for x in r["force"]],
            "peak_current_A": round(float(r["i_peak"]), 1),
            "mean_current_A": round(float(r["i_mean"]), 1),
            "peak_force_N": round(float(r["f_peak"]), 2)},
        "same_setpoint_population": {"n_welds": int(len(same)),
                                     "peak_current_A": dist("i_peak"),
                                     "mean_current_A": dist("i_mean"),
                                     "peak_force_N": dist("f_peak")},
    }


def build(seed: int = 0) -> list[TierECase]:
    w = _welds(load_raw())
    w = w[w["Comments"] != "Communication error"]
    rgb = SRC / "rgb"
    has_photo = {sid for sid in w.index if (rgb / f"RGB_{sid}F.jpg").exists()}
    w = w[w.index.isin(has_photo)]
    rnd = random.Random(seed)

    explode = [int(s) for s in w.index[w["Category"] == "Explode"]]
    good_pool = w[(w["Category"] == "Good") & (w["Comments"] == "")]
    used: set[int] = set()
    pairs = []
    for sid in explode:
        same = good_pool[(good_pool[SETPOINT] == w.loc[sid, SETPOINT]).all(axis=1)]
        cands = [int(s) for s in same.index if int(s) not in used]
        if not cands:   # 같은 설정값의 정상 용접이 없으면 전체에서
            cands = [int(s) for s in good_pool.index if int(s) not in used]
        g = rnd.choice(cands)
        used.add(g)
        pairs.append((sid, g))

    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for ex, gd in pairs:
        for sid, label, other in ((ex, "Explode", gd), (gd, "Good", ex)):
            for s in (sid, other):
                for side in "FB":
                    dst = PHOTO_DIR / f"RGB_{s}{side}.jpg"
                    if not dst.exists():
                        shutil.copy(rgb / f"RGB_{s}{side}.jpg", dst)
            out.append(TierECase(
                case_id=f"E-{sid}", sample_id=sid, label=label, truth=TRUTH[label],
                truth_key=TRUTH_KEY[label],
                photo=f"data/photos/tier_e/RGB_{sid}F.jpg",
                swap_photo=f"data/photos/tier_e/RGB_{other}F.jpg", swap_sample_id=other,
                cooccurrence=_record(w, sid)))
    rnd.shuffle(out)
    return out


def attach_references(cases: list[TierECase]) -> list[TierECase]:
    """사건마다 '정상 샘플' 기준 사진을 붙인다 — 실제 공장의 골든 샘플에 해당한다.

    후보: 판정 Good · 비고 없음 · **62건의 사건과 바꿔치기 사진에 쓰지 않은** 용접.
    같은 설정값이 있으면 그중 번호가 가장 작은 것, 없으면(DOE 설정 5건) 설정값이 가장 가까운 것.
    판정 라벨을 쓰는 단계다 — 라벨 없이 쓰는 Agent 조건과 구분해 보고한다.
    """
    w = _welds(load_raw())
    w = w[w["Comments"] != "Communication error"]
    used = {c.sample_id for c in cases} | {c.swap_sample_id for c in cases}
    gold = w[(w["Category"] == "Good") & (w["Comments"] == "") & (~w.index.isin(used))]
    gold = gold[[(SRC / "rgb" / f"RGB_{i}F.jpg").exists() for i in gold.index]]
    scale = gold[SETPOINT].std().replace(0, 1)
    (PHOTO_DIR / "ref").mkdir(parents=True, exist_ok=True)
    for c in cases:
        sp = w.loc[c.sample_id, SETPOINT]
        same = gold[(gold[SETPOINT] == sp).all(axis=1)]
        if len(same):
            gid, ok = int(sorted(same.index)[0]), True
        else:
            dist = (((gold[SETPOINT] - sp) / scale) ** 2).sum(axis=1)
            gid, ok = int(dist.idxmin()), False
        for side in "FB":
            dst = PHOTO_DIR / "ref" / f"RGB_{gid}{side}.jpg"
            if not dst.exists():
                shutil.copy(SRC / "rgb" / f"RGB_{gid}{side}.jpg", dst)
        c.reference_photo = f"data/photos/tier_e/ref/RGB_{gid}F.jpg"
        c.reference_sample_id, c.reference_same_setpoint = gid, ok
    return cases


def save(cases: list[TierECase]) -> Path:
    CASES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CASES_PATH, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
    return CASES_PATH


def load() -> list[TierECase]:
    return [TierECase(**json.loads(ln)) for ln in open(CASES_PATH, encoding="utf-8")]


if __name__ == "__main__":
    import sys
    if "--copy-back-photos" in sys.argv:            # 기존 사건은 그대로 두고 뒷면 사진만 복사
        n = 0
        for c in load():
            for f in (c.photo, c.swap_photo, c.reference_photo):
                b = back_of(f)
                if b and not (ROOT / b).exists():
                    shutil.copy(SRC / "rgb" / Path(b).name, ROOT / b)
                    n += 1
        print(f"뒷면 사진 {n}장 복사")
        raise SystemExit
    if "--attach-references" in sys.argv:          # 기존 사건은 그대로 두고 기준 사진만 붙인다
        cs = attach_references(load())
        save(cs)
        print(f"기준 사진 {sum(1 for c in cs if c.reference_photo)}건 · 같은 설정값 "
              f"{sum(1 for c in cs if c.reference_same_setpoint)}건")
        raise SystemExit
    cs = build()
    p = save(cs)
    from collections import Counter
    print(f"Tier E {len(cs)}건 {dict(Counter(c.label for c in cs))} → {p}")
    same = sum(1 for c in cs if c.cooccurrence["same_setpoint_population"]["n_welds"] > 0)
    print(f"같은 설정값 모집단이 있는 사건 {same}/{len(cs)}")
