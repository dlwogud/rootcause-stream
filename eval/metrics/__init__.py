"""평가 지표. 각 함수는 (case, result) → {metric: value, ...} 를 반환한다."""
from __future__ import annotations

from eval.metrics.m1_rootcause import m1_rootcause
from eval.metrics.m2_variable import m2_primary_variable
from eval.metrics.m7_citation import m7_citation_integrity

ALL_METRICS = [m1_rootcause, m2_primary_variable, m7_citation_integrity]
