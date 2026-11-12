#!/usr/bin/env python3
"""D1 스파이크 — VLM 사진 판독 능력 측정.

docs/04-llm-techniques.md 의 판독 과제 4종이 실제로 가능한지 재고, 그 결과로
설계 범위를 확정한다. 버리는 코드지만 결과(spike/out/)는 남긴다.

측정하는 것
  1) 과제별 판독 정확도      ← review.html 에서 사람이 라벨링 후 계산
  2) 자기일관성(self-consistency)  ← 같은 이미지 N회 반복 시 일치율
  3) 신뢰도 신호의 타당성    ← confidence 와 실제 정답의 상관
  4) 블러 열화 민감도        ← --blur 옵션
  5) 모델별 비교             ← --model 로 haiku/sonnet 각각 실행

주의: Commons 카테고리에는 과제와 무관한 사진이 섞여 있다(예: gauge_zone 에 커피머신).
스키마의 `*_present` 필드와 리뷰의 '해당없음' 판정으로 걸러지며, 정확도 분모에서 제외된다.

배경: arXiv 2608.17723 (Vision-Language Models for Analog Gauge Reading)은
zero-shot VLM의 아날로그 게이지 '수치' 판독이 평균 21~39% 오차로 실용 불가이고,
±5% full-scale 허용에서는 79~96%가 통과하지만 ±1%에서는 19~44%로 급락한다고
보고한다. 또한 confidence >= 0.99 에서도 오답이 발생한다. 그래서 이 스파이크는
'수치 환산'이 아니라 '구간/범주 판정'만 측정한다.

사용:
  export ANTHROPIC_API_KEY=sk-...
  python3 spike/vlm_reading_spike.py --repeats 3
  python3 spike/vlm_reading_spike.py --model claude-sonnet-5 --tag sonnet
  open spike/out/review.html     # 사람이 정답 라벨링 → CSV 내려받기
  python3 spike/vlm_reading_spike.py --score spike/out/labels.csv
"""
from __future__ import annotations
import argparse, base64, csv, io, json, os, sys, time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "spike" / ".." / "data" / "photos" / "public"
OUT = ROOT / "spike" / "out"

