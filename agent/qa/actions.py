"""OpenAI function schemas for the graph tools and the response control tool."""

import copy

RESOLVE_ENTITY = {
    "type": "function",
    "function": {
        "name": "resolve_entity",
        "description": ("Find candidate entity QIDs from a film or person label. "
                        "Filter by a type label or QID when the name is ambiguous."),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "type": {"type": "string"},
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

DISCOVER = {
    "type": "function",
    "function": {
        "name": "discover",
        "description": ("Search the graph vocabulary for a relation or type that the schema card "
                        "does not carry. Pass a QID as subject to see the relations used by that "
                        "type or entity."),
        "parameters": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["relation", "type"]},
                "query": {"type": "string"},
                "subject": {"type": ["string", "null"]},
            },
            "required": ["kind", "query"],
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

GRAPH_TOOLS = [RESOLVE_ENTITY, DISCOVER, RUN_SPARQL]


def available_tools(decision) -> list:
    tools = [copy.deepcopy(tool) for tool in GRAPH_TOOLS] if decision.tools_enabled else []
    tools.append(copy.deepcopy(SUBMIT_RESPONSE))
    return tools
