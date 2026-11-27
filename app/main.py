"""RootCause Stream — 웹 서비스.

관제 화면에서 사건을 고르면 Agent 루프가 백그라운드로 돌고, 스텝마다 가설·증거가
SSE 로 흘러온다. Agent 가 촬영을 요청하면 1회성 토큰과 QR 이 생기고, 휴대폰에서
업로드한 사진을 VLM 이 판독해 **같은 세션으로 루프를 재개**한다
(docs/02-architecture.md — request_photo 는 비동기 중단점).

실행: uvicorn app.main:app --host 0.0.0.0 --port 8000
     → 같은 와이파이의 휴대폰에서 QR 로 접속한다
"""
from __future__ import annotations

import asyncio
import io
import json
import secrets
import socket
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.agent.declaration import photo_payload
from app.agent.inputs import agent_view
from app.agent.loop import FULL, WELD_QUALITY, AgentState, run
from app.agent.tools.photo import read_photo
from app.db import ROOT

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
UPLOADS = ROOT / "data" / "photos" / "uploads"
PHOTO_ROOT = ROOT / "data" / "photos"
TOKEN_TTL_S = 15 * 60
# 진단은 sonnet, 사진 판독은 haiku (2026-11-20)
#  - 진단: Tier E 에서 sonnet 이 날림을 더 잡았다 (eval/results/model_comparison.json)
#  - 판독: 기준 사진과 함께일 때 haiku 의 판별력이 sonnet 보다 높았다 (+35%p vs +28%p, reader_eval.json)
MODEL = "sonnet"
VLM_MODEL = "haiku"
DEMO_RUNS = ROOT / "data" / "demo_runs"   # 실제 실행을 기록한 이벤트 열 (scripts/record_demo.py)

app = FastAPI(title="RootCause Stream")

# 서버는 휴대폰이 접속하도록 0.0.0.0 에 열린다. 같은 와이파이의 다른 기기는 촬영 페이지(/m/)만 쓴다.
# 진단 시작·사진 선택 같은 나머지는 노트북 자신만 — 남이 진단을 반복 실행해 사용 한도를 쓰지 못하게.
LOCAL = {"127.0.0.1", "::1", "testclient"}


@app.middleware("http")
async def phone_only_upload(request: Request, call_next):
    host = request.client.host if request.client else ""
    if request.url.path.startswith("/m/") or host in LOCAL or host == lan_ip():
        return await call_next(request)
    return JSONResponse({"detail": "이 기기에서는 촬영 페이지만 열 수 있습니다"}, status_code=403)


# ── 사건 목록 ───────────────────────────────────────────────────
def _all_cases() -> dict:
    from eval.cases import load as load_abc
    from eval.tier_d import load as load_d
    out = {}
    for c in load_abc():
        out[c.case_id] = c
    try:
        for c in load_d():
            out[c.case_id] = c
    except FileNotFoundError:
        pass
    try:                                     # 실제 용접 · 실제 사진 — 시연용으로 고른 것만
        from eval.tier_e import load as load_e
        for c in load_e():
            if c.case_id in DEMO_E:
                out[c.case_id] = c
    except FileNotFoundError:
        pass
    return out


# 시연용 Tier E 사건 (2026-11-20, run #76 sonnet 기준). 진짜 사진으로는 맞히고 바꿔치기 사진으로는
# 틀린 사건 중에서 골랐다 — 잘 되는 사건을 고른 것이다. 전체 성능은 eval/RESULTS_TIER_E.md (약 56%)
DEMO_E = ("E-317", "E-323", "E-357", "E-483")


LANGUAGE = "ko"          # 화면을 보는 사람을 위해 AI 의 가설·요청·판독·결론을 한국어로 (평가 수치는 영어 출력으로 쟀다)


def _ablation(case):
    from dataclasses import replace
    return replace(WELD_QUALITY if getattr(case, "tier", "") == "E" else FULL, language=LANGUAGE)


CASE_BLURB = {
    "A": "실측 · 수준 이동 — 센서로 원인 특정 불가",
    "B": "합성 · 주입 결함",
    "C": "실측 · 알람 폭주 — 실은 설비 이상이 아님",
    "D": "구성 · 사진이 결정적인 사건",
    "E": "실제 용접 · 실제 사진 — 기록만으로는 날림을 못 가른다",
}


