# 06. 데이터베이스 설계

Postgres 16 단일 인스턴스 + `timescaledb` + `pgvector` + `pg_trgm`.

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

## 공정 / 알람

```sql
-- 공정 이벤트 (하이퍼테이블)
CREATE TABLE events (
  ts           TIMESTAMPTZ NOT NULL,
  equipment_id TEXT        NOT NULL,
  point_seq    INTEGER,                 -- 용접점 순번
  force        DOUBLE PRECISION,
  current      DOUBLE PRECISION,
  resistance   DOUBLE PRECISION,
  heat_input   DOUBLE PRECISION,
  is_dup_block BOOLEAN NOT NULL DEFAULT FALSE  -- Tier C(26.8% 중복) 플래그
);
SELECT create_hypertable('events', 'ts');

-- 알람
CREATE TABLE alarms (
  id           BIGSERIAL PRIMARY KEY,
  ts           TIMESTAMPTZ NOT NULL,
  equipment_id TEXT NOT NULL,
  detector     TEXT NOT NULL,       -- control_chart | knn | residual
  tag          TEXT NOT NULL,       -- force_median | knn_score | ...
  severity     SMALLINT NOT NULL,
  value        DOUBLE PRECISION,
  threshold    DOUBLE PRECISION,
  incident_id  BIGINT               -- 버스트 귀속 (NULL = 미귀속)
);
CREATE INDEX ON alarms (ts DESC);
CREATE INDEX ON alarms (incident_id);
```

## 사건 / Agent

```sql
CREATE TYPE incident_status AS ENUM (
  'open', 'diagnosing', 'awaiting_photo', 'resolved', 'abandoned'
);

CREATE TABLE incidents (
  id             BIGSERIAL PRIMARY KEY,
  opened_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  closed_at      TIMESTAMPTZ,
  equipment_id   TEXT NOT NULL,
  status         incident_status NOT NULL DEFAULT 'open',
  alarm_count    INTEGER NOT NULL,
  burst_window   TSTZRANGE NOT NULL,
  cooccurrence   JSONB,          -- Flink가 계산한 공발생/선후 행렬
  -- Agent 상태 외부화 (02-architecture.md 핵심 설계)
  agent_state    JSONB,          -- {messages, hypotheses, evidence, loop_count}
  root_cause     TEXT,           -- 확정 원인 라벨
  root_cause_cf  REAL,           -- 확정 신뢰도
  -- 평가용
  eval_tier      CHAR(1),        -- A | B | C | NULL(운영)
  eval_truth     TEXT,           -- 정답 라벨 (평가 케이스만)
  token_usage    JSONB           -- {input, output, cache_read, by_model{}}
);
CREATE INDEX ON incidents (status);
CREATE INDEX ON incidents (opened_at DESC);
```

`agent_state`를 JSONB 단일 컬럼으로 둔 이유: Agent 메시지 히스토리는 스키마가 모델/버전에 따라 변한다. 정규화하면 매번 마이그레이션이 필요하다. 조회·집계가 필요한 필드만 위로 승격했다.

```sql
-- 증거 (가설 점수 변경의 근거. id를 LLM이 인용한다)
CREATE TABLE evidence (
  id           TEXT PRIMARY KEY,      -- 'E1', 'E2', ... (incident 내 유일)
  incident_id  BIGINT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  kind         TEXT NOT NULL,         -- timeseries | manual | diagram | photo | case
  summary      TEXT NOT NULL,
  payload      JSONB,                 -- 원 데이터 또는 참조(file_id, page, chunk_id)
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 촬영 요청 / 사진

```sql
CREATE TABLE photo_requests (
  id            BIGSERIAL PRIMARY KEY,
  incident_id   BIGINT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  token         TEXT UNIQUE NOT NULL,   -- QR/링크용 1회성 토큰
  target        TEXT NOT NULL,
  how_to_shoot  TEXT NOT NULL,
  why           TEXT NOT NULL,          -- 작업자에게 보여주는 이유
  discriminates TEXT[] NOT NULL,        -- ['H1','H3']
  if_observed   JSONB NOT NULL,         -- 사전 선언된 관찰→가설 영향 매핑
  requested_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at    TIMESTAMPTZ NOT NULL,
  fulfilled_at  TIMESTAMPTZ
);

