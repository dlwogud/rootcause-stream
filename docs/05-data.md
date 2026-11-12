# 05. 데이터 수집 및 전처리

## 3종 소스

| 소스 | 무엇 | 확보 상태 |
|---|---|---|
| A. 공정 시계열 | 저항점용접(RSW) 공정 데이터 | ✅ **보유** (`~/kamp-welding/data/raw/`) |
| B. 설비 문서 | 용접기 O&M 매뉴얼, 배선도·공압계통, 트러블슈팅 | ✅ **확보** 5종 415p (`data/manuals/`) |
| C. 현장 사진 | 게이지, 표시등, 에러코드 패널, 부식·균열 | 🟡 공개수집 ✅ (`data/photos/public/`) / **직접 촬영 ⬜** |

---

## A. 공정 시계열 — 이미 보유, 그리고 라벨 출처가 외부다

선행 프로젝트(제6회 K-인공지능 제조데이터 분석 경진대회, `~/kamp-welding`)에서 분석을 끝낸 데이터.

| | |
|---|---|
| 규모 | 용접점 11,939개, 작업일 8일 |
| 공정 변수 | 가압력, 전류, 동저항, 입열량 |
| 실제 불량 라벨 | 작업일 단위 집계 39건 |
| 파일 | `Welding Data Set_01.xlsx`, `scaled_data.csv` |

### 알람 스트림 생성 방법 — 발명하지 않는다

알람은 새로 만들지 않고, **선행 프로젝트에서 이미 검증된 탐지기 2개를 재사용해 생성**한다.

| 탐지기 | 선행 검증 결과 | 이 프로젝트에서의 역할 |
|---|---|---|
| 2σ 관리도 (작업일 가압력 중위수) | 실제 공정 shift **3/3 탐지**, 오경보 **0/5**, exact permutation **p = 0.0179** | 수준 이동 알람 |
| kNN 거리 (k=3, 물리 파생 공간) | 7종 결함에 mean ROC-AUC 0.971 — **단, 주입한 결함에 대한 민감도** | 점 단위 이상 알람 |
| 정상운전 모델 (가압력→전류, LODO R² 0.509) | — | 잔차 기반 보조 알람 |

**중요: 알람 1건 = 사건이 아니다.** 하나의 공정 이상이 두 탐지기에서 여러 윈도우에 걸쳐 수십 건의 알람으로 나타나고, 그 중 대부분이 파생 알람이다. 이게 바로 Agent가 수렴시켜야 하는 입력이다.

### 정답 라벨 — 3개 Tier로 분리해서 보고한다

이 구분이 **발표 질의응답에서 가장 중요한 방어선**이다.

| Tier | 케이스 수 | 정답의 출처 | 발표에서의 표기 |
|---|---:|---|---|
| **A. 실측** | 3 | 선행 프로젝트에서 **permutation test로 통계적으로 입증한 실제 공정 shift** (p=0.0179). 라벨을 심지 않았다 | 주 성과표 |
| **B. 합성(명시)** | 7종 × n | 물리 기반으로 **주입한** 결함 모드 | "주입 결함에 대한 민감도"로 **별도 표기** |
| **C. 데이터 품질** | 1 | 실제 데이터에서 발견된 **26.8% 중복 구간** (800점 런이 4개 작업일에 반복, 1개 작업일은 전체가 이 런) | 주 성과표 |

> **Tier C가 가장 참신한 평가 케이스다.** 이 구간에서 알람이 터지지만 원인은 설비 이상이 **아니라** 데이터 수집 계통 이상이다. Agent가 "이것은 설비 고장이 아닙니다"라고 올바르게 판정하면, 그건 패턴 매칭이 아니라 추론이라는 증거가 된다. 선행 프로젝트에서 이 중복을 제외하자 이전 결론이 **4/4 탐지 → 0/3으로 완전히 뒤집혔다** — 즉 이전 결과는 이 artifact를 탐지하고 있었다.

**Tier A 3건으로는 표본이 작다.** 이 한계를 발표에서 먼저 말한다. 보완책:
- Tier B를 **난이도 축**으로 활용해 케이스 수를 확보(단 합성임을 매 표에 명기)
- 선행 프로젝트의 외부 데이터셋 2종(`22_external_press.py`, `23_external_mold.py`)으로 **도메인 이전 검증** — 재튜닝 없이 적용했을 때의 성능을 부가 성과로 제시

