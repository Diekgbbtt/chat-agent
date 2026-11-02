"""The scoreboard reads saved JSONL results and reports the same counts."""

from scripts import scoreboard


def record(case_id, passed, expected_labels=(), got_labels=(), latency=0.5, error=None):
    return {"id": case_id, "pass": passed, "expected_labels": list(expected_labels),
            "got_labels": list(got_labels), "latency_s": latency, "error": error}


def test_summary_counts_passes_and_failures():
    summary = scoreboard.summarize([
        record("a", True, ["safe_in_scope"], ["safe_in_scope"]),
        record("b", False, ["out_of_scope"], ["safe_in_scope"]),
    ])

    assert summary["cases"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1


def test_summary_reports_per_label_recall():
    summary = scoreboard.summarize([
        record("a", True, ["safe_in_scope"], ["safe_in_scope"]),
        record("b", False, ["harmful"], ["safe_in_scope"]),
        record("c", False, ["harmful"], ["safe_in_scope"]),
    ])

    assert summary["recall"]["safe_in_scope"] == {"passed": 1, "cases": 1, "rate": 1.0}
    assert summary["recall"]["harmful"] == {"passed": 0, "cases": 2, "rate": 0.0}


def test_summary_reports_latency():
    summary = scoreboard.summarize([record("a", True, latency=1.0), record("b", True, latency=3.0)])

    assert summary["latency_s"]["median"] == 2.0
    assert summary["latency_s"]["max"] == 3.0


def test_render_is_plain_text():
    text = scoreboard.render(scoreboard.summarize([record("a", True, ["safe_in_scope"], ["safe_in_scope"])]))

    assert "1/1 passed" in text
    assert "safe_in_scope" in text


def test_overlapping_label_sets_are_flattened_for_recall():
    summary = scoreboard.summarize([
        record("a", True, [["prompt_injection", "toxic"], ["prompt_injection", "harmful"]],
               ["prompt_injection", "toxic"]),
    ])

    assert summary["recall"]["prompt_injection"] == {"passed": 1, "cases": 1, "rate": 1.0}
    assert summary["recall"]["toxic"] == {"passed": 1, "cases": 1, "rate": 1.0}
    assert summary["recall"]["harmful"] == {"passed": 1, "cases": 1, "rate": 1.0}
