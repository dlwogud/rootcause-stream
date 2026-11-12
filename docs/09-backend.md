# 09. 백엔드 구성

## 모듈 경계

```
app/
├── main.py                 FastAPI 앱, SSE 허브
├── routes/
│   ├── console.py          관제 화면 + /api/incidents*
│   ├── mobile.py           /m/upload/{token}
│   ├── search.py           /api/search/manual (mode 파라미터 = ablation 스위치)
│   └── evalview.py         성과표 조회
│
├── stream/
│   ├── replay.py           CSV 리플레이어 (1단계)
│   ├── detectors.py        관리도 / kNN / 잔차 — 선행 프로젝트 로직 이식
│   ├── windows.py          텀블링 윈도우, 버스트 탐지, 공발생 행렬
│   └── flink_job.py        PyFlink Table API (2단계)
│
├── agent/
│   ├── loop.py             수동 Agent 루프 + 중단/재개
│   ├── state.py            agent_state 직렬화/역직렬화
│   ├── prompts/            역할별 프롬프트 (버전 관리 대상)
│   ├── tools/
│   │   ├── timeseries.py
│   │   ├── manual.py
│   │   ├── diagram.py      도면 → VLM 질의
│   │   ├── cases.py
│   │   └── photo.py        request_photo (중단 신호 반환)
│   └── schemas.py          structured output 스키마 (pydantic)
│
├── llm/
│   ├── client.py           모델별 파라미터 분기 (effort vs budget_tokens)
│   ├── caching.py          cache_control 프리픽스 구성 + 적중률 로깅
│   └── vision.py           이미지 전처리(리사이즈) + 판독 호출
│
├── retrieval/
│   ├── index.py            매뉴얼 색인 구축
│   ├── hybrid.py           벡터 + BM25 + RRF
│   └── rerank.py           bge-reranker
│
├── memory/
│   └── cases.py            사례 서명 생성 / 유사 사례 조회 / 적립
│
└── db/
    ├── models.py           SQLAlchemy
    └── migrations/         Alembic

eval/
├── run.py                  평가 실행 (CLI, --batch로 Batches API)
├── cases/                  Tier A/B/C 케이스 정의 (YAML)
├── metrics/
│   ├── m1_rootcause.py
│   ├── m2_derived.py
│   ├── m4_infogain.py      ★ 정보이득
│   ├── m6_vlm.py
│   └── ...
├── judge.py                LLM-as-Judge (Sonnet 5)
└── report.py               HTML/표 생성
```

## Agent 루프 — 중단·재개의 핵심

```python
# agent/loop.py (구조만)

async def run_loop(incident_id: int, max_steps: int = 12) -> LoopOutcome:
    state = await load_state(incident_id)          # 없으면 초기화 + 가설 생성

    for _ in range(max_steps - state.step):
        resp = await llm.call(
            model=state.role_model("reason"),       # opus-5
            messages=state.messages,
            tools=TOOLS,
            system=cached_system(state),            # cache_control 프리픽스
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
        )
        state.append_assistant(resp)

        if resp.stop_reason != "tool_use":
            break

        results, suspend = await execute_tools(resp, state)

        if suspend:                                 # request_photo
            state.status = "awaiting_photo"
            await save_state(state)
            return LoopOutcome.SUSPENDED            # ← 프로세스 반환. 사람을 기다린다
        
        state.append_tool_results(results)
        await save_state(state)                     # 매 스텝 저장 (중단 복구)

    return await finalize(state)
```

재개는 동일 함수를 다시 호출한다. 사진 판독 결과를 `tool_result`로 주입한 뒤 `status`를 `diagnosing`으로 되돌리고 `run_loop`를 부른다. **Tool Runner 헬퍼를 쓰지 않는 이유가 여기 있다** — 루프 중간에 수 분짜리 사람 I/O가 들어가므로, 상태를 외부화한 수동 루프가 맞다.

타임아웃 처리는 별도 워커가 담당한다: `expires_at` 경과한 `awaiting_photo` incident를 찾아 `{"status":"no_response"}`를 주입하고 재개.

## 모델별 파라미터 분기 (한 곳에 모은다)

```python
# llm/client.py
def thinking_params(model: str, effort: str) -> dict:
    if model.startswith(("claude-opus-5", "claude-sonnet-5", "claude-opus-4-")):
        return {"thinking": {"type": "adaptive"},
                "output_config": {"effort": effort}}
    if model.startswith("claude-haiku-4-5"):
        return {"thinking": {"type": "enabled", "budget_tokens": 2048}}
    raise ValueError(model)
```

이유: Opus 5 / Sonnet 5에 `budget_tokens`를 보내면 400, Haiku 4.5에 `effort`를 보내면 에러다. 호출부에 흩어지면 반드시 사고가 난다.

## 주의할 API 제약 (설계에 이미 반영됨)

| 제약 | 대응 |
|---|---|
| `citations` + `output_config.format` 동시 사용 → 400 | 매뉴얼 근거 수집(citations)과 구조화 결론 생성을 **2회 호출로 분리** |
| Assistant prefill 불가 (Opus 5 / Sonnet 5) | 출력 형식 제어는 structured output으로만 |
| tool 입력 JSON 이스케이프가 모델마다 다를 수 있음 | tool 인자는 반드시 `json.loads()` — 문자열 매칭 금지 |
| 병렬 tool_use | 모든 `tool_result`를 **단일 user 메시지**에 담아 반환 (나누면 병렬 호출이 사라진다) |
| 이미지 토큰 | 업로드 시 장변 1568px로 리사이즈 — 그 이상은 토큰만 증가 |

## 운영 로깅 (평가의 원재료)

모든 LLM 호출에 대해 기록한다:

```
{incident_id, step, role, model, effort, 
 input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens,
 latency_ms, stop_reason, request_id}
```

`cache_read_input_tokens`가 반복 호출에서 0이면 캐시가 조용히 깨진 것이다 — 시스템 프롬프트에 타임스탬프나 UUID가 들어갔는지 확인. 이 로그가 비용 절감 성과(발표 수치)의 근거가 된다.

`request_id`(`response._request_id`)를 남기면 Anthropic 측 문제 신고 시 추적이 가능하다.