PRICES = {  # USD / 1M tokens  (2026-06)
    "claude-opus-5":   (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
}

COMMON = {
    "readable":          {"type": "boolean"},
    "unreadable_reason": {"type": ["string", "null"],
                          "description": "판독 불가 사유. blur/occlusion/too_small/not_applicable 등. 판독 가능하면 null"},
    "confidence":        {"type": "string", "enum": ["low", "medium", "high"]},
}

TASKS: dict[str, dict] = {
    # ③ 게이지 구간 판정 — 수치 환산이 아니라 눈금 대비 위치 구간
    "gauge_zone": {
        "instruction": (
            "이 사진에 아날로그 게이지(다이얼형 계기)가 있는지 보고, 있다면 바늘이 "
            "전체 눈금(full scale)의 어느 구간을 가리키는지 4분위로 판정하라. "
            "정확한 수치를 환산하지 말고 구간만 답하라. "
            "컬러 밴드(녹/황/적)가 있으면 바늘이 어느 밴드에 있는지도 답하라."
        ),
        "schema": {**COMMON,
            "gauge_present":  {"type": "boolean"},
            "needle_visible": {"type": "boolean"},
            "quartile":       {"type": "string", "enum": ["0-25", "25-50", "50-75", "75-100", "unknown"]},
            "color_band":     {"type": "string", "enum": ["green", "yellow", "red", "none", "unknown"]},
        },
        "key": "quartile",
    },
    # ① 디지털 표시기 · 에러코드 문자 판독
    "digital_readout": {
        "instruction": (
            "이 사진에 디지털 표시기(7세그먼트, LCD, LED 등)가 있으면 화면에 표시된 "
            "문자/숫자를 그대로 옮겨 적어라. 추측하지 말고 보이는 대로만 적는다. "
            "에러코드처럼 보이는 것이 있으면 따로 표시하라."
        ),
        "schema": {**COMMON,
            "display_present": {"type": "boolean"},
            "displayed_text":  {"type": "string", "description": "보이는 그대로. 없으면 빈 문자열"},
            "is_error_code":   {"type": "boolean"},
        },
        "key": "displayed_text",
    },
    # ② 상태 표시등 색 분류
    "indicator_light": {
        "instruction": (
            "이 사진에 상태 표시등(파일럿 램프, LED, 표시 버튼)이 있으면 점등된 것의 "
            "색을 분류하라. 점등/소등을 구분하고, 점등된 것이 여러 개면 가장 두드러진 색을 "
            "dominant_color 로 답하라."
        ),
        "schema": {**COMMON,
            "lamp_present":   {"type": "boolean"},
            "any_lit":        {"type": "boolean"},
            "dominant_color": {"type": "string",
                               "enum": ["red", "green", "yellow", "blue", "white", "other", "none"]},
            "lit_count":      {"type": "integer"},
        },
        "key": "dominant_color",
    },
    # ④ 정성 이상 판정
    "qualitative_fault": {
        "instruction": (
            "이 사진에서 설비 이상 징후(부식, 녹, 균열, 마모, 누유/누수, 변형, 파손)가 "
            "보이는지 판정하라. 보이면 유형과 정도를 답하라. 추측하지 말고 사진에서 "
            "실제로 확인되는 것만 답한다."
        ),
        "schema": {**COMMON,
            "fault_present": {"type": "boolean"},
            "fault_type":    {"type": "string",
                              "enum": ["corrosion", "crack", "wear", "leak", "deformation", "breakage", "none"]},
            "severity":      {"type": "string", "enum": ["none", "minor", "moderate", "severe"]},
        },
        "key": "fault_type",
    },
}

SYSTEM = (
    "너는 산업 설비 점검 보조 시스템의 사진 판독 모듈이다.\n"
    "규칙:\n"
    "1. 사진에서 실제로 확인되는 것만 답한다. 추론으로 채우지 않는다.\n"
    "2. 판별이 어려우면 readable=false 와 unreadable_reason 을 반환한다. "
    "   틀린 답보다 '판독 불가'가 낫다.\n"
    "3. confidence 는 보수적으로 매긴다. 흐리거나 가려져 있으면 high 를 쓰지 않는다."
)


def encode(p: Path, blur: int = 0) -> tuple[str, str]:
    data = p.read_bytes()
    mt = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}[p.suffix.lower().lstrip(".")]
    if blur:
        try:
            from PIL import Image, ImageFilter
            im = Image.open(io.BytesIO(data)).convert("RGB")
            im = im.filter(ImageFilter.GaussianBlur(radius=blur))
            buf = io.BytesIO(); im.save(buf, format="JPEG", quality=90)
            data, mt = buf.getvalue(), "image/jpeg"
        except ImportError:
            print("  ! Pillow 없음 — 블러 생략 (pip install pillow)", file=sys.stderr)
    return base64.standard_b64encode(data).decode(), mt


def model_params(model: str) -> dict:
    """모델별 thinking 파라미터 분기. Opus5/Sonnet5=effort, Haiku4.5=budget_tokens."""
    if model.startswith(("claude-opus-5", "claude-sonnet-5", "claude-opus-4-")):
        return {"thinking": {"type": "adaptive"}, "output_config_effort": "low"}
    if model.startswith("claude-haiku-4-5"):
        return {"thinking": {"type": "enabled", "budget_tokens": 1024}}
    raise ValueError(f"알 수 없는 모델: {model}")


def call(client, model: str, task: str, img_b64: str, mime: str) -> tuple[dict, dict]:
    spec = TASKS[task]
    mp = model_params(model)
    effort = mp.pop("output_config_effort", None)
    oc = {"format": {"type": "json_schema",
                     "schema": {"type": "object",
                                "properties": spec["schema"],
                                "required": list(spec["schema"].keys()),
                                "additionalProperties": False}}}
    if effort:
        oc["effort"] = effort
    r = client.messages.create(
        model=model, max_tokens=2048, system=SYSTEM,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": mime, "data": img_b64}},
            {"type": "text", "text": spec["instruction"]},
        ]}],
        output_config=oc, **mp,
    )
    text = next(b.text for b in r.content if b.type == "text")
    u = r.usage
    return json.loads(text), {"in": u.input_tokens, "out": u.output_tokens}


