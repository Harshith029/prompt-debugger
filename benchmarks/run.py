#!/usr/bin/env python3
"""Benchmark corpus runner (stdlib only).

Subcommands:
  validate   Schema-validate and integrity-check every corpus case (CI gate).
  list       List case ids grouped by category.
  stats      Print counts per category and totals.

The 'run' subcommand (execute cases through an adapter and score against
expectations) arrives in Milestone M3, when an analyzer exists to run. At M0 the
corpus is inventory + integrity only.

Case validation uses the dev-only `jsonschema` package when available; without it,
validate performs structural integrity checks (unique ids, category matches
directory, required keys present) so CI still catches corpus mistakes on either path.
CI installs jsonschema, so the full check runs there.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BENCHMARKS = Path(__file__).resolve().parent
CORPUS = BENCHMARKS / "corpus"
SCHEMA = BENCHMARKS / "benchmark-case.schema.json"

CATEGORIES = [
    "good",
    "poor",
    "ambiguous",
    "coding",
    "research",
    "creative",
    "educational",
    "long-context",
    "multi-step",
]


def _cases() -> list[Path]:
    return sorted(CORPUS.glob("*/*.json"))


def _load(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def validate() -> int:
    errors: list[str] = []
    seen_ids: set[str] = set()

    for cat in CATEGORIES:
        if not (CORPUS / cat).is_dir():
            errors.append(f"missing category directory: corpus/{cat}/")

    schema = None
    try:
        import jsonschema

        schema = _load(SCHEMA)
    except ImportError:
        print("WARNING: jsonschema not installed; running structural checks only.", file=sys.stderr)

    cases = _cases()
    if not cases:
        errors.append("no benchmark cases found")

    for path in cases:
        rel = path.relative_to(BENCHMARKS)
        try:
            case = _load(path)
        except json.JSONDecodeError as exc:
            errors.append(f"{rel}: invalid JSON: {exc}")
            continue

        # Structural checks (always).
        cid = case.get("id")
        if not isinstance(cid, str):
            errors.append(f"{rel}: missing string 'id'")
        else:
            if cid in seen_ids:
                errors.append(f"{rel}: duplicate id '{cid}'")
            seen_ids.add(cid)
        dir_category = path.parent.name
        case_category = case.get("category")
        if case_category != dir_category:
            errors.append(
                f"{rel}: category '{case_category}' does not match directory '{dir_category}'"
            )

        # Full schema validation (when available).
        if schema is not None:
            try:
                jsonschema.validate(case, schema)
            except jsonschema.ValidationError as exc:
                loc = "/".join(str(p) for p in exc.absolute_path) or "<root>"
                errors.append(f"{rel}: {loc}: {exc.message}")

    if errors:
        print("Benchmark validation FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"Benchmark validation passed ({len(cases)} cases across {len(CATEGORIES)} categories).")
    return 0


def list_cases() -> int:
    by_cat: dict[str, list[str]] = {c: [] for c in CATEGORIES}
    for path in _cases():
        case = _load(path)
        by_cat.setdefault(case.get("category", "?"), []).append(case.get("id", path.stem))
    for cat in CATEGORIES:
        print(f"{cat}:")
        for cid in sorted(by_cat.get(cat, [])):
            print(f"  - {cid}")
    return 0


def stats() -> int:
    counts: Counter[str] = Counter()
    for path in _cases():
        counts[_load(path).get("category", "?")] += 1
    total = 0
    for cat in CATEGORIES:
        n = counts.get(cat, 0)
        total += n
        print(f"{cat:16} {n}")
    print(f"{'TOTAL':16} {total}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "list", "stats"])
    args = parser.parse_args(argv)
    return {"validate": validate, "list": list_cases, "stats": stats}[args.command]()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