### 전처리

1. 작업일/타점 순서로 정렬하여 **의사 타임스탬프 부여** (원본에 연속 시각이 없다면 타점 간격을 상수로 가정 — 이 가정을 코드와 보고서에 명기)
2. 리플레이 속도 배율 파라미터화 (`--speed 60` = 실시간 60배)
3. 중복 구간(26.8%)을 **제거하지 않고 플래그만 부여** — Tier C 평가에 필요하다
4. 윈도우 집계·탐지기는 `stream/detectors.py`에 선행 프로젝트 로직을 이식 (수치가 재현되는지 대조 테스트 1개 필수)

---

## B. 설비 문서 — ✅ 확보 완료 (D2 게이트 통과)

`scripts/01b_survey_manuals.py`로 페이지 단위 조사. 결과는 `data/manuals/SURVEY.md` / `survey.csv`.

| 매뉴얼 | 페이지 | 도면 후보 | 확인된 내용 |
|---|---:|---:|---|
| `philips_rw_handbook.pdf` | 221 | 23 | 트러블슈팅 p117·121, 플로우차트 p121·152, 공압 p7~29, 냉각 p4~94, 계통도 p94~180 |
| `spotweldinc_users.pdf` | 64 | 31 | 플로우차트 p19, 공압 p2~39, 냉각 p5~47, 계통도 p6·27·41 |
| `sureweld.pdf` | 34 | 14 | **트러블슈팅 p27~29, 배선도 p12~15**, 공압 p2~33, 에러코드 p33 |
| `prospot_i4s.pdf` | 52 | 13 | 트러블슈팅 p3·6, 공압 p4~13, 전극 p4~46 |
| `prospot_i4.pdf` | 44 | 1 | 트러블슈팅 p5, 플로우차트 p10 |
| **합계** | **415** | **82** | |

육안 검증한 페이지 (휴리스틱만 믿지 않았다):

- `sureweld.pdf` p13 — **실제 배선도.** 컴포넌트 태그(MSW, TRF, CN1, TS1/TS2, S1, FOOT-PEDAL)가 **선으로만** 연결되어 있다. 텍스트 RAG로는 연결관계를 읽을 수 없다 → **기술 #3(Multimodal RAG)의 존재 근거**
- `sureweld.pdf` p28 — PROBLEM / CAUSE / REMEDY 트러블슈팅 표. 조치 카드 생성의 원본
- `spotweldinc_users.pdf` p6 — 공압 FRL 유닛 도해 + **기준값 명시**: *"Turn the adjusting knob until the air pressure gauge reads 0.5 MPa {71 psi}"*
  → **VLM의 게이지 구간 판독 결과를 매뉴얼 기준값과 대조할 수 있다.** 루프가 닫히는 지점

### 라이선스

제조사 공개 자료이므로 **PDF는 레포에 커밋하지 않는다**(`.gitignore`). `data/manuals/SOURCES.md`에 출처 URL·수집일을 기록하고, `scripts/01b_survey_manuals.py`로 누구나 재수집할 수 있게 한다.

### 전처리

```
manual.pdf
  └─ PyMuPDF
       ├─ 텍스트 페이지 → 청킹(헤딩 경계 우선, 512토큰) → bge-m3 임베딩 → pgvector
       │                                              └→ tsvector (BM25용)
       └─ 도면/플로우차트 페이지 → 200dpi PNG 렌더
                                   ├─ VLM 구조 서술 생성 → 색인
                                   └─ Files API 업로드 → file_id 저장
```

페이지 분류는 `survey.csv`의 `diagram_candidate`(이미지 있음 + 텍스트 < 900자)를 1차로 쓰고, 오분류는 `data/manuals/page_overrides.json`으로 수동 교정한다.

## C. 현장 사진 — 공개 수집은 완료, 직접 촬영만 남았다

