"""평가 지표. 각 함수는 (case, result) → {metric: value, ...} 를 반환한다.

Tier 별로 주 지표가 다르다 — 정답의 성격이 다르기 때문이다.
  Tier A : M9 (적절한 보류 + 가르는 관측 요청). 원인이 특정되지 않는 사건이다
  Tier B : M2 (주 변수 식별). 정답이 '무엇을 조작했는가' 라 M1 은 참고용
  Tier C : M1 (근본원인 정확도). 정답이 명확한 공정·데이터 현상이다
"""
from eval.metrics.m1_rootcause import m1_rootcause
from eval.metrics.m2_variable import m2_primary_variable
from eval.metrics.m7_citation import m7_citation_integrity
from eval.metrics.m9_abstention import m9_abstention

ALL_METRICS = [m1_rootcause, m2_primary_variable, m7_citation_integrity, m9_abstention]
