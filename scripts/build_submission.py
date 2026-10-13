"""
Assembles a submission folder from the single codebase in agent/.

    python scripts/build_submission.py 2          -> "Project Submission 2/"
    python scripts/build_submission.py final      -> "Final Project Submission/"

Writes main.py (a thin launcher), copies agent/ into additional_files/agent/ and
copies requirements.txt. report.pdf and presentation.pdf are left untouched.
Credentials are NOT copied: put a .env next to main.py on Nuvolos (see README).
"""

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LAUNCHER = '''"""Starts the chatbot. Do not rename: the online evaluation runs this file."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "additional_files"))

from agent.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
'''

TEMPLATE_MARKER = "# Add the code required to run your chatbot here."


def target_folder(stage: str) -> Path:
    if stage.lower() == "final":
        return ROOT / "Final Project Submission"
    return ROOT / f"Project Submission {stage}"


def build(dest: Path, force: bool = False) -> None:
    if not dest.is_dir():
        sys.exit(f"Submission folder not found: {dest}")
    main_py = dest / "main.py"
    if main_py.exists():
        current = main_py.read_text(encoding="utf-8")
        if current != LAUNCHER and TEMPLATE_MARKER not in current and not force:
            sys.exit(f"{main_py} has custom content; rerun with --force to overwrite it.")
    main_py.write_text(LAUNCHER, encoding="utf-8")

    package_dest = dest / "additional_files" / "agent"
    if package_dest.exists():
        shutil.rmtree(package_dest)  # only ever our own previous copy
    shutil.copytree(ROOT / "agent", package_dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(ROOT / "requirements.txt", dest / "requirements.txt")
    print(f"Built {dest}")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stage", help="stage number (1-4) or 'final'")
    parser.add_argument("--dest", type=Path, help="build into this folder instead (for testing)")
    parser.add_argument("--force", action="store_true", help="overwrite a customised main.py")
    args = parser.parse_args(argv)
    build(args.dest or target_folder(args.stage), force=args.force)


if __name__ == "__main__":
    main()
