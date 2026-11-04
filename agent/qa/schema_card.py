"""Render the curated RDF schema card for the QA system prompt."""

import json
from pathlib import Path

GROUPS = ("film", "person", "metadata")


class SchemaCard:
    def __init__(self, data: dict):
        self.data = data

    @classmethod
    def load(cls, path) -> "SchemaCard":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def render(self) -> str:
        lines = ["Prefixes:"]
        lines.extend(f"  {name}: <{iri}>" for name, iri in self.data["prefixes"].items())
        lines.append("Core classes:")
        lines.extend(f"  {item['id']} = {item['label']}" for item in self.data["classes"])
        lines.append("Core properties:")
        for group in GROUPS:
            items = [item for item in self.data["properties"] if item.get("group") == group]
            if not items:
                continue
            lines.append(f"  {group}:")
            lines.extend(f"    {item['id']} = {item['label']} ({item['shape']})" for item in items)
        lines.append("Value shapes:")
        lines.extend(f"  {item['name']}: {item['description']}" for item in self.data["value_shapes"])
        lines.append("Query examples (replace a variable with a resolved QID before run_sparql):")
        for item in self.data["examples"]:
            lines.append(f"  {item['question']}")
            lines.append(f"    {item['sparql']}")
        return "\n".join(lines)
