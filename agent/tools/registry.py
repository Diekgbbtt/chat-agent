"""Tool lookup and execution for the QA loop."""

from dataclasses import dataclass

from agent.tools.resolve import ResolveEntityTool
from agent.tools.sparql import Observation, RunSparqlTool


@dataclass(frozen=True)
class ExecutedTool:
    name: str
    arguments: dict
    observation: Observation


class ToolRegistry:
    def __init__(self, resolve: ResolveEntityTool, sparql: RunSparqlTool):
        self.tools = {"resolve_entity": resolve, "run_sparql": sparql}

    def names(self) -> tuple:
        return tuple(self.tools)

    def execute(self, name: str, arguments: dict) -> ExecutedTool:
        tool = self.tools.get(name)
        if tool is None:
            return ExecutedTool(name, arguments, Observation((), error=f"unknown tool: {name}"))
        if name == "resolve_entity":
            observation = tool.run(str(arguments.get("query", "")), int(arguments.get("limit", 5)))
        elif name == "run_sparql":
            observation = tool.run(str(arguments.get("query", "")))
        else:  # pragma: no cover - guarded by the name lookup
            observation = Observation((), error=f"unknown tool: {name}")
        return ExecutedTool(name, arguments, observation)