def run(a) -> int:
    import anthropic
    client = anthropic.Anthropic()
    OUT.mkdir(parents=True, exist_ok=True)
    rows, tok_in, tok_out, errs = [], 0, 0, 0
    photos_root = (ROOT / "data" / "photos" / "public").resolve()

    for task in (a.tasks or list(TASKS)):
        d = photos_root / task
        files = sorted([f for f in d.glob("*") if f.suffix.lower() in {".jpg", ".jpeg", ".png"}])[: a.limit]
        if not files:
            print(f"  {task}: 이미지 없음 — 건너뜀"); continue
        print(f"\n== {task} — {len(files)}장 × {a.repeats}회 ==")
        for f in files:
            b64, mt = encode(f, a.blur)
            for rep in range(a.repeats):
                try:
                    out, u = call(client, a.model, task, b64, mt)
                    tok_in += u["in"]; tok_out += u["out"]
                except Exception as e:
                    errs += 1; print(f"  ! {f.name} rep{rep}: {type(e).__name__}: {e}", file=sys.stderr)
                    continue
                rows.append({"task": task, "file": f.name, "rep": rep, "model": a.model,
                             "blur": a.blur, **out})
            print(f"  {f.name[:52]:54s} ok")

    tag = a.tag or a.model.replace("claude-", "")
    jp = OUT / f"results_{tag}{'_blur' + str(a.blur) if a.blur else ''}.jsonl"
    with open(jp, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    pin, pout = PRICES.get(a.model, (0, 0))
    cost = tok_in / 1e6 * pin + tok_out / 1e6 * pout
    print(f"\n호출 {len(rows)}건 · 실패 {errs}건")
    print(f"토큰 in {tok_in:,} / out {tok_out:,} · 추정 비용 ${cost:.4f}")
    print(f"→ {jp}")

    consistency(rows)
    write_review(rows, photos_root)
    return 0


def consistency(rows: list[dict]) -> None:
    """같은 이미지를 반복 판독했을 때 핵심 필드가 일치하는 비율."""
    g = defaultdict(list)
    for r in rows:
        g[(r["task"], r["file"])].append(r)
    per = defaultdict(lambda: [0, 0])
    conf_split = defaultdict(lambda: [0, 0])  # confidence → [일관, 전체]
    for (task, _), rs in g.items():
        if len(rs) < 2:
            continue
        key = TASKS[task]["key"]
        vals = [str(r.get(key)) for r in rs]
        agree = len(set(vals)) == 1
        per[task][0] += int(agree); per[task][1] += 1
        c = Counter(r.get("confidence") for r in rs).most_common(1)[0][0]
        conf_split[c][0] += int(agree); conf_split[c][1] += 1
    if not per:
        return
    print("\n=== 자기일관성 (반복 판독 일치율) ===")
    for t, (ok, n) in per.items():
        print(f"  {t:20s} {ok}/{n}  {ok/n*100:5.1f}%")
    print("=== confidence 별 일관성 ===  (높아야 신뢰 가능한 신호)")
    for c, (ok, n) in sorted(conf_split.items()):
        print(f"  {str(c):8s} {ok}/{n}  {ok/n*100:5.1f}%")


def write_review(rows: list[dict], photos_root: Path) -> None:
    """사람이 정답을 매기는 페이지. 라벨은 브라우저에 저장되고 CSV로 내보낸다."""
    first = {}
    for r in rows:
        first.setdefault((r["task"], r["file"]), r)
    items = []
    for (task, fn), r in sorted(first.items()):
        key = TASKS[task]["key"]
        items.append({"task": task, "file": fn,
                      "src": os.path.relpath(photos_root / task / fn, OUT),
                      "pred": str(r.get(key)), "key": key,
                      "readable": r.get("readable"), "conf": r.get("confidence"),
                      "raw": {k: v for k, v in r.items()
                              if k not in {"task", "file", "rep", "model", "blur"}}})
    html = """<!doctype html><meta charset=utf-8><title>VLM 판독 스파이크 리뷰</title>
<style>
body{font:14px system-ui;margin:0;background:#f6f6f4;color:#1a1a18}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid #ddd;padding:12px 20px;display:flex;gap:16px;align-items:center;z-index:9}
button{padding:7px 14px;border:1px solid #999;border-radius:6px;background:#fff;cursor:pointer;font:inherit}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px;padding:18px}
.card{background:#fff;border:1px solid #e2e2de;border-radius:10px;overflow:hidden}
.card img{width:100%;height:210px;object-fit:contain;background:#efefec;display:block}
.m{padding:10px 12px}
.p{font-weight:600;margin:2px 0 8px}
.t{font-size:12px;color:#666}
label{margin-right:12px;cursor:pointer}
details{margin-top:8px;font-size:12px}pre{white-space:pre-wrap;word-break:break-all;background:#f3f3f0;padding:7px;border-radius:5px}
.done{outline:2px solid #2c7}
</style>
<header>
  <strong>VLM 판독 스파이크 리뷰</strong>
  <span id=prog></span>
  <button onclick=dl()>CSV 내려받기</button>
  <span class=t>맞음 / 틀림 / <b>해당없음</b>(대상이 사진에 없음 — 정확도 계산에서 제외)</span>
</header>
<div class=grid id=g></div>
<script>
const items = __ITEMS__;
const S = JSON.parse(localStorage.getItem('vlmspike')||'{}');
const g = document.getElementById('g');
items.forEach((it,i)=>{
  const id = it.task+'/'+it.file;
  const d = document.createElement('div'); d.className='card'; d.id='c'+i;
  d.innerHTML = `<img src="${it.src}" loading=lazy>
  <div class=m>
    <div class=t>${it.task} · readable=${it.readable} · conf=${it.conf}</div>
    <div class=p>${it.key}: ${it.pred}</div>
    <div>
      <label><input type=radio name=r${i} value=1> 맞음</label>
      <label><input type=radio name=r${i} value=0> 틀림</label>
      <label><input type=radio name=r${i} value=x> 해당없음</label>
    </div>
    <details><summary>원본 출력</summary><pre>${JSON.stringify(it.raw,null,1)}</pre></details>
  </div>`;
  g.appendChild(d);
  if(S[id]!==undefined){const el=d.querySelector(`input[value="${S[id]}"]`); if(el){el.checked=true; d.classList.add('done');}}
  d.querySelectorAll('input').forEach(inp=>inp.onchange=()=>{S[id]=inp.value;localStorage.setItem('vlmspike',JSON.stringify(S));d.classList.add('done');prog();});
});
function prog(){document.getElementById('prog').textContent=`${Object.keys(S).length} / ${items.length} 라벨링됨`;}
prog();
function dl(){
  let csv='task,file,key,pred,verdict\\n';
  items.forEach(it=>{const id=it.task+'/'+it.file;
    csv+=[it.task,it.file,it.key,JSON.stringify(it.pred),S[id]??''].join(',')+'\\n';});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='labels.csv'; a.click();
}
</script>"""
    (OUT / "review.html").write_text(html.replace("__ITEMS__", json.dumps(items, ensure_ascii=False)),
                                     encoding="utf-8")
    print(f"→ {OUT/'review.html'}  (브라우저로 열어 라벨링 → labels.csv 내려받기)")


def score(labels_csv: Path) -> int:
    per = defaultdict(lambda: [0, 0, 0])  # task → [맞음, 판정된것, 애매]
    with open(labels_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            v = (row.get("verdict") or "").strip()
            t = row["task"]
            if v == "x":
                per[t][2] += 1  # 대상 부재 — 분모에서 제외
            elif v in ("0", "1"):
                per[t][0] += int(v == "1"); per[t][1] += 1
    print("\n=== 판독 정확도 ===")
    print(f"{'과제':22s} {'정확도':>8s}  {'n':>4s}  해당없음")
    tot_ok = tot_n = 0
    for t, (ok, n, amb) in sorted(per.items()):
        tot_ok += ok; tot_n += n
        print(f"{t:22s} {ok/n*100 if n else 0:7.1f}% {n:5d}  {amb}")
    if tot_n:
        print(f"{'전체':22s} {tot_ok/tot_n*100:7.1f}% {tot_n:5d}")
    print("\n→ 정확도가 낮은 과제는 docs/04-llm-techniques.md 에서 설계 범위 밖으로 옮긴다.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="claude-haiku-4-5")
    p.add_argument("--repeats", type=int, default=3, help="자기일관성 측정용 반복 횟수")
    p.add_argument("--limit", type=int, default=15, help="과제별 이미지 수 상한")
    p.add_argument("--blur", type=int, default=0, help="가우시안 블러 반경 (열화 민감도 테스트)")
    p.add_argument("--tasks", nargs="*", choices=list(TASKS))
    p.add_argument("--tag", default="")
    p.add_argument("--score", type=Path, help="labels.csv 로 정확도 계산만 수행")
    a = p.parse_args()
    if a.score:
        return score(a.score)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY 가 설정되어 있지 않다.\n"
              "  export ANTHROPIC_API_KEY=sk-ant-...", file=sys.stderr)
        return 2
    return run(a)


if __name__ == "__main__":
    raise SystemExit(main())
