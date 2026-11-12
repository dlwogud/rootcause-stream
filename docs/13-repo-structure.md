# 13. GitHub 프로젝트 구조

```
rootcause-stream/
├── README.md                   서비스 개요 + 성과 요약 (심사용 얼굴)
├── PROGRESS.md                 진행 상태 — 재개 시 먼저 읽는다
├── run_all.sh                  전체 재현 (마지막 2단계가 종료 조건)
├── docker-compose.yml          redpanda / postgres / flink / app
├── requirements.txt
├── .env.example                ANTHROPIC_API_KEY, DATABASE_URL
├── .gitignore
│
├── docs/                       01~13 설계 문서 (이 디렉터리)
│
├── app/
│   ├── main.py
│   ├── routes/      console.py  mobile.py  search.py  evalview.py
│   ├── templates/   console.html  mobile_upload.html  partials/
│   ├── static/
│   ├── stream/      replay.py  detectors.py  windows.py  flink_job.py
│   ├── agent/       loop.py  state.py  schemas.py  prompts/  tools/
│   ├── llm/         client.py  caching.py  vision.py
│   ├── retrieval/   index.py  hybrid.py  rerank.py
│   ├── memory/      cases.py
│   └── db/          models.py  migrations/
│
├── eval/
│   ├── run.py
│   ├── judge.py
│   ├── report.py
│   ├── cases/       tier_a/*.yaml  tier_b/*.yaml  tier_c/*.yaml
│   ├── metrics/     m1_rootcause.py … m8_memory.py
│   └── configs/ablation/  full.yaml  no_photo.yaml  no_diagram.yaml  …
│
├── scripts/
│   ├── 00_ingest_process_data.py
│   ├── 01_index_manuals.py
│   ├── 02_upload_diagrams.py        Files API
│   ├── 90_verify_report_numbers.py  문서 인용 수치 ↔ 원본 CSV 대조 (exit 1 on mismatch)
│   └── 91_verify_artifacts.py       기대 산출물 mtime·SHA-256 검증 (exit 1 on stale)
│
├── spike/
│   └── vlm_reading_report.md        D1 판독 스파이크 결과 (버리는 코드지만 결과는 남긴다)
│
├── data/
│   ├── raw/           (gitignore) 공정 데이터
│   ├── manuals/       SOURCES.md  page_overrides.json  (PDF는 라이선스 확인 후)
│   └── photos/
│       ├── public/    CC 라이선스 측정용
│       ├── demo/      직접 촬영 시연용
│       └── private/   (gitignore) 라이선스 불명
│
├── outputs/           (gitignore) 표·그림·성과표
├── tests/
└── report/
    ├── 최종보고서.md
    └── 발표자료.pptx
```

## 심사자가 레포를 열었을 때 보이는 것

README 첫 화면에 다음이 순서대로 있어야 한다.

1. 한 문장 (무엇을 하는 서비스인가)
2. **"왜 LLM/VLM이 없으면 안 되는가" 표**
3. **성과표 2개** (진단 정확도 / 구성요소 기여도)
4. 시연 GIF 1개 (QR → 사진 → 점수 이동)
5. `bash run_all.sh` 한 줄 재현 안내
6. 설계 문서 링크

학생 레포 대부분은 1번과 설치 안내만 있다. 2·3·4가 있으면 그 자체로 차별된다.

## 커밋 규율

- 설계 문서 변경과 코드 변경을 같은 커밋에 섞지 않는다
- 각 ablation 결과는 `git_sha`와 함께 `eval_runs`에 기록된다 — 성과표의 재현 가능성이 커밋 해시에 묶인다
- 프롬프트는 `app/agent/prompts/` 안의 파일로 관리한다. 코드 문자열에 인라인하면 변경 이력이 추적되지 않고, 프롬프트 변경이 성과에 미친 영향을 설명할 수 없다