| 용도 | 소스 | 상태 |
|---|---|---|
| **정확도 측정** (M6) | Wikimedia Commons CC/PD | ✅ `data/photos/public/` + `MANIFEST.csv` |
| **라벨 있는 벤치마크** | 공개 데이터셋 (아래) | 🟡 토큰 필요 |
| **시연** | **직접 촬영 5~8장** | ⬜ **이것만 사람이 해야 한다** |
| few-shot 참조 | 매뉴얼의 전극 팁 정상/마모 비교 이미지 | ✅ 매뉴얼 내 존재 |

### 수집 완료 — `scripts/03_fetch_cc_photos.py`

Commons API로 카테고리별 파일을 받아 **라이선스를 확인한 것만** 저장한다(CC / Public domain). 출처·저작자·라이선스는 `MANIFEST.csv`에 기록되므로 레포에 커밋 가능하고 발표자료에도 쓸 수 있다.

판독 과제 4종에 매핑된 카테고리:

| 과제 | Commons 카테고리 |
|---|---|
| ③ `gauge_zone` | Bourdon gauge / Manometers / Pressure gauges |
| ① `digital_readout` | Digital clocks / LED displays / Multimeters / Gas meters / Water meters / Digital thermometers |
| ② `indicator_light` | Light-emitting diodes / Push buttons / Control panels / Switchgear / Circuit breakers |
| ④ `qualitative_fault` | Corrosion / Rust / Cracks / Broken machinery |

> 카테고리는 추측하지 않고 Commons API로 **파일 수를 확인한 것만** 채택했다. 처음 쓴 `Category:Indicator lights` 등 여러 개가 파일 0건(하위분류만 보유)이었다.

### 라벨 있는 공개 벤치마크 (선택)

정확도에 외부 비교 기준을 붙이고 싶을 때 쓴다. **논문 arXiv 2608.17723이 아래 2번을 벤치마크로 썼으므로 같은 데이터로 수치를 비교할 수 있다.**

| 데이터셋 | 내용 | 접근 |
|---|---|---|
| [Synthetic Data for Precision Gauge Reading](https://www.kaggle.com/datasets/endava/synthetic-data-for-precision-gauge-reading) (Endava) | 합성 게이지 501장, COCO 어노테이션(바늘 끝·중심·판독값) | Kaggle 토큰 필요 |
| [Pressure Gauge Reader Data](https://www.kaggle.com/datasets/juliusgrassme/pressure-gauge-reader-data) | 실사진, train 57 / test 36 | Kaggle 토큰 필요 |
| [Analog Gauge Meter](https://universe.roboflow.com/yolo-lxxyl/analog-gauge-meter) (Roboflow, CC BY 4.0) | 게이지 163장 | Roboflow 키 필요 |
| [gauge-analog](https://universe.roboflow.com/analog-meter-reading/gauge-analog-tndze) (Roboflow) | center/gauge/max/min/tip 어노테이션 | Roboflow 키 필요 |

셋 다 계정 토큰이 필요하다. 필수는 아니다 — `MANIFEST.csv` 기반 수동 라벨링(`spike/out/review.html`)으로도 M6을 낼 수 있다.

### 직접 촬영 — 사람이 해야 하는 유일한 작업

발표 시연의 라이브 촬영용. **5~8장이면 충분하다.**

| 대상 | 대응 과제 |
|---|---|
| 보일러 압력계 / 수도·가스 계량기 | ③ 게이지 구간 |
| 보일러 에러코드 패널, 자동차 계기판 경고등 | ① 디지털 문자·코드 |
| 분전반, 설비 상태 표시등 | ② 표시등 색 |
| 배관 부식·누수 흔적, 에어컨 실외기 | ④ 정성 이상 |
| 건물 기계실·공조기 (관리실 허락) | ①②③④ — 확보되면 시연 품질이 크게 오른다 |

시연 시 **"실제 용접기에 접근할 수 없어 동형 계기로 시연합니다"**라고 밝힌다. 숨기는 것보다 신뢰를 얻는다.

### 주의

- 라이선스 불명 이미지는 `data/photos/private/`(gitignore)에만 두고, 레포에는 결과 표만 올린다
- 남의 시설을 촬영할 때는 허락을 받는다
- 사람·차량 번호판이 찍힌 사진은 사용하지 않는다
