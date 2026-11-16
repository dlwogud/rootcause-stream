from app.agent.tools.cases import recall_cases, signature, store_case
from app.agent.tools.diagram import lookup_diagram
from app.agent.tools.manual import search_manual
from app.agent.tools.timeseries import query_timeseries

REGISTRY = {
    "query_timeseries": query_timeseries,
    "search_manual": search_manual,
    "lookup_diagram": lookup_diagram,
    "recall_cases": recall_cases,
}
