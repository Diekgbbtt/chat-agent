"""The adversarial policy suite is well-formed and covers every e2e branch."""

import json
from pathlib import Path

from agent.guard.schema import load_schema
from scripts.adversarial.build_policy_e2e import CASES
from scripts.adversarial.policy_branches import ALL_REQUIRED, BRANCHES, E2E_REQUIRED, UNIT_REQUIRED

SCHEMA = load_schema("agent/data/guardrails.json")


def test_the_committed_jsonl_matches_the_builder():
    path = Path("evals/adversarial/policy_e2e.jsonl")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]

    assert rows == CASES


def test_case_ids_are_unique():
    ids = [case["id"] for case in CASES]
    assert len(ids) == len(set(ids))


def test_every_declared_branch_exists():
    for case in CASES:
        assert case["branches"], case["id"]
        for branch in case["branches"]:
            assert branch in BRANCHES, (case["id"], branch)


def test_declared_cases_cover_every_model_driven_branch():
    declared = {branch for case in CASES for branch in case["branches"]}
    assert not (set(E2E_REQUIRED) - declared)


def test_every_branch_has_an_owner():
    assert set(ALL_REQUIRED) == set(BRANCHES)
    assert not (set(UNIT_REQUIRED) - set(BRANCHES))


def test_case_shape_is_valid():
    for case in CASES:
        assert case["mode"] == "llm"
        assert isinstance(case["input"], str) and case["input"].strip()
        expected = case["expected"]
        assert expected["action"] in ("answer", "refuse", "clarify", "out_of_scope")
        assert expected["min_spans"] <= expected["max_spans"]
        folded = case["input"].casefold()
        for entry in expected.get("plan", []):
            assert entry["span_contains"].casefold() in folded, (case["id"], entry)
            if "types" in entry:
                assert all(name in SCHEMA.safety_types for name in entry["types"]), (case["id"], entry)
            if "own_types" in entry:
                assert all(name in SCHEMA.safety_types for name in entry["own_types"]), (case["id"], entry)
            if "any_of_types" in entry:
                assert all(name in SCHEMA.safety_types
                           for option in entry["any_of_types"] for name in option), (case["id"], entry)
            if "any_of_own_types" in entry:
                assert all(name in SCHEMA.safety_types
                           for option in entry["any_of_own_types"] for name in option), (case["id"], entry)
            if "scope" in entry:
                assert entry["scope"] in SCHEMA.scopes, (case["id"], entry)
            if "own_scope" in entry:
                assert entry["own_scope"] in SCHEMA.scopes, (case["id"], entry)
        for pair in expected.get("must_separate", []):
            for phrase in pair:
                assert phrase.casefold() in folded, (case["id"], phrase)
        for phrase in expected.get("must_cover", []):
            assert phrase.casefold() in folded, (case["id"], phrase)
        for entry in expected.get("relationships", []):
            assert entry["source_contains"].casefold() in folded, (case["id"], entry)
            if "target_contains" in entry:
                assert entry["target_contains"].casefold() in folded, (case["id"], entry)


def test_policy_decisions_are_graded_not_exploratory():
    probes = {case["id"] for case in CASES if case["expected"].get("probe")}
    taxonomy = {case["id"] for case in CASES if case["expected"].get("taxonomy_probe")}

    assert probes == set()
    assert taxonomy == set()


def test_gender_mismatch_is_non_ambiguous_and_has_no_relationship():
    case = next(case for case in CASES if case["id"] == "gender-mismatch-assumption")
    child = next(entry for entry in case["expected"]["plan"]
                 if entry["span_contains"] == "Who is she?")

    assert child["ambiguous"] is False
    assert child["own_types"] == []
    assert case["expected"]["no_relationships"] is True
