# 원본 데이터

이 디렉터리의 원본 데이터는 **본 저장소에 포함하지 않는다.** KAMP(인공지능 제조 플랫폼)가
제공한 데이터이고, [KAMP 이용약관](https://www.kamp-ai.kr/agreement)에 재배포에 관한 조항이
없어 재배포 권한이 확인되지 않기 때문이다. 선행 프로젝트 `kamp-welding` 도 같은 이유로 제외했다.

## 받는 방법

1. https://www.kamp-ai.kr 로그인
2. 제조AI데이터셋 → **용접기 AI 데이터셋**
3. `Welding Data Set_01.xlsx` 를 이 디렉터리에 둔다

## 받은 뒤 전부 재생성하기

```bash
python3 -m eval.cases          # 평가 사건 + eval/cases/data/*.csv
python3 -m eval.tier_d         # Tier D 사건
python3 scripts/90_verify_design.py   # 설계 검증 (선행 수치 재현 포함)
```

매뉴얼 색인(검색·도면 RAG)은 `data/manuals/SOURCES.md` 의 재수집 명령 후
`scripts/01_index_manuals.py` → `scripts/02_describe_diagrams.py` 순서로 만든다.