# ── 세션 ────────────────────────────────────────────────────────
@dataclass
class Session:
    id: str
    case_id: str
    state: AgentState | None = None
    events: list = field(default_factory=list)
    token: str | None = None
    token_expires: float = 0.0
    done: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    def push(self, ev: dict) -> None:
        with self.lock:
            ev["seq"] = len(self.events)
            ev["t"] = time.time()
            self.events.append(ev)


SESSIONS: dict[str, Session] = {}
TOKENS: dict[str, str] = {}          # token → session id


def lan_ip() -> str:
    """같은 와이파이의 휴대폰이 접속할 주소."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def _hyps(st: AgentState) -> list:
    return sorted(({"id": h["id"], "statement": h["statement"], "score": h["score"],
                    "cited": h.get("cited_evidence_ids", [])} for h in st.hypotheses),
                  key=lambda h: -h["score"])


def _agent_thread(sess: Session, case, max_steps: int) -> None:
    def on_step(st, act, note):
        ev = st.evidence[-1] if st.evidence else None
        sess.push({"type": "step", "step": st.step, "action": act.get("type"),
                   "tool": act.get("tool"), "note": note, "hypotheses": _hyps(st),
                   "evidence": ({"id": ev["id"], "kind": ev["kind"], "summary": ev["summary"]}
                                if ev and act.get("type") == "use_tool" else None),
                   "usage": {k: st.usage.get(k) for k in ("calls", "ms", "in", "cache_read")}})
    try:
        st = run(case, model=MODEL, max_steps=max_steps, state=sess.state, on_step=on_step,
                 ablation=_ablation(case))
        sess.state = st
        if st.status == "awaiting_photo":
            tok = secrets.token_urlsafe(8)
            sess.token, sess.token_expires = tok, time.time() + TOKEN_TTL_S
            TOKENS[tok] = sess.id
            sess.push({"type": "photo_request", "token": tok,
                       "upload_url": f"http://{lan_ip()}:8000/m/upload/{tok}",
                       "requests": st.photo_requests[-1]["requests"],
                       "hypotheses": _hyps(st), "expires_in_s": TOKEN_TTL_S})
        else:
            sess.done = True
            ch = next((t for t in st.transcript if t.get("action") == "declaration_challenge"), None)
            sess.push({"type": "final", "status": st.status, "root_cause": st.root_cause,
                       "challenge": ({"conflicts": ch["conflicts"],
                                      "draft_root_cause": ch["draft_root_cause"]} if ch else None),
                       "confidence": st.confidence, "cited": st.cited_evidence_ids,
                       "hypotheses": _hyps(st), "steps": st.step,
                       "usage": {k: st.usage.get(k) for k in ("calls", "ms", "in", "cache_read")}})
    except Exception as e:                           # 루프 실패가 서버를 죽이면 안 된다
        sess.done = True
        sess.push({"type": "error", "message": f"{type(e).__name__}: {str(e)[:300]}"})


def _match_request(reqs: list, path: Path) -> dict:
    """사진이 어느 요청에 대한 응답인지 — 뒷면 사진(…B.jpg)은 뒷면을 요청한 항목에 붙인다."""
    if not reqs:
        return {}
    from eval.tier_e import requested_sides
    face = "B" if path.name.endswith("B.jpg") else "F"
    return next((r for r in reqs if face in requested_sides(r)), reqs[0])


def _accept_photos(sess: Session, paths: list[Path], source: str) -> list[dict]:
    """사진(한 장 또는 앞면·뒷면 여러 장)을 판독해 증거로 넣고, 같은 세션으로 루프를 **한 번** 재개한다."""
    st = sess.state
    case = _all_cases()[sess.case_id]
    entry = st.photo_requests[-1] if st.photo_requests else {}
    out = []
    for path in paths:
        req = _match_request(entry.get("requests", []), path)
        # 같은 설비·같은 설정의 정상 샘플 사진(골든 샘플)이 있으면 나란히 보고 판독한다
        ref = getattr(case, "reference_photo", None)
        if ref and path.name.endswith("B.jpg"):         # 뒷면 사진이면 정상 샘플도 뒷면
            from eval.tier_e import back_of
            ref = back_of(ref)
        face = "뒷면" if path.name.endswith("B.jpg") else ("앞면" if path.name.endswith("F.jpg") else "")
        sess.push({"type": "photo_received", "source": source, "face": face,
                   "photo": str(path.relative_to(ROOT)), "reference": ref})
        reading = read_photo(path, req.get("target", ""), model=VLM_MODEL,
                             checks=list((req.get("if_observed") or {}).keys()), reference=ref,
                             language=LANGUAGE)
        clean = {k: v for k, v in reading.items() if not k.startswith("_")}
        payload = photo_payload(entry, req, clean)
        eid = st.add_evidence("photo", f"사진 판독{f' ({face})' if face else ''}: "
                                       f"{str(reading.get('observation',''))[:110]}", payload)
        sess.push({"type": "photo_read", "evidence_id": eid, "reading": clean, "face": face,
                   "photo": str(path.relative_to(ROOT)), "reference": ref,
                   "declaration": (payload.get("your_declaration") or {}).get("seen", [])})
        out.append(clean)
    if sess.token:
        TOKENS.pop(sess.token, None)
        sess.token = None
    st.status = "diagnosing"
    threading.Thread(target=_agent_thread, args=(sess, case, st.step + 5), daemon=True).start()
    return out


def _accept_photo(sess: Session, path: Path, source: str) -> dict:
    return _accept_photos(sess, [path], source)[0]


# ── 화면 ────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    cases = [{"id": c.case_id, "tier": c.case_id[0], "kind": c.kind,
              "alarms": c.alarm_count, "truth": c.truth_key,
              "blurb": CASE_BLURB.get(c.case_id[0], "")}
             for c in _all_cases().values()]
    order = {"E": 0, "D": 1, "C": 2, "A": 3, "B": 4}
    cases.sort(key=lambda c: (order.get(c["tier"], 9), c["id"]))
    return TEMPLATES.TemplateResponse(request, "dashboard.html",
                                      {"cases": cases, "model": MODEL, "vlm": VLM_MODEL})


@app.post("/api/sessions")
async def start(request: Request):
    body = await request.json()
    cid = body.get("case_id")
    cases = _all_cases()
    if cid not in cases:
        raise HTTPException(404, "알 수 없는 사건")
    case = cases[cid]
    sess = Session(id=secrets.token_hex(6), case_id=cid)
    SESSIONS[sess.id] = sess
    sess.push({"type": "incident", "case_id": cid, "kind": case.kind,
               "alarm_count": case.alarm_count, "summary": agent_view(case.cooccurrence),
               "window": [case.window_start, case.window_end]})
    threading.Thread(target=_agent_thread, args=(sess, case, 9), daemon=True).start()
    return {"session_id": sess.id}


@app.get("/api/sessions/{sid}/stream")
async def stream(sid: str):
    sess = SESSIONS.get(sid)
    if not sess:
        raise HTTPException(404)

    async def gen():
        i = 0
        while True:
            with sess.lock:
                new = sess.events[i:]
            for ev in new:
                yield f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"
            i += len(new)
            if sess.done and i >= len(sess.events):
                yield "event: end\ndata: {}\n\n"
                return
            await asyncio.sleep(0.4)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/sessions/{sid}/demo_photos")
def demo_photos(sid: str):
    """휴대폰이 없을 때 쓰는 시연용 사진. Tier D 는 사건에 준비된 사진을 쓴다."""
    sess = SESSIONS.get(sid)
    if not sess:
        raise HTTPException(404)
    case = _all_cases()[sess.case_id]
    if getattr(case, "tier", "") == "E":         # 그 용접의 사진 / 반대 판정을 받은 다른 용접의 사진
        from eval.tier_e import back_of
        return {"options": [{"key": "이 용접 · 앞면", "path": case.photo, "shows": "this_weld"},
                            {"key": "이 용접 · 뒷면", "path": back_of(case.photo), "shows": "this_weld_back"},
                            {"key": "다른 용접 (대조)", "path": case.swap_photo, "shows": "swap"}]}
    opts = []
    for ph in getattr(case, "photos", []) or []:
        opts.append({"key": ph.key, "path": ph.path, "shows": ph.shows})
    from eval.tier_d import RANDOM_PHOTO
    opts.append({"key": RANDOM_PHOTO.key, "path": RANDOM_PHOTO.path, "shows": RANDOM_PHOTO.shows})
    return {"options": opts}


@app.post("/api/sessions/{sid}/demo_photo")
async def use_demo_photo(sid: str, request: Request):
    sess = SESSIONS.get(sid)
    if not sess or not sess.state or sess.state.status != "awaiting_photo":
        raise HTTPException(409, "촬영 요청 대기 상태가 아니다")
    body = await request.json()
    paths = []
    for raw in (body.get("paths") or [body.get("path")])[:2]:   # 앞면·뒷면까지
        p = (ROOT / str(raw)).resolve()
        if PHOTO_ROOT.resolve() not in p.parents or not p.exists():
            raise HTTPException(400, "허용되지 않은 경로")
        paths.append(p)
    readings = await asyncio.to_thread(_accept_photos, sess, paths, "demo")
    return {"reading": readings[0], "readings": readings}


@app.post("/api/sessions/{sid}/no_photo")
def skip_photo(sid: str):
    """타임아웃 경로 — 사진 없이 결론을 내게 한다."""
    sess = SESSIONS.get(sid)
    if not sess or not sess.state:
        raise HTTPException(404)
    st = sess.state
    st.add_evidence("photo", "촬영 요청에 응답 없음 (타임아웃)",
                    {"status": "no_response", "note": "가진 증거만으로 결론을 내라."})
    st.status = "diagnosing"
    sess.push({"type": "photo_timeout"})
    case = _all_cases()[sess.case_id]
    threading.Thread(target=_agent_thread, args=(sess, case, st.step + 4), daemon=True).start()
    return {"ok": True}


# ── 녹화용 재생 ─────────────────────────────────────────────────
@app.get("/api/demo_runs/{name}")
def demo_run(name: str):
    """scripts/record_demo.py 가 남긴 실제 실행 기록. 화면은 이것을 시간만 압축해 재생한다.

    이벤트 내용은 손대지 않는다 — 재생은 '언제 보여주느냐'만 바꾼다.
    """
    if not name.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(404)
    p = DEMO_RUNS / f"{name}.json"
    if not p.exists():
        raise HTTPException(404)
    return json.loads(p.read_text())


@app.get("/qr/{token}.png")
def qr(token: str):
    import qrcode
    if token not in TOKENS:
        raise HTTPException(404)
    img = qrcode.make(f"http://{lan_ip()}:8000/m/upload/{token}", box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png")


@app.get("/photo")
def photo(path: str):
    p = (ROOT / path).resolve()
    if PHOTO_ROOT.resolve() not in p.parents or not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


# ── 모바일 ──────────────────────────────────────────────────────
def _session_for(token: str) -> Session:
    sid = TOKENS.get(token)
    sess = SESSIONS.get(sid) if sid else None
    if not sess or time.time() > sess.token_expires:
        raise HTTPException(410, "만료되었거나 이미 사용된 링크입니다")
    return sess


@app.get("/m/upload/{token}", response_class=HTMLResponse)
def mobile(request: Request, token: str):
    sess = _session_for(token)
    reqs = sess.state.photo_requests[-1]["requests"]
    return TEMPLATES.TemplateResponse(request, "mobile.html", {"token": token, "reqs": reqs})


def save_upload(data: bytes, dest: Path) -> None:
    """휴대폰 사진을 장변 1568px 로 줄여 저장한다 (그 이상은 토큰만 늘어난다).

    휴대폰은 사진을 가로로 저장하고 EXIF 방향 값만 붙이는 경우가 많다. 다시 저장하면 그 값이
    사라져 사진이 90도 돌아간 채 판독되므로, 줄이기 전에 방향대로 실제로 돌려 놓는다 (2026-11-27).
    """
    try:
        from PIL import Image, ImageOps
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
        im.thumbnail((1568, 1568))
        im.save(dest, "JPEG", quality=88)
    except Exception:
        dest.write_bytes(data)


@app.post("/m/upload/{token}")
async def mobile_upload(token: str, file: UploadFile = File(...)):
    sess = _session_for(token)
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "사진이 너무 큽니다")
    UPLOADS.mkdir(parents=True, exist_ok=True)
    dest = UPLOADS / f"{sess.id}_{int(time.time())}.jpg"
    save_upload(data, dest)
    reading = await asyncio.to_thread(_accept_photo, sess, dest, "mobile")
    return {"reading": reading}
