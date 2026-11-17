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
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.agent.loop import AgentState, run
from app.agent.tools.photo import read_photo
from app.db import ROOT

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
UPLOADS = ROOT / "data" / "photos" / "uploads"
PHOTO_ROOT = ROOT / "data" / "photos"
TOKEN_TTL_S = 15 * 60
MODEL = "haiku"
DEMO_RUNS = ROOT / "data" / "demo_runs"   # 실제 실행을 기록한 이벤트 열 (scripts/record_demo.py)

app = FastAPI(title="RootCause Stream")


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
    return out


CASE_BLURB = {
    "A": "실측 · 수준 이동 — 센서로 원인 특정 불가",
    "B": "합성 · 주입 결함",
    "C": "실측 · 알람 폭주 — 실은 설비 이상이 아님",
    "D": "구성 · 사진이 결정적인 사건",
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
        st = run(case, model=MODEL, max_steps=max_steps, state=sess.state, on_step=on_step)
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
            sess.push({"type": "final", "status": st.status, "root_cause": st.root_cause,
                       "confidence": st.confidence, "cited": st.cited_evidence_ids,
                       "hypotheses": _hyps(st), "steps": st.step,
                       "usage": {k: st.usage.get(k) for k in ("calls", "ms", "in", "cache_read")}})
    except Exception as e:                           # 루프 실패가 서버를 죽이면 안 된다
        sess.done = True
        sess.push({"type": "error", "message": f"{type(e).__name__}: {str(e)[:300]}"})


def _accept_photo(sess: Session, path: Path, source: str) -> dict:
    """사진을 판독하고 증거로 넣은 뒤 같은 세션으로 루프를 재개한다."""
    st = sess.state
    req = st.photo_requests[-1]["requests"][0] if st.photo_requests else {}
    sess.push({"type": "photo_received", "source": source,
               "photo": str(path.relative_to(ROOT))})
    reading = read_photo(path, req.get("target", ""), model=MODEL)
    clean = {k: v for k, v in reading.items() if not k.startswith("_")}
    eid = st.add_evidence("photo", f"사진 판독: {str(reading.get('observation',''))[:120]}",
                          {"status": "received", "requested": req.get("target", ""), **clean})
    sess.push({"type": "photo_read", "evidence_id": eid, "reading": clean,
               "photo": str(path.relative_to(ROOT))})
    if sess.token:
        TOKENS.pop(sess.token, None)
        sess.token = None
    st.status = "diagnosing"
    case = _all_cases()[sess.case_id]
    threading.Thread(target=_agent_thread, args=(sess, case, st.step + 5), daemon=True).start()
    return clean


# ── 화면 ────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    cases = [{"id": c.case_id, "tier": c.case_id[0], "kind": c.kind,
              "alarms": c.alarm_count, "truth": c.truth_key,
              "blurb": CASE_BLURB.get(c.case_id[0], "")}
             for c in _all_cases().values()]
    order = {"D": 0, "C": 1, "A": 2, "B": 3}
    cases.sort(key=lambda c: (order.get(c["tier"], 9), c["id"]))
    return TEMPLATES.TemplateResponse(request, "dashboard.html", {"cases": cases})


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
               "alarm_count": case.alarm_count, "summary": case.cooccurrence,
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
    p = (ROOT / body["path"]).resolve()
    if PHOTO_ROOT.resolve() not in p.parents or not p.exists():
        raise HTTPException(400, "허용되지 않은 경로")
    reading = await asyncio.to_thread(_accept_photo, sess, p, "demo")
    return {"reading": reading}


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


@app.post("/m/upload/{token}")
async def mobile_upload(token: str, file: UploadFile = File(...)):
    sess = _session_for(token)
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "사진이 너무 큽니다")
    UPLOADS.mkdir(parents=True, exist_ok=True)
    dest = UPLOADS / f"{sess.id}_{int(time.time())}.jpg"
    try:                                  # 장변 1568px 로 축소 (그 이상은 토큰만 늘어난다)
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert("RGB")
        im.thumbnail((1568, 1568))
        im.save(dest, "JPEG", quality=88)
    except Exception:
        dest.write_bytes(data)
    reading = await asyncio.to_thread(_accept_photo, sess, dest, "mobile")
    return {"reading": reading}
