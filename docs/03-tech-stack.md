# 03. 기술 스택 및 선정 이유

## 요약

| 계층 | 선택 | 이유 |
|---|---|---|
| 언어 | Python 3.11+ | 기존 역량, Anthropic SDK, PyFlink |
| 메시지 | **Redpanda** (Kafka API 호환) | 단일 바이너리·단일 컨테이너. 1인 개발 환경에서 Kafka+ZK/KRaft 스택보다 압도적으로 가볍다. 코드는 `kafka-python`/`confluent-kafka` 그대로 |
| 스트림 | **PyFlink (Table API)** | 평가기준의 "실시간 데이터와 LLM 결합" 충족. 리스크는 아래 참조 |
| DB | **Postgres 16 + TimescaleDB + pgvector** | 시계열·벡터·관계형을 **한 DB로** 끝낸다. 1인 프로젝트에서 DB 3개를 운영하는 건 리스크 |
| 백엔드 | **FastAPI** + SSE | 비동기, SSE로 실시간 푸시, 모바일 업로드 엔드포인트 |
| 프론트 | **Jinja2 + HTMX + Tailwind(CDN)** | 16일 안에 관제 화면 + 모바일 업로드를 만들려면 SPA는 과잉. HTMX + SSE로 실시간 갱신 충분 |
| 임베딩 | `BAAI/bge-m3` (로컬) | 한국어·영어 혼재 매뉴얼에 적합, **API 비용 0** |
| 리랭커 | `BAAI/bge-reranker-v2-m3` (로컬) | 비용 0, ablation 대상으로 깔끔 |
| 문서 파싱 | PyMuPDF | 텍스트 추출 + 페이지 이미지 렌더(도면용) 동시 처리 |
| 컨테이너 | Docker Compose | Redpanda / Postgres / Flink / app |

### PyFlink 리스크 — 명시적으로 기록

PyFlink는 JVM 의존과 버전 호환 문제로 환경 구축이 아프다. **그래서 2단 전략을 쓴다.**

- **11/28까지**: 스트림 로직을 순수 Python 모듈 `stream/detectors.py`로 작성하고 CSV 리플레이어가 호출한다. 윈도우·버스트 탐지·공발생 행렬 전부 여기에 구현.
- **12/13까지**: 같은 로직을 PyFlink Table API 작업으로 이식. 인터페이스를 동일하게 유지해 교체 비용을 낮춘다.
- **PyFlink 구축이 12/10까지 실패하면**: Kafka Consumer + 슬라이딩 윈도우 직접 구현으로 대체하고 보고서에 사유를 기록한다. Kafka는 유지된다.

이 순서의 이유: 점수가 걸린 LLM/VLM 루프를 먼저 완성하고, 이미 할 수 있는 인프라를 뒤에 붙인다.

## 모델 선택

> 원칙: **기본은 `claude-opus-5`**, 단 이 프로젝트는 "저렴한 모델 우선"이 요구사항이므로 역할별로 등급을 나눈다. 최종 성과표 측정만 상위 모델로 돌린다.

| 역할 | 모델 | 설정 | 이유 |
|---|---|---|---|
| 가설 생성 / 재평가 | `claude-opus-5` | `thinking:{type:"adaptive"}`, `output_config:{effort:"high"}` | 다중 가설 추론이 서비스의 핵심. 여기서 아끼면 전부 무너진다 |
| 촬영 요청 설계 | `claude-opus-5` | adaptive, `effort:"high"` | "어떤 사진이 가설을 가르는가"는 가장 어려운 추론 |
| 도면(P&ID) 판독 | `claude-sonnet-5` | adaptive, `effort:"medium"` | 도면은 복잡하지만 호출 빈도가 낮고 캐시가 먹는다 |
| 현장 사진 판독 | `claude-haiku-4-5` | `thinking:{type:"enabled", budget_tokens:2048}` | 판정 과제를 정성·구간 분류로 한정했으므로 충분. 호출 빈도 최고 → 가장 저렴한 모델 |
| 조치 카드 생성 | `claude-sonnet-5` | adaptive, `effort:"medium"` | 플로우차트 이미지 → 단계 변환 |
| LLM-as-Judge (평가) | `claude-sonnet-5` | adaptive, `effort:"high"` | 피평가 모델(Opus 5)과 **분리**해야 채점이 신뢰받는다 |
| 개발 중 반복 실행 | `claude-sonnet-5` | `effort:"medium"` | 최종 성과표만 Opus 5로 재측정 |

