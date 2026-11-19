from app.agent.tools.cases import recall_cases, signature, store_case
from app.agent.tools.diagram import lookup_diagram
from app.agent.tools.manual import search_manual
from app.agent.tools.photo import read_photo
from app.agent.tools.sql import query_sql
from app.agent.tools.timeseries import query_timeseries

REGISTRY = {
    "query_timeseries": query_timeseries,
    "search_manual": search_manual,
    "lookup_diagram": lookup_diagram,
    "recall_cases": recall_cases,
    "query_sql": query_sql,          # 선택 도구 — Ablation.extra_tools 로 켤 때만 Agent 에게 보인다
}
# read_photo 는 REGISTRY 에 넣지 않는다. Agent 가 직접 호출하는 도구가 아니라
# 촬영 요청에 대한 응답으로 **루프 바깥에서** 실행되는 것이다 (비동기 중단점).
