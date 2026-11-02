"""OpenAI function schemas for the graph tools and the response control tool."""

import copy

RESOLVE_ENTITY = {
    "type": "function",
    "function": {
        "name": "resolve_entity",
        "description": "Find candidate entity QIDs from a film or person label. Exact, prefix, and contains matches only.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        },
    },
}

RUN_SPARQL = {
    "type": "function",
    "function": {
        "name": "run_sparql",
        "description": "Run one read-only SPARQL query and return labelled rows with row IDs.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}

_PART = {
    "type": "object",
    "properties": {
        "verbatim_index": {"type": "integer"},
        "kind": {"type": "string",
                 "enum": ["factual_answer", "general_answer", "capability_limit",
                          "refusal", "clarification", "boundary"]},
        "text": {"type": "string"},
        "evidence_row_ids": {"type": "array", "items": {"type": "string"}},
        "addressed_safety_types": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verbatim_index", "kind", "text", "evidence_row_ids",
                 "addressed_safety_types"],
}

SUBMIT_RESPONSE = {
    "type": "function",
    "function": {
        "name": "submit_response",
        "description": "Submit one ordered part per verbatim. This is the only way to finish.",
        "parameters": {
            "type": "object",
            "properties": {"parts": {"type": "array", "items": _PART}},
            "required": ["parts"],
        },
    },
}

GRAPH_TOOLS = [RESOLVE_ENTITY, RUN_SPARQL]


def available_tools(decision) -> list:
    tools = [copy.deepcopy(tool) for tool in GRAPH_TOOLS] if decision.tools_enabled else []
    tools.append(copy.deepcopy(SUBMIT_RESPONSE))
    return tools
