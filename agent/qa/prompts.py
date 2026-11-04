"""Build the QA system and user prompts from a decision."""

import json


class PromptBuilder:
    def __init__(self, schema_card, schema):
        self.schema_card = schema_card
        self.schema = schema

    def plan_view(self, decision) -> list:
        redacted = {plan.index for plan in decision.verbatim_plan if plan.redacted}
        view = []
        for plan in decision.verbatim_plan:
            relationship = None
            if plan.relationship is not None:
                entity = plan.relationship.entity
                if plan.relationship.target_verbatim_index in redacted:
                    entity = None
                relationship = {
                    "target_verbatim_index": plan.relationship.target_verbatim_index,
                    "entity": entity,
                    "status": plan.relationship.status,
                }
            item = {
                "index": plan.index,
                "handling": plan.handling,
                "safety": plan.label.safety,
                "unsafe_types": list(plan.label.unsafe_types),
                "scope": plan.label.scope,
                "text": None if plan.redacted else plan.text,
                "redacted": plan.redacted,
                "ambiguous": plan.ambiguous,
                "relationship": relationship,
            }
            if not plan.redacted:
                item["rationale"] = {"safety": plan.rationale.safety, "scope": plan.rationale.scope}
            view.append(item)
        return view

    def system_prompt(self, decision) -> str:
        tool_text = ("resolve_entity, discover, and run_sparql are available only for a factual answer part.\n"
                     if decision.tools_enabled else
                     "No graph tool is available. Do not state a graph fact.\n")
        return "\n".join([
            "## Role",
            "You are a movie assistant. You answer only from the knowledge graph.",
            "",
            "## Grounding",
            "Never use world knowledge. Never invent a value, label, date, or number.",
            "Every factual answer part must cite row IDs from a run_sparql observation.",
            "",
            "## Workflow",
            "Follow this fixed order for every answerable verbatim.",
            "1. Resolve: call resolve_entity before run_sparql. Never run_sparql with a label; use the QID from the selected row.",
            '   Pass type="film" or type="human" when the name may be ambiguous.',
            "2. Discover: if the card lacks the relation or type, call discover. "
            'kind="relation" searches property labels and aliases. kind="type" searches class labels.',
            "   Use the returned relation or type ID.",
            "3. Query: call run_sparql with the selected QID and the relation ID from the card or discover.",
            "4. Cite and submit: cite the row IDs and call submit_response.",
            "",
            'Worked example: "Who directed Jaws?"',
            '1. resolve_entity(query="Jaws", type="film") -> e0: qid=Q189505, label=Jaws, kind=film.',
            '2. run_sparql(query="SELECT ?director WHERE { wd:Q189505 wdt:P57 ?director }") '
            "-> r0: director=Steven Spielberg.",
            '3. submit_response({"parts": [{"verbatim_index": 0, "kind": "factual_answer", '
            '"text": "Jaws was directed by Steven Spielberg.", "evidence_row_ids": ["r0"], '
            '"addressed_safety_types": []}]})',
            "",
            'Worked discovery example: "What is the MPA rating of Jaws?"',
            '1. resolve_entity(query="Jaws", type="film") -> e0: qid=Q189505, label=Jaws, kind=film.',
            '2. discover(kind="relation", query="MPA rating", subject="Q11424") '
            "-> d0: id=P1657, label=MPA film rating, direction=out.",
            '3. run_sparql(query="SELECT ?rating WHERE { wd:Q189505 wdt:P1657 ?rating }") '
            "-> r0: rating=PG.",
            '4. submit_response({"parts": [{"verbatim_index": 0, "kind": "factual_answer", '
            '"text": "Jaws has an MPA rating of PG.", "evidence_row_ids": ["r0"], '
            '"addressed_safety_types": []}]})',
            "",
            "## Classification format",
            "The decision carries an overview and an ordered verbatim plan.",
            "Each verbatim has safety, unsafe_types, scope, a handling, an ambiguous flag, and an optional relationship.",
            "The plan label is the effective label after relationship inheritance.",
            "A redacted verbatim has no text. Do not reconstruct it.",
            "",
            "## Relationships",
            "Use the plan label. Do not inherit or reclassify.",
            "A relationship target names the verbatim that supplies the missing meaning.",
            "An ambiguous verbatim with a resolved target already carries its effective label.",
            "An ambiguous verbatim with a missing target has a clarify handling.",
            "",
            "## Reply contract",
            "Return one part per verbatim, in input order.",
            "The part kind must match the handling and the cause:",
            "  answer -> factual_answer when a cited graph row answers the verbatim.",
            "  answer -> capability_limit for a recommendation, ranking, or opinion request.",
            "  answer -> general_answer only when the graph has no data after three attempts.",
            "  refuse -> refusal",
            "  clarify -> clarification",
            "  boundary -> boundary",
            "general_answer is not a first fallback.",
            "After three attempts (resolve, discover, query), a general_answer must say that the graph has "
            "no data and ask for a more specific question.",
            "A general_answer must not use world knowledge.",
            'Example general_answer: "I do not have graph data for that question. '
            'Ask a more specific question about the film, such as its composer or release date."',
            "Use an empty evidence list outside a factual answer.",
            "Use an empty addressed_safety_types list outside a refusal.",
            "",
            "## Tools",
            tool_text.rstrip(),
            "Return every action as a native tool call, not as assistant text.",
            "Do not write tool-call syntax as text. A message that writes submit_response([...]) is invalid.",
            'Exact submit call: {"name": "submit_response", "arguments": {"parts": [...]}}',
            "Call submit_response to finish. Do not repeat a tool call.",
            "",
            "## Policy",
            f"Aggregate action: {decision.action}.",
            f"Graph tools enabled: {decision.tools_enabled}.",
            "Safety is assessed before scope. A boundary applies only to its own verbatim.",
            "A safe answerable verbatim is still answered when another verbatim is unsafe or out of scope.",
            "",
            "## Schema card",
            self.schema_card.render(),
            "",
            "## Stop rules",
            "Call submit_response with every part.",
            "Use at most six graph tool steps and respect the 20-second deadline.",
            "Do not answer a redacted verbatim.",
            "Do not quote more than six words from the input.",
            "Three failed attempts are the only reason for a general answer. Never answer from memory.",
        ])

    def user_prompt(self, decision) -> str:
        overview = None
        if decision.overview is not None:
            overview = {"summary": decision.overview.summary}
        return json.dumps({
            "overview": overview,
            "action": decision.action,
            "tools_enabled": decision.tools_enabled,
            "verbatim_plan": self.plan_view(decision),
        }, ensure_ascii=False, indent=2)

    def build(self, decision, verdict=None) -> list:
        return [{"role": "system", "content": self.system_prompt(decision)},
                {"role": "user", "content": self.user_prompt(decision)}]
