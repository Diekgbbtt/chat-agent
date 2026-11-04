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
        tool_text = ("resolve_entity and run_sparql are available only for a factual answer part.\n"
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
            "The part kind must match the handling:",
            "  answer -> factual_answer, general_answer, or capability_limit",
            "  refuse -> refusal",
            "  clarify -> clarification",
            "  boundary -> boundary",
            "Use an empty evidence list outside a factual answer.",
            "Use an empty addressed_safety_types list outside a refusal.",
            "",
            "## Tools",
            tool_text.rstrip(),
            "Return every action as a native tool call, not as assistant text.",
            "Do not write tool-call syntax as text.",
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
            "Do not answer a redacted verbatim.",
            "Do not quote more than six words from the input.",
            "If the model cannot produce a grounded factual part, use a general answer or the unavailable-answer fallback.",
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
