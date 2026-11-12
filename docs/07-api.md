# 07. 주요 API 설계

FastAPI. 인증은 범위 외(로컬·시연 전제) — 단 모바일 업로드는 **1회성 토큰**으로 보호한다.

## 관제 (데스크톱)

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/` | 관제 대시보드 (Jinja2) |
| `GET` | `/api/stream` | **SSE** — 알람·incident·가설 변경 푸시 |
| `GET` | `/api/incidents?status=&limit=` | 사건 목록 |
| `GET` | `/api/incidents/{id}` | 사건 상세 (가설, 증거, 촬영요청, 조치카드) |
| `POST` | `/api/incidents/{id}/diagnose` | Agent 루프 수동 트리거 (데모·재실행용) |
| `GET` | `/api/incidents/{id}/trace` | **Agent 추론 트레이스** — 발표 시연의 핵심 화면 |
| `POST` | `/api/incidents/{id}/feedback` | 조치 결과 피드백 → 사례 적립 |

`/api/incidents/{id}/trace` 응답: 루프 각 스텝의 `{step, model, effort, tool_calls, hypotheses_before, hypotheses_after, tokens, latency_ms}`. 이 엔드포인트가 "기술을 실제로 썼다"는 증거를 화면으로 만든다.

## 촬영 (모바일)

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/m/upload/{token}` | 모바일 업로드 페이지. 요청 사유·촬영 방법 표시 |
| `POST` | `/m/upload/{token}` | 사진 업로드 (multipart) → VLM 판독 → Agent 루프 재개 |
| `GET` | `/api/photo-requests/{id}/qr` | QR PNG (관제 화면에 띄워 폰으로 스캔) |

**토큰 규칙**: 1회성, 기본 유효 15분, 사용 즉시 소멸. `photo_requests.expires_at` 경과 시 Agent는 `{"status":"no_response"}`로 재개된다.

`POST /m/upload/{token}` 처리 순서:
1. 토큰 검증 → `photo_requests` 조회
2. 이미지 저장 + 리사이즈 (장변 1568px 상한 — 그 이상은 토큰만 늘고 정확도 이득이 없다)
3. VLM 판독 (Haiku 4.5, structured output, few-shot 참조 이미지 동봉)
4. `evidence` 1건 생성 (kind=photo)
5. `incidents.status` → `diagnosing`, Agent 루프 재개 (백그라운드 태스크)
6. 작업자에게는 판독 결과를 즉시 보여준다 (판독 실패 시 재촬영 안내)

## 검색 (내부 + 디버깅용 공개)

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/api/search/manual` | `{query, mode}` — mode: `vector`\|`bm25`\|`hybrid`\|`hybrid_rerank` |
| `GET` | `/api/manual/pages/{id}/image` | 도면 페이지 이미지 |

`mode`를 API 파라미터로 노출한 이유: **ablation 실험이 이 엔드포인트를 그대로 호출한다.** 평가용 코드와 서비스 코드가 갈라지지 않게 한다. 그리고 시연에서 "리랭커를 끄면 이렇게 나옵니다"를 실시간으로 보여줄 수 있다.

## 평가 (CLI 중심, HTTP는 조회만)

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/api/eval/runs` | 실행 목록 |
| `GET` | `/api/eval/runs/{id}/report` | 성과표 (HTML/JSON) |

실행 자체는 CLI: `python -m eval.run --config configs/ablation/no_rerank.yaml --batch`

## Agent Tool 스키마 (모델에 노출되는 인터페이스)

모든 툴은 `strict: True` + `additionalProperties: False`.

| 툴 | 입력 | 반환 |
|---|---|---|
| `query_timeseries` | `{tag, start, end, agg}` | 통계 요약 + 추세 (원시 배열이 아니라 요약 — 토큰 절약) |
| `search_manual` | `{query, top_k}` | 청크 + `{doc, page}` |
| `lookup_diagram` | `{equipment_id, question}` | VLM이 도면을 보고 답한 텍스트 + 페이지 참조 |
| `recall_cases` | `{alarm_signature}` | 유사 사례 ≤2건 |
| `request_photo` | `{requests:[{target, how_to_shoot, discriminates, if_observed, why_this_photo}]}` | ⏸ 루프 중단 (결과는 재개 시 주입) |
| `finalize` | `{root_cause, confidence, cited_evidence_ids}` | 루프 종료 |

`query_timeseries`가 원시 시계열을 반환하지 않는 것이 중요하다. 수천 개 숫자를 컨텍스트에 넣으면 토큰이 폭증하고 정확도도 떨어진다. 요약 통계 + 추세 방향 + 임계 초과 구간만 반환한다.