CREATE TABLE photos (
  id           BIGSERIAL PRIMARY KEY,
  request_id   BIGINT REFERENCES photo_requests(id) ON DELETE SET NULL,
  path         TEXT NOT NULL,
  anthropic_file_id TEXT,
  vlm_reading  JSONB,        -- {observation, category, confidence, unreadable_reason}
  read_model   TEXT,
  read_at      TIMESTAMPTZ
);
```

`if_observed`를 **사진 수신 전에** 저장하는 것이 핵심이다. 정보이득(M4) 계산은 이 사전 선언과 사후 실제 판독을 대조해야 성립한다.

## 매뉴얼 색인 (하이브리드 검색)

```sql
CREATE TABLE manual_pages (
  id           BIGSERIAL PRIMARY KEY,
  doc          TEXT NOT NULL,
  page_no      INTEGER NOT NULL,
  page_kind    TEXT NOT NULL,        -- text | diagram | flowchart
  image_path   TEXT,                 -- 도면/플로우차트만
  anthropic_file_id TEXT,
  vlm_description  TEXT              -- 도면의 구조 서술 (색인 대상)
);

CREATE TABLE manual_chunks (
  id         BIGSERIAL PRIMARY KEY,
  page_id    BIGINT NOT NULL REFERENCES manual_pages(id) ON DELETE CASCADE,
  heading    TEXT,
  content    TEXT NOT NULL,
  embedding  VECTOR(1024),           -- bge-m3
  tsv        TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED
);
CREATE INDEX ON manual_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON manual_chunks USING gin (tsv);
```

하이브리드 검색: 벡터 top-30 ∪ BM25 top-30 → RRF 병합 → bge-reranker로 top-5. ablation은 ① 벡터만 ② BM25만 ③ 하이브리드 ④ 하이브리드+리랭커 4조건.

## 사례 (Long-term Memory)

```sql
CREATE TABLE cases (
  id              BIGSERIAL PRIMARY KEY,
  incident_id     BIGINT REFERENCES incidents(id),
  signature       VECTOR(256) NOT NULL,   -- [알람패턴, 원인, 이상방향] 결합 벡터
  root_cause      TEXT NOT NULL,
  action_taken    TEXT NOT NULL,
  outcome         TEXT NOT NULL,          -- resolved | ineffective | partial
  worker_note     TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON cases USING hnsw (signature vector_cosine_ops);
```

`outcome = 'ineffective'`인 사례도 저장한다 — "이 조치는 효과가 없었다"는 정보가 더 가치 있다.

## 조치 카드

```sql
CREATE TABLE action_cards (
  id          BIGSERIAL PRIMARY KEY,
  incident_id BIGINT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  steps       JSONB NOT NULL,   -- [{order, instruction, citation{doc,page,cited_text}, caution}]
  checks      JSONB NOT NULL,   -- 조치 후 확인 포인트
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

모든 step은 `citation`을 가진다. 인용 없는 step은 생성 단계에서 거부한다(기술 #9, #11).

## 평가 기록

```sql
CREATE TABLE eval_runs (
  id          BIGSERIAL PRIMARY KEY,
  started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  config      JSONB NOT NULL,   -- ablation 조건: {rerank:false, diagram:true, ...}
  git_sha     TEXT NOT NULL,
  model_map   JSONB NOT NULL
);

CREATE TABLE eval_results (
  run_id     BIGINT NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
  case_id    TEXT NOT NULL,
  tier       CHAR(1) NOT NULL,
  metric     TEXT NOT NULL,     -- M1..M8
  value      DOUBLE PRECISION NOT NULL,
  detail     JSONB,
  PRIMARY KEY (run_id, case_id, metric)
);
```

`git_sha`와 `config`를 함께 저장해야 성과표가 재현 가능해진다. 선행 프로젝트에서 산출물 진위 검사를 종료 조건으로 걸었던 방식을 그대로 따른다.
