"""recall_cases — 과거 유사 사례 (Long-term Memory, 기술 #10).

사례 DB 가 비어 있으면 빈 목록을 돌려준다. 그 상태와 적립 후 상태를 비교하는 것이
M8(메모리 효과) 측정이다 — 정확도만이 아니라 **루프 길이와 토큰**이 줄어드는 것을 본다.
"""
from __future__ import annotations

import json

import numpy as np

from app.db import connect, from_blob, to_blob


def signature(cooccurrence: dict, ts_summary: dict | None = None) -> np.ndarray:
    """알람 패턴 + 이상 방향을 하나의 벡터로. 결정적이어야 재현된다."""
    tags = ["knn_conformal", "force_median_low", "force_median_high", "current_residual"]
    by_tag = (cooccurrence or {}).get("by_tag", {})
    tot = sum(by_tag.values()) or 1
    v = [by_tag.get(t, 0) / tot for t in tags]
    # dup_fraction 은 정답 라벨이라 서명에 쓰지 않는다 (app/agent/inputs.py). 차원 유지를 위해 0
    v.append(0.0)
    for name in ("force", "current", "voltage", "time"):
        s = ((ts_summary or {}).get("variables", {}) or {}).get(name, {})
        v.append(float(s.get("shift_in_sd") or 0.0) / 10.0)
        v.append(float(s.get("sd_ratio_vs_stable") or 1.0) / 10.0)
    a = np.asarray(v, dtype=np.float32)
    n = np.linalg.norm(a)
    return a / n if n else a


def recall_cases(sig: np.ndarray | None = None, top_k: int = 2,
                 min_sim: float = 0.80, **_) -> dict:
    con = connect()
    rows = con.execute("SELECT id, signature, root_cause, action_taken, outcome,"
                       " worker_note FROM cases").fetchall()
    con.close()
    if not rows or sig is None:
        return {"n_cases_in_memory": len(rows), "matches": []}
    M = np.stack([from_blob(r["signature"]) for r in rows])
    sims = M @ np.asarray(sig, dtype=np.float32)
    idx = np.argsort(-sims)[:top_k]
    return {"n_cases_in_memory": len(rows), "matches": [
        {"case_id": int(rows[i]["id"]), "similarity": round(float(sims[i]), 3),
         "root_cause": rows[i]["root_cause"], "action_taken": rows[i]["action_taken"],
         "outcome": rows[i]["outcome"], "worker_note": rows[i]["worker_note"]}
        for i in idx if sims[i] >= min_sim]}


def store_case(incident_id: int | None, sig: np.ndarray, root_cause: str,
               action_taken: str, outcome: str, note: str = "") -> int:
    from datetime import datetime, timezone
    con = connect()
    cid = con.execute(
        "INSERT INTO cases (incident_id, signature, root_cause, action_taken, outcome,"
        " worker_note, created_at) VALUES (?,?,?,?,?,?,?)",
        (incident_id, to_blob(sig), root_cause, action_taken, outcome, note,
         datetime.now(timezone.utc).isoformat())).lastrowid
    con.commit(); con.close()
    return cid
