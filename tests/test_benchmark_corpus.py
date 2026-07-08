"""Benchmark corpus integrity: all categories present, cases valid, ids unique."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "benchmarks"))

import run as benchmark_runner  # noqa: E402

CORPUS = REPO / "benchmarks" / "corpus"
CATEGORIES = benchmark_runner.CATEGORIES


def test_all_nine_categories_present() -> None:
    assert len(CATEGORIES) == 9
    for cat in CATEGORIES:
        assert (CORPUS / cat).is_dir(), f"missing category dir: {cat}"


def test_every_category_has_at_least_one_case() -> None:
    for cat in CATEGORIES:
        cases = list((CORPUS / cat).glob("*.json"))
        assert cases, f"category '{cat}' has no cases"


def test_case_ids_unique_and_category_matches_dir() -> None:
    seen: set[str] = set()
    for path in sorted(CORPUS.glob("*/*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        assert case["id"] not in seen, f"duplicate id {case['id']}"
        seen.add(case["id"])
        assert case["category"] == path.parent.name


def test_runner_validate_passes() -> None:
    assert benchmark_runner.validate() == 0
