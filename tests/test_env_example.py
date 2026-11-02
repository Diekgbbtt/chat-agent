"""Every environment setting has a documented example entry."""

import re
from pathlib import Path

CONFIG = Path("agent/config.py").read_text(encoding="utf-8")
EXAMPLE = Path(".env.example").read_text(encoding="utf-8")

NAMES = set(re.findall(
    r'(?:os\.environ\.get|_int_env|_bool_env|_float_env)\(\s*"([A-Z][A-Z0-9_]+)"',
    CONFIG,
))


def example_keys() -> set:
    keys = set()
    for line in EXAMPLE.splitlines():
        line = line.strip()
        if line.startswith("#"):
            line = line[1:].strip()
        key, separator, _ = line.partition("=")
        if separator and re.fullmatch(r"[A-Z][A-Z0-9_]+", key):
            keys.add(key)
    return keys


def test_every_setting_has_an_example_entry():
    missing = sorted(NAMES - example_keys())

    assert NAMES
    assert not missing, f"missing from .env.example: {missing}"


def test_example_has_no_unknown_setting_names():
    unknown = sorted(example_keys() - NAMES)

    assert not unknown, f"unknown in .env.example: {unknown}"
