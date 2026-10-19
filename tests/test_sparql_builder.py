from agent import sparql_builder as sb

P57 = "http://www.wikidata.org/prop/direct/P57"


def test_directions():
    assert f"<http://www.wikidata.org/entity/Q47703> <{P57}> ?x" in sb.lookup("Q47703", P57, "out")
    assert f"?x <{P57}> <http://www.wikidata.org/entity/Q193628>" in sb.lookup("Q193628", P57, "in")
    assert sb.lookup("Q1", P57, "out").endswith(f"LIMIT {sb.LIMIT}")


def test_superlative_order():
    assert "MIN(?d)" in sb.superlative("Q1", P57, "in", "ASC") and "ORDER BY ASC(?date)" in sb.superlative("Q1", P57, "in", "ASC")
    assert "MAX(?d)" in sb.superlative("Q1", P57, "in", "DESC")


P166 = "http://www.wikidata.org/prop/direct/P166"


def test_count_filters_films_only_for_film_credits():
    assert "?x wdt:P31 wd:Q11424" in sb.count("Q193628", P57, "in")
    assert "?x wdt:P31 wd:Q11424" not in sb.count("Q103569", P166, "out")
    assert "?x wdt:P31 wd:Q11424" not in sb.count("Q103569", P57, "out")


def test_complement_directions():
    film = sb.complement("Q56094", P57, "in")
    assert f"?x wdt:P31 wd:Q11424 . FILTER NOT EXISTS {{ ?x <{P57}> <http://www.wikidata.org/entity/Q56094> }}" in film
    people = sb.complement("Q103569", P57, "out")
    assert f"?f <{P57}> ?x" in people
    assert f"FILTER NOT EXISTS {{ <http://www.wikidata.org/entity/Q103569> <{P57}> ?x }}" in people


def test_complement_actor_universe_scopes_person_answers_to_cast_members():
    q = sb.complement("Q103569", P57, "out", universe="actor")
    assert "?f wdt:P161 ?x . ?x wdt:P31 wd:Q5 ." in q
    assert f"FILTER NOT EXISTS {{ <http://www.wikidata.org/entity/Q103569> <{P57}> ?x }}" in q


def test_complement_actor_universe_only_applies_to_the_director_relation():
    q = sb.complement("Q103569", "http://www.wikidata.org/prop/direct/P166", "out", universe="actor")
    assert "wdt:P161" not in q


def test_complement_extra_films_are_all_excluded():
    q = sb.complement("Q103569", P57, "out", others=("Q47703",))
    assert q.count("FILTER NOT EXISTS") == 2
    assert "<http://www.wikidata.org/entity/Q47703>" in q
    assert "<http://www.wikidata.org/entity/Q103569>" in q


def test_claim_ask():
    assert sb.claim("Q47703", P57, "Q56094") == \
        f"ASK {{ <http://www.wikidata.org/entity/Q47703> <{P57}> <http://www.wikidata.org/entity/Q56094> }}"


def test_queries_run(movies_kg):
    for query in (sb.lookup("Q47703", P57, "out"), sb.count("Q193628", P57, "in"),
                  sb.superlative("Q193628", P57, "in", "ASC"), sb.degree("Q47703"),
                  sb.complement("Q56094", P57, "in"), sb.complement("Q103569", P57, "out"),
                  sb.complement("Q103569", P57, "out", universe="actor"),
                  sb.complement("Q103569", P57, "out", others=("Q47703",))):
        movies_kg.query(query)
    assert movies_kg.query(sb.has_facts("Q47703", P57, "out")) is True
    assert movies_kg.query(sb.has_facts("Q47703", P57, "in")) is False
    assert movies_kg.query(sb.claim("Q47703", P57, "Q56094")) is True
