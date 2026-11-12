# RootCause Stream — 진행 상태

> 재개 시 이 파일을 먼저 읽는다. 최종 갱신 2026-11-12.
> **발표자료 제출 11/28(토) 19:00 · 최종 제출 12/13(일) · 1인**

## 현재 상태 — 설계 완료, D1~D2 데이터 확보 완료

| 항목 | 상태 |
|---|---|
| 주제 선정 | ✅ RootCause Stream (7-A) |
| 설계 문서 01~13 | ✅ 완료 (선행 연구 반영해 판독 설계 1회 개정) |
| **D2 게이트 — 매뉴얼·도면** | ✅ **통과** 5종 415p, 도면 후보 82장 |
| 공개 사진 (측정용) | ✅ Commons CC/PD, `data/photos/public/` + MANIFEST.csv |
| 스파이크 코드 | ✅ `spike/vlm_reading_spike.py` (실행만 남음) |
| **스파이크 실행** | ⬜ **API 키 필요** |
| **직접 촬영 (시연용)** | ⬜ **사람이 해야 함** |
| 공정 시계열 | ✅ 보유 (`~/kamp-welding/data/raw/`) |
| 서비스 코드 | ⬜ 미착수 |

## 다음에 할 일 — 순서대로

### 1. 스파이크 실행 (API 키만 있으면 바로)

```bash
cd ~/rootcause-stream
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...

python3 spike/vlm_reading_spike.py --repeats 3          # haiku-4.5
open spike/out/review.html                               # 정답 라벨링 → labels.csv
python3 spike/vlm_reading_spike.py --score spike/out/labels.csv

# 비교 실험
python3 spike/vlm_reading_spike.py --model claude-sonnet-5 --tag sonnet
python3 spike/vlm_reading_spike.py --blur 3 --tag blur3   # 논문의 지배적 실패요인 재현
```

측정되는 것: 과제별 정확도 / 자기일관성 / confidence 타당성 / 블러 민감도 / 모델 비교.
**결과에 따라 `docs/04-llm-techniques.md`의 판독 과제 4종을 조정한다.**

### 2. 직접 촬영 5~8장 (사람만 가능)

보일러 압력계 · 에러코드 패널 · 분전반/표시등 · 배관 부식 → `data/photos/demo/`.
건물 기계실을 찍을 수 있으면 시연 품질이 크게 오른다(관리실 허락).

### 3. D3 — 공정 데이터 이식

`~/kamp-welding`의 2σ 관리도 + kNN 로직을 `app/stream/detectors.py`로 옮기고
**선행 수치 재현 테스트**(실제 shift 3/3, 오경보 0/5)를 통과시킨다.

## 주의사항

- **평가 하네스를 D5(11/16)까지 만든다.** 발표자료의 모든 숫자가 여기서 나온다
- **Kafka/Flink는 2단계(11/29~).** 먼저 세우고 싶은 충동을 참는다 — 점수는 LLM/VLM 루프에 있다
- **confidence 단독 게이팅 금지.** 선행 연구에서 confidence ≥0.99 오답이 보고됐다.
  abstention + 자기일관성 + 교차근거 3중 장치를 쓴다 (`docs/04-llm-techniques.md` §8)
- **수치 환산 판독 금지.** 구간·범주 판정만 (zero-shot 오차 21~39%)
- 라이선스 불명 이미지를 커밋하거나 발표자료에 넣지 않는다. 매뉴얼 PDF도 gitignore
- `if_observed`는 사진 수신 **전에** 저장한다 — M4(정보이득) 측정의 전제
- 모델 파라미터 분기는 한 곳에만: Opus5/Sonnet5 = `effort`, Haiku 4.5 = `budget_tokens`
- `citations` + `output_config.format` 동시 사용 불가 → 호출 2개로 분리
- **라이브 촬영 시연 리허설 3회** (D16)

## 게이트

| 시점 | 통과 조건 | 상태 |
|---|---|---|
| D1 (11/12~13) | VLM 판독 과제 범위 확정 | 🟡 선행 연구로 1차 확정, 스파이크 실측 대기 |
| D2 (11/13) | 도면 3장 + 플로우차트 2개 | ✅ **통과** (82장) |
| D5 (11/16) | 평가 하네스가 숫자를 출력 | ⬜ |
| D9 (11/20) | **end-to-end 루프 1회 완주** | ⬜ |
| D14 (11/25) | ablation 3개 숫자 확보 | ⬜ |
| 12/7 | PyFlink 채택 판정 | ⬜ |