주의: Haiku 4.5는 `effort`를 지원하지 않고 `budget_tokens`를 쓴다. Opus 5 / Sonnet 5는 `budget_tokens`를 보내면 400이다. 모델별 분기를 `llm/client.py`에 한 곳으로 모은다.

### 가격 (2026-06 기준, 1M 토큰당)

| 모델 | 입력 | 출력 | 컨텍스트 |
|---|---:|---:|---:|
| `claude-opus-5` | $5.00 | $25.00 | 1M |
| `claude-sonnet-5` | $2.00 | $10.00 | 1M |
| `claude-haiku-4-5` | $1.00 | $5.00 | 200K |

## 비용 설계

### 추정 (실측 아님 — 1주차에 `count_tokens`로 재산정할 것)

| 작업 | 토큰 추정 | 모델 | 건당 |
|---|---|---|---:|
| 사진 1장 판독 | 입력 ~2K(이미지 포함) / 출력 ~0.3K | Haiku 4.5 | ~$0.004 |
| Agent 루프 1회 (캐시 90% 적용) | 입력 ~30K / 출력 ~3K | Opus 5 | ~$0.09 |
| Agent 루프 1회 | 동일 | Sonnet 5 | ~$0.04 |

개발 중 반복 1,000회(Sonnet 5) + 최종 측정 200회(Opus 5) + 사진 판독 500건
→ **대략 $60~80**. 아래 4개 레버로 절반 이하로 줄인다.

### 비용 레버 (순서대로 적용)

1. **Prompt caching** — 매뉴얼 발췌와 도면 설명은 incident 간 재사용된다. `cache_control:{type:"ephemeral", ttl:"1h"}`로 고정 프리픽스에 걸고, `usage.cache_read_input_tokens`가 0이 아닌지 매 호출 로깅한다. 시스템 프롬프트에 타임스탬프/UUID를 넣으면 캐시가 조용히 깨진다 — 금지.
2. **Message Batches** — 벤치마크 평가는 지연에 민감하지 않다. `client.messages.batches.create()`로 **50% 할인**. ablation 전체 실행은 반드시 배치로.
3. **effort 조절** — 판정류는 `low`, 가설 생성만 `high`. 전부 `high`로 두면 비용이 몇 배가 된다.
4. **Files API** — 같은 도면 페이지를 매번 base64로 재전송하지 않는다. `client.files.upload()` 후 `{"type":"document","source":{"type":"file","file_id":...}}`로 참조.

### 사용할 API 기능 (전부 현행 문법)

| 기능 | 호출 형태 | 용도 |
|---|---|---|
| Structured output | `output_config={"format": {...}}` | 가설/판독/조치 스키마 |
| Strict tool use | 툴 정의에 `strict: True` + `additionalProperties: False` | tool 인자 스키마 보장 |
| Vision | `{"type":"image","source":{"type":"base64",...}}` | 현장 사진·도면 |
| Document citations | document 블록에 `citations={"enabled": True}` | 매뉴얼 근거 인용 (`cited_text`, `page_location`) |
| Adaptive thinking | `thinking={"type":"adaptive"}` | 가설 추론 |
| Prompt caching | `cache_control={"type":"ephemeral","ttl":"1h"}` | 비용 |
| Batches | `client.messages.batches.*` | 평가 |

⚠️ **citations와 `output_config.format`은 함께 쓰면 400이다.** 그래서 호출을 2개로 나눈다 — ① 매뉴얼 근거 수집(citations 사용, 자유 텍스트) ② 구조화 결론 생성(structured output). 이 제약은 설계에 반영되어 있다.

## 외부 API 의존성

| 의존 | 대체 가능성 | 실패 시 |
|---|---|---|
| Anthropic API | 유일한 필수 외부 의존 | 서비스 정지. 로컬 오픈 VLM 폴백은 **범위 외**(명시) |
| (없음) 임베딩·리랭커 | 로컬 모델 | — |
| (없음) 외부 DB/검색 | 자체 Postgres | — |

의존을 1개로 유지한 것은 의도적이다. 1개월 프로젝트에서 외부 API가 2개 이상이면 장애 지점이 곱해진다.
