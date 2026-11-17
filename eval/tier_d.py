"""Tier D — 시각 정보가 결정적인 사건.

⚠️ **합성 케이스다.** 2020년 공정 데이터에는 사진이 존재하지 않으므로(그 공장에서
아무도 찍지 않았다), 사진 단계를 실제 사건으로 측정할 방법이 없다. 그래서
**시각 정보에만 답이 있는 사건을 구성해서** 사진 루프의 능력만 따로 측정한다.
Tier B 와 같은 원칙으로, 성과표에서 항상 '구성된 사건' 으로 표기한다.

측정 주장은 두 개이고 둘 다 좁다.
  (1) 가설이 센서로 갈리지 않을 때, Agent 가 **가르는 사진**을 요청하는가
  (2) 그 사진이 무작위 사진보다 가설 불확실성을 더 줄이는가 (정보이득)

사건 설계 원칙: 센서가 보는 신호는 두 가설을 **똑같이 잘 설명**해야 한다.
그래야 사진 없이는 원리적으로 못 가르고, 사진의 기여가 측정된다.

판독 과제는 스파이크(spike/RESULTS.md)에서 자기일관성이 확인된 것만 쓴다 —
이상징후 유무(91.7%), 에러코드 유무(100%), 경고등 점등(대상 명확 시 100%).
게이지 수치/구간 판독(50%)은 쓰지 않는다.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

CASES_DIR = Path(__file__).resolve().parent / "cases"
PHOTO_ROOT = Path(__file__).resolve().parents[1] / "data" / "photos"


@dataclass
class PhotoOption:
    """사건에 준비된 사진 한 장."""
    key: str                  # 'electrode_tip' 등 — Agent 요청과 매칭하는 키
    path: str
    shows: str                # 이 사진에 실제로 무엇이 보이는가 (판독 정답)
    discriminating: bool      # 이 사진이 가설을 가르는가
    aliases: list = field(default_factory=list)   # 요청 매칭용 동의어


@dataclass
class TierDCase:
    case_id: str
    kind: str                 # burst | level_shift
    truth: str
    truth_key: str
    sensor_story: str         # 센서가 보는 것 (두 가설을 똑같이 설명한다)
    hypotheses_expected: list
    photos: list              # [PhotoOption]
    alarm_count: int = 0
    window_start: str = ""
    window_end: str = ""
    cooccurrence: dict = field(default_factory=dict)
    alarm_sample: list = field(default_factory=list)
    tier: str = "D"
    source: str = "본 프로젝트가 구성 — 합성 사건 (시각 정보가 결정적)"
    data_ref: str | None = None
    injected: str | None = None

    def photo_for(self, request_target: str) -> PhotoOption | None:
        """Agent 가 요청한 대상에 맞는 사진을 고른다. 못 맞히면 None(= 무관한 사진)."""
        t = (request_target or "").lower()
        for p in self.photos:
            keys = [p.key] + list(p.aliases)
            if any(k.lower() in t for k in keys):
                return p
        return None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["photos"] = [asdict(p) if not isinstance(p, dict) else p for p in self.photos]
        return d


def save(cases: list[TierDCase], path: Path | None = None) -> Path:
    p = path or (CASES_DIR / "tier_d.jsonl")
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
    return p


def load(path: Path | None = None) -> list[TierDCase]:
    p = path or (CASES_DIR / "tier_d.jsonl")
    out = []
    for line in open(p, encoding="utf-8"):
        d = json.loads(line)
        d["photos"] = [PhotoOption(**x) for x in d["photos"]]
        out.append(TierDCase(**d))
    return out


# ── 정보이득 ───────────────────────────────────────────────────
def entropy(scores: list[float]) -> float:
    """가설 점수 분포의 섀넌 엔트로피(bit). 점수를 정규화해 쓴다."""
    import math
    s = [max(float(x), 1e-12) for x in scores]
    tot = sum(s)
    p = [x / tot for x in s]
    return -sum(x * math.log2(x) for x in p if x > 0)


def information_gain(before: list[dict], after: list[dict]) -> dict:
    """사진 전후 가설 불확실성 감소량(bit).

    가설 집합이 달라질 수 있으므로 **공통 가설 id 기준**으로 비교한다.
    새로 생긴 가설까지 포함하면 '가설을 늘려서 엔트로피를 키운 뒤 줄인' 것처럼 보인다.
    """
    b = {h["id"]: h["score"] for h in before}
    a = {h["id"]: h["score"] for h in after}
    common = [k for k in b if k in a]
    if len(common) < 2:
        return {"h_before": None, "h_after": None, "information_gain": None,
                "n_common": len(common)}
    hb, ha = entropy([b[k] for k in common]), entropy([a[k] for k in common])
    return {"h_before": round(hb, 4), "h_after": round(ha, 4),
            "information_gain": round(hb - ha, 4), "n_common": len(common)}
