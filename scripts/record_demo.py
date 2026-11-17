"""시연 녹화용 — 웹 서비스로 실제 진단을 한 번 돌리고, 화면에 흘러간 이벤트를 그대로 저장한다.

발표장에서 라이브로 돌리면 3~4분이 걸리고 와이파이·LLM 지연에 취약하다. 그래서
실제 실행을 기록해 두고, 관제 화면이 그 기록을 **시간만 압축해** 재생하게 한다
(`/?replay=<name>`). 이벤트 내용은 손대지 않는다 — 화면에 '실제 실행 기록 · N배속'을 표시한다.

사용:
  .venv/bin/python scripts/record_demo.py A-2020-03-25 --photo data/photos/tier_d/equipment_exterior.jpg
  .venv/bin/python scripts/record_demo.py A-2020-03-25 --no-photo --name a25-timeout
→ data/demo_runs/<name>.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import DEMO_RUNS, SESSIONS, app  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("case_id")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--photo", help="촬영 요청에 응답할 사진 (data/photos 아래)")
    g.add_argument("--no-photo", action="store_true", help="응답 없음(타임아웃) 경로")
    ap.add_argument("--name", help="저장 이름 (기본: 사건 id)")
    ap.add_argument("--human-delay", type=float, default=8.0,
                    help="촬영 요청 후 사람이 응답하기까지 기다리는 초 (재생 화면에 그대로 남는다)")
    ap.add_argument("--timeout", type=float, default=900)
    a = ap.parse_args()

    client = TestClient(app)
    sid = client.post("/api/sessions", json={"case_id": a.case_id}).json()["session_id"]
    sess = SESSIONS[sid]
    t0, answered = time.time(), False
    print(f"session {sid} — {a.case_id}", flush=True)
    seen = 0
    while not sess.done:
        if time.time() - t0 > a.timeout:
            sys.exit("시간 초과")
        evs = sess.events
        for ev in evs[seen:]:
            print(f"  +{ev['t'] - t0:6.1f}s  {ev['type']}"
                  + (f"  {ev.get('tool') or ev.get('action') or ''}" if ev["type"] == "step" else ""),
                  flush=True)
        seen = len(evs)
        if (not answered and sess.state is not None and sess.state.status == "awaiting_photo"
                and any(e["type"] == "photo_request" for e in evs)):
            time.sleep(a.human_delay)
            if a.no_photo:
                client.post(f"/api/sessions/{sid}/no_photo")
            else:
                r = client.post(f"/api/sessions/{sid}/demo_photo", json={"path": a.photo})
                r.raise_for_status()
            answered = True
            continue
        time.sleep(0.5)
    for ev in sess.events[seen:]:
        print(f"  +{ev['t'] - t0:6.1f}s  {ev['type']}", flush=True)

    events = json.loads(json.dumps(sess.events, ensure_ascii=False, default=str))
    for ev in events:                       # 노트북의 사설 IP 는 남기지 않는다
        if "upload_url" in ev:
            ev["upload_url"] = re.sub(r"^http://[^/]+", "http://<노트북 IP>:8000", ev["upload_url"])
    final = next((e for e in reversed(events) if e["type"] in ("final", "error")), {})
    out = {"meta": {"case_id": a.case_id,
                    "photo": None if a.no_photo else a.photo,
                    "recorded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "elapsed_s": round(events[-1]["t"] - events[0]["t"], 1),
                    "human_delay_s": a.human_delay,
                    "final_type": final.get("type")},
           "events": events}
    DEMO_RUNS.mkdir(parents=True, exist_ok=True)
    p = DEMO_RUNS / f"{a.name or a.case_id}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"→ {p}  ({out['meta']['elapsed_s']}s, {len(events)} events, {final.get('type')})")
    if final.get("type") == "final":
        print("결론:", final.get("root_cause"))


if __name__ == "__main__":
    main()
