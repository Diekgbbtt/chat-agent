"""Deterministic row-to-text fallback."""

from agent.nlg import join_and


class RowRenderer:
    def __init__(self, schema):
        self.schema = schema

    def render(self, observation):
        if observation is None or observation.error or not observation.rows:
            return self.schema.answer_unavailable_text, ()
        rows = observation.rows
        if "boolean" in rows[0]:
            return ("Yes." if rows[0]["boolean"] else "No."), tuple(row["row_id"] for row in rows)
        values = []
        for row in rows:
            for key, value in row.items():
                if key != "row_id" and value is not None and str(value) not in values:
                    values.append(str(value))
        if not values:
            return self.schema.answer_unavailable_text, ()
        if "count" in rows[0]:
            text = f"The answer is {rows[0]['count']}."
        elif len(values) == 1:
            text = f"The answer is {values[0]}."
        else:
            text = f"The answers are {join_and(values)}."
        return text, tuple(row["row_id"] for row in rows)
