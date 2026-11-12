# 매뉴얼 출처

PDF 본체는 레포에 커밋하지 않는다(제조사 공개 자료, 재배포 권한 불명). 아래 URL로 재수집하고
`python3 scripts/01b_survey_manuals.py`로 조사 결과를 재생성한다.

수집일: 2026-11-12

| 파일 | 페이지 | 출처 |
|---|---:|---|
| `prospot_i4s.pdf` | 52 | https://prospot.com/pdf/MNL-i4s%20v1.5.pdf |
| `prospot_i4.pdf` | 44 | https://prospot.com/pdf/i4-instruction-manual.pdf |
| `spotweldinc_users.pdf` | 64 | https://spotweldinc.com/PDFs/SWI_Machinery_Users_Manual_2025.09.25.pdf |
| `sureweld.pdf` | 34 | https://www.westermans.com/assets/products/18006/files/5587/sureweld-welder-manual%20(1)1.pdf |
| `philips_rw_handbook.pdf` | 221 | https://frank.pocnet.net/other/sos/Philips_ResistanceWelding_Handbook.pdf |

## 재수집

```bash
mkdir -p data/manuals/pdf && cd data/manuals/pdf
curl -sSL -A 'Mozilla/5.0' -o prospot_i4s.pdf        'https://prospot.com/pdf/MNL-i4s%20v1.5.pdf'
curl -sSL -A 'Mozilla/5.0' -o prospot_i4.pdf         'https://prospot.com/pdf/i4-instruction-manual.pdf'
curl -sSL -A 'Mozilla/5.0' -o spotweldinc_users.pdf  'https://spotweldinc.com/PDFs/SWI_Machinery_Users_Manual_2025.09.25.pdf'
curl -sSL -A 'Mozilla/5.0' -o sureweld.pdf           'https://www.westermans.com/assets/products/18006/files/5587/sureweld-welder-manual%20(1)1.pdf'
curl -sSL -A 'Mozilla/5.0' -o philips_rw_handbook.pdf 'https://frank.pocnet.net/other/sos/Philips_ResistanceWelding_Handbook.pdf'
cd ../../.. && python3 scripts/01b_survey_manuals.py
```

## 발표자료에 쓸 때

이미지를 발표자료에 넣으려면 제조사에 확인하거나, 직접 그린 재현 도식으로 대체한다.
조사 결과(`SURVEY.md`)와 페이지 번호 인용은 문제없다.

## 참고 문헌

- *Vision-Language Models for Analog Gauge Reading: An Empirical Study of Specialization,
  Transfer and Reliability*, arXiv:2608.17723 — 판독 과제 범위와 confidence 게이팅 설계의 근거.
  `docs/04-llm-techniques.md` §8 참조.
