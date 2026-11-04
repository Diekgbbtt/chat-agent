"""Tool lookup and execution for the QA loop."""

from dataclasses import dataclass

from agent.tools.discover import DiscoverTool
from agent.tools.resolve import ResolveEntityTool
from agent.tools.sparql import Observation, RunSparqlTool


@dataclass(frozen=True)
class ExecutedTool:
    name: str
    arguments: dict
    observation: Observation


class ToolRegistry:
    def __init__(self, resolve: ResolveEntityTool, discover: DiscoverTool, sparql: RunSparqlTool):
        self.tools = {"resolve_entity": resolve, "discover": discover, "run_sparql": sparql}

    def names(self) -> tuple:
        return tuple(self.tools)

    def execute(self, name: str, arguments: dict) -> ExecutedTool:
        tool = self.tools.get(name)
        if tool is None:
            return ExecutedTool(name, arguments, Observation((), error=f"unknown tool: {name}"))
        if name == "resolve_entity":
            observation = tool.run(str(arguments.get("query", "")),
                                  str(arguments.get("type", "") or ""))
        elif name == "discover":
            observation = tool.run(str(arguments.get("kind", "")),
                                  str(arguments.get("query", "")),
                                  str(arguments.get("subject", "") or ""))
        elif name == "run_sparql":
            observation = tool.run(str(arguments.get("query", "")))
        else:  # pragma: no cover - guarded by the name lookup
            observation = Observation((), error=f"unknown tool: {name}")
        return ExecutedTool(name, arguments, observation)
