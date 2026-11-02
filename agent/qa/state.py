"""State shared by the QA loop, validator, and composer."""

from dataclasses import dataclass, field


@dataclass
class AgentState:
    verdict: object
    decision: object
    observations: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    step_count: int = 0
    tool_signatures: set = field(default_factory=set)

    @property
    def allowed_row_ids(self) -> set:
        return {row_id for item in self.observations for row_id in item.observation.row_ids}

    @property
    def tool_queries(self) -> list:
        queries = []
        for item in self.observations:
            query = item.arguments.get("query") if isinstance(item.arguments, dict) else None
            if isinstance(query, str):
                queries.append(query)
        return queries
