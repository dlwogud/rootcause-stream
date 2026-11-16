-- RootCause Stream — 1단계 스키마 (SQLite)
-- 2단계(11/29~)에서 Postgres + TimescaleDB + pgvector 로 이전한다.
-- 컬럼 구성은 docs/06-database.md 의 Postgres 설계를 따른다. 차이는 타입뿐이다.
--   VECTOR(n)   → BLOB (float32 배열)  + 코사인 유사도는 애플리케이션에서 계산
--   JSONB       → TEXT (JSON 문자열)
--   TSVECTOR    → FTS5 가상 테이블

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ── 매뉴얼 색인 ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS manual_pages (
  id                INTEGER PRIMARY KEY,
  doc               TEXT    NOT NULL,
  page_no           INTEGER NOT NULL,
  page_kind         TEXT    NOT NULL,   -- text | diagram
  n_images          INTEGER NOT NULL DEFAULT 0,
  n_chars           INTEGER NOT NULL DEFAULT 0,
  image_path        TEXT,               -- 도면 페이지 렌더 결과
  vlm_description   TEXT,               -- 도면의 구조 서술 (색인 대상)
  keywords          TEXT,               -- survey 휴리스틱 결과
  UNIQUE (doc, page_no)
);

CREATE TABLE IF NOT EXISTS manual_chunks (
  id          INTEGER PRIMARY KEY,
  page_id     INTEGER NOT NULL REFERENCES manual_pages(id) ON DELETE CASCADE,
  ord         INTEGER NOT NULL,
  heading     TEXT,
  content     TEXT    NOT NULL,
  source      TEXT    NOT NULL DEFAULT 'text',  -- text | vlm_description
  embedding   BLOB                              -- float32[dim]
);
CREATE INDEX IF NOT EXISTS idx_chunks_page ON manual_chunks(page_id);

-- BM25 용 전문검색. content 는 manual_chunks 와 동기화한다.
CREATE VIRTUAL TABLE IF NOT EXISTS manual_fts USING fts5(
  content, heading, content='manual_chunks', content_rowid='id', tokenize='porter unicode61'
);

-- ── 사건 / Agent ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS incidents (
  id             INTEGER PRIMARY KEY,
  opened_at      TEXT    NOT NULL,
  closed_at      TEXT,
  equipment_id   TEXT    NOT NULL,
  status         TEXT    NOT NULL DEFAULT 'open',
                 -- open | diagnosing | awaiting_photo | resolved | abandoned
  workday        TEXT,
  alarm_count    INTEGER NOT NULL DEFAULT 0,
  window_start   TEXT,
  window_end     TEXT,
  cooccurrence   TEXT,     -- JSON
  agent_state    TEXT,     -- JSON {messages, hypotheses, evidence, step}
  root_cause     TEXT,
  root_cause_cf  REAL,
  eval_tier      TEXT,     -- A | B | C | NULL
  eval_truth     TEXT,
  token_usage    TEXT      -- JSON
);
CREATE INDEX IF NOT EXISTS idx_inc_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_inc_opened ON incidents(opened_at DESC);

CREATE TABLE IF NOT EXISTS alarms (
  id           INTEGER PRIMARY KEY,
  ts           TEXT    NOT NULL,
  equipment_id TEXT    NOT NULL,
  detector     TEXT    NOT NULL,
  tag          TEXT    NOT NULL,
  severity     INTEGER NOT NULL,
  value        REAL,
  threshold    REAL,
  point_seq    INTEGER,
  is_dup       INTEGER NOT NULL DEFAULT 0,
  incident_id  INTEGER REFERENCES incidents(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_alarm_inc ON alarms(incident_id);
CREATE INDEX IF NOT EXISTS idx_alarm_ts  ON alarms(ts);

CREATE TABLE IF NOT EXISTS evidence (
  id           TEXT    NOT NULL,          -- 'E1','E2'... incident 내 유일
  incident_id  INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  kind         TEXT    NOT NULL,          -- timeseries|manual|diagram|photo|case
  summary      TEXT    NOT NULL,
  payload      TEXT,                      -- JSON
  created_at   TEXT    NOT NULL,
  PRIMARY KEY (incident_id, id)
);

-- ── 촬영 요청 / 사진 ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS photo_requests (
  id            INTEGER PRIMARY KEY,
  incident_id   INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  token         TEXT    NOT NULL UNIQUE,
  target        TEXT    NOT NULL,
  how_to_shoot  TEXT    NOT NULL,
  why           TEXT    NOT NULL,
  discriminates TEXT    NOT NULL,   -- JSON ["H1","H3"]
  if_observed   TEXT    NOT NULL,   -- JSON. **사진 수신 전에** 저장한다 (M4 정보이득의 전제)
  requested_at  TEXT    NOT NULL,
  expires_at    TEXT    NOT NULL,
  fulfilled_at  TEXT
);

CREATE TABLE IF NOT EXISTS photos (
  id           INTEGER PRIMARY KEY,
  request_id   INTEGER REFERENCES photo_requests(id) ON DELETE SET NULL,
  path         TEXT    NOT NULL,
  vlm_reading  TEXT,                -- JSON {observation, category, confidence, unreadable_reason}
  read_model   TEXT,
  read_at      TEXT
);

-- ── 사례 (Long-term Memory) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS cases (
  id           INTEGER PRIMARY KEY,
  incident_id  INTEGER REFERENCES incidents(id),
  signature    BLOB    NOT NULL,    -- float32[dim]
  root_cause   TEXT    NOT NULL,
  action_taken TEXT    NOT NULL,
  outcome      TEXT    NOT NULL,    -- resolved | ineffective | partial
  worker_note  TEXT,
  created_at   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS action_cards (
  id          INTEGER PRIMARY KEY,
  incident_id INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  steps       TEXT    NOT NULL,     -- JSON
  checks      TEXT    NOT NULL,     -- JSON
  created_at  TEXT    NOT NULL
);

-- ── 평가 ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS eval_runs (
  id          INTEGER PRIMARY KEY,
  started_at  TEXT NOT NULL,
  config      TEXT NOT NULL,   -- JSON ablation 조건
  git_sha     TEXT NOT NULL,
  model_map   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eval_results (
  run_id   INTEGER NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
  case_id  TEXT NOT NULL,
  tier     TEXT NOT NULL,
  metric   TEXT NOT NULL,
  value    REAL NOT NULL,
  detail   TEXT,
  PRIMARY KEY (run_id, case_id, metric)
);
