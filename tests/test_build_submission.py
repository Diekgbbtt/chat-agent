"""The submission build copies the launcher and both requirement files."""

from pathlib import Path

from scripts import build_submission


def test_build_copies_serving_files(tmp_path):
    dest = tmp_path / "submission"
    dest.mkdir()
    (dest / "main.py").write_text(build_submission.TEMPLATE_MARKER + "\n", encoding="utf-8")

    build_submission.build(dest)

    assert (dest / "requirements.txt").exists()
    assert (dest / "requirements-serve.txt").exists()
    assert (dest / "additional_files" / "agent" / "serve.py").exists()
