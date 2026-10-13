from agent import sparql_builder as sb

P57 = "http://www.wikidata.org/prop/direct/P57"


def test_directions():
    assert f"<http://www.wikidata.org/entity/Q47703> <{P57}> ?x" in sb.lookup("Q47703", P57, "out")
    assert f"?x <{P57}> <http://www.wikidata.org/entity/Q193628>" in sb.lookup("Q193628", P57, "in")
    assert sb.lookup("Q1", P57, "out").endswith(f"LIMIT {sb.LIMIT}")


def test_superlative_order():
    assert "MIN(?d)" in sb.superlative("Q1", P57, "in", "ASC") and "ORDER BY ASC(?date)" in sb.superlative("Q1", P57, "in", "ASC")
    assert "MAX(?d)" in sb.superlative("Q1", P57, "in", "DESC")


def test_queries_run(movies_kg):
    for query in (sb.lookup("Q47703", P57, "out"), sb.count("Q193628", P57, "in"),
                  sb.superlative("Q193628", P57, "in", "ASC"), sb.degree("Q47703")):
        movies_kg.query(query)
    assert movies_kg.query(sb.has_facts("Q47703", P57, "out")) is True
    assert movies_kg.query(sb.has_facts("Q47703", P57, "in")) is False
