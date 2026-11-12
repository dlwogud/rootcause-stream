# 02. 시스템 아키텍처

## 전체 구성

```
┌─ 이벤트 소스 ──────────────────────────────────────────┐
│  1단계(11/28): CSV 리플레이어  (실제 용접 공정 데이터)   │
│  2단계(12/13): Kafka Producer → topic: raw-events       │
└────────────────────────────┬───────────────────────────┘
                             ↓
┌─ 스트림 처리 (Flink) ──────────────────────────────────┐
│  · 텀블링 윈도우 집계 (10s)                             │
│  · 관리도(2σ) + kNN 이상점수 → 알람 생성                │
│  · 알람 버스트 탐지 (윈도우 내 알람 수 임계치)           │
│  · 선후관계 / 공발생 행렬 계산                           │
└────────────────────────────┬───────────────────────────┘
                             ↓  topic: incidents
┌─ Diagnosis Agent (수동 루프) ──────────────────────────┐
│                                                        │
│  A. 가설 생성        Opus 5, adaptive thinking, high   │
│         ↓                                              │
│  B. 증거 수집 루프 (Tool Calling)                       │
│     ├ query_timeseries(tag, window)   → Timescale      │
│     ├ search_manual(query)            → pgvector+rerank│
│     ├ lookup_diagram(equipment_id)    → 도면 → VLM     │
│     ├ recall_cases(signature)         → 과거 사례       │
│     └ request_photo(target, purpose)  → ⏸ 루프 중단     │
│         ↓                                              │
│  C. 사진 도착 → VLM 판독 (Haiku 4.5, structured)        │
│         ↓                                              │
│  D. 가설 재평가 (Reflection) → 확정 or B로 복귀          │
│         ↓                                              │
│  E. 조치 카드 생성 + 사례 적립 (Long-term Memory)        │
└────────────────────────────┬───────────────────────────┘
                             ↓
┌─ Web (FastAPI + HTMX + SSE) ───────────────────────────┐
│  관제 화면: 알람 타임라인 · 가설 보드 · 조치 카드        │
│  모바일   : QR → /m/upload/{token} 촬영 업로드          │
└────────────────────────────────────────────────────────┘
```

## 핵심 설계 결정 — Agent 루프가 사람을 기다린다

**`request_photo`는 일반 tool call이 아니다. 비동기 중단점이다.**

일반 Agent 루프는 tool을 호출하고 수 초 안에 결과를 받는다. 그러나 촬영 요청은 작업자가 현장으로 이동해 사진을 찍어야 하므로 **수 분~수십 분이 걸리고, 아예 응답하지 않을 수도 있다.** 동기 루프로는 버틸 수 없다.

그래서 Agent 상태를 외부화한다.

| | |
|---|---|
| 상태 저장 | `incidents.agent_state` (JSONB) — 가설, 증거, 대화 메시지 전체 |
| 중단 | `request_photo` 호출 시 `status = awaiting_photo`, 루프 종료, 프로세스 반환 |
| 재개 | 사진 업로드 이벤트 → 상태 로드 → VLM 판독 결과를 `tool_result`로 주입 → 루프 재진입 |
| 타임아웃 | 15분 미응답 시 `request_photo` 결과를 `{"status":"no_response"}`로 채워 재개 → Agent가 사진 없이 최선의 결론을 내린다 |

**이게 보고서에 쓸 기술적 주장 중 하나다.** "Human-in-the-loop Agent는 상태를 메모리에 둘 수 없다."

메시지 히스토리를 DB에 저장하므로 재개 시 전체를 다시 전송한다. 도면·매뉴얼 컨텍스트는 prompt caching으로 재사용한다(`03-tech-stack.md` 비용 절).

## 가설 상태 모델

각 가설은 확률이 아니라 **증거 로그 + 현재 점수**를 가진다. 점수는 LLM이 structured output으로 직접 갱신하고, 갱신 시 반드시 근거 증거 id를 인용하게 한다(근거 없는 점수 변경 차단).

```json
{
  "id": "H1",
  "statement": "상부 전극 팁 마모로 접촉 저항이 상승했다",
  "score": 0.91,
  "evidence": [
    {"id": "E3", "kind": "timeseries", "effect": "support", "note": "동저항 상향 추세"},
    {"id": "E7", "kind": "photo",      "effect": "support", "note": "팁 선단 버섯형 변형"}
  ],
  "discriminating_tests": ["상부 전극 팁 근접 촬영"]
}
```

## 촬영 요청 생성 로직

Agent는 "아무 사진"을 요청하지 않는다. **가설을 가르는 사진**을 요청해야 한다.

1. 남은 가설 집합과 각 점수를 본다
2. 각 후보 관찰 대상에 대해 "이 사진의 결과가 어떻게 나오면 어떤 가설이 배제되는가"를 structured output으로 서술하게 한다
3. 가설 분포의 불확실성을 가장 크게 줄이는 2개 이하를 선택한다
4. 선택 이유를 작업자에게 그대로 보여준다 ("이 사진으로 H1과 H3을 구분합니다")

이 선택이 실제로 유효했는지는 **정보이득(information gain)**으로 사후 측정한다 → `10-evaluation.md` 메트릭 M4. 이 메트릭이 발표의 차별 포인트다.

## 전체 데이터 흐름 (한 사건)

| 순서 | 입력 | 처리 | 출력 | 저장 |
|---:|---|---|---|---|
| 1 | 공정 레코드 | 리플레이/Kafka | 이벤트 | `events` |
| 2 | 이벤트 | Flink 윈도우 + 탐지기 | 알람 | `alarms` |
| 3 | 알람 N건 | 버스트 탐지 | Incident | `incidents` |
| 4 | Incident | 가설 생성 (LLM) | 가설 3~5 | `agent_state` |
| 5 | 가설 | 증거 수집 (Tool) | 증거 | `evidence` |
| 6 | 가설 | 촬영 요청 (LLM) | 요청 + 토큰 | `photo_requests` |
| 7 | 사진 | VLM 판독 | 판독 결과 | `photos`, `evidence` |
| 8 | 증거 전체 | 재평가 (LLM) | 확정 원인 | `incidents.root_cause` |
| 9 | 확정 원인 | 조치 카드 (VLM+LLM) | 단계 목록 | `action_cards` |
| 10 | 작업자 피드백 | 사례 적립 | 사례 벡터 | `cases` |
