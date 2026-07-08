#!/usr/bin/env python3
"""Validate contract schemas and seed instances.

Two independent checks:

1. Subset conformance (always, stdlib only): every core/contracts/**/*.schema.json and
   benchmarks/*.schema.json parses as JSON and uses only the allowed keyword subset.

2. Instance validation (requires the dev-only `jsonschema` package): seed data files
   (knowledge packs, benchmark cases, adapter manifest) validate against their schemas.
   Skipped with a warning if jsonschema is absent, unless --require-jsonschema is set
   (CI passes that flag).

Exit code 0 on success, 1 on any failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _subset import find_subset_violations

REPO = Path(__file__).resolve().parent.parent
CONTRACTS = REPO / "core" / "contracts"
KNOWLEDGE = REPO / "core" / "knowledge"
BENCHMARKS = REPO / "benchmarks"
ADAPTER = REPO / "adapters" / "claude-code"


def _load(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def check_subset() -> list[str]:
    errors: list[str] = []
    schema_files = sorted(CONTRACTS.rglob("*.schema.json")) + sorted(
        BENCHMARKS.glob("*.schema.json")
    )
    if not schema_files:
        errors.append("no schema files found")
    for sf in schema_files:
        try:
            schema = _load(sf)
        except json.JSONDecodeError as exc:
            errors.append(f"{sf.relative_to(REPO)}: invalid JSON: {exc}")
            continue
        for v in find_subset_violations(schema):
            errors.append(f"{sf.relative_to(REPO)}: {v}")
    return errors


# (instance file, schema file) pairs. Composite-only schemas (report, history-record)
# are validated at their own level; nested composition is exercised by M2 tests.
def _instance_pairs() -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = [
        (KNOWLEDGE / "manifest.json", CONTRACTS / "knowledge" / "manifest.schema.json"),
        (
            KNOWLEDGE / "packs" / "common" / "pack.json",
            CONTRACTS / "knowledge" / "pack.schema.json",
        ),
        (
            KNOWLEDGE / "packs" / "common" / "rubric.json",
            CONTRACTS / "knowledge" / "rubric.schema.json",
        ),
        (
            KNOWLEDGE / "packs" / "anthropic" / "pack.json",
            CONTRACTS / "knowledge" / "pack.schema.json",
        ),
        (
            KNOWLEDGE / "packs" / "anthropic" / "claims.json",
            CONTRACTS / "knowledge" / "claims.schema.json",
        ),
        (
            KNOWLEDGE / "packs" / "anthropic" / "techniques.json",
            CONTRACTS / "knowledge" / "techniques.schema.json",
        ),
        (
            KNOWLEDGE / "packs" / "anthropic" / "events.json",
            CONTRACTS / "knowledge" / "events.schema.json",
        ),
        (
            KNOWLEDGE / "packs" / "anthropic" / "patterns" / "index.json",
            CONTRACTS / "knowledge" / "patterns-index.schema.json",
        ),
        (
            ADAPTER / "adapter-manifest.json",
            CONTRACTS / "plugin-api" / "adapter-manifest.schema.json",
        ),
    ]
    for case in sorted(BENCHMARKS.glob("corpus/*/*.json")):
        pairs.append((case, BENCHMARKS / "benchmark-case.schema.json"))
    return pairs


def check_instances(require: bool) -> list[str]:
    errors: list[str] = []
    try:
        import jsonschema
    except ImportError:
        msg = "jsonschema not installed; instance validation skipped"
        if require:
            return [msg + " (required by --require-jsonschema)"]
        print(f"WARNING: {msg}", file=sys.stderr)
        return []

    for instance_path, schema_path in _instance_pairs():
        if not instance_path.exists():
            errors.append(f"missing instance file: {instance_path.relative_to(REPO)}")
            continue
        try:
            instance = _load(instance_path)
            schema = _load(schema_path)
            jsonschema.validate(instance, schema)
        except json.JSONDecodeError as exc:
            errors.append(f"{instance_path.relative_to(REPO)}: invalid JSON: {exc}")
        except jsonschema.ValidationError as exc:
            loc = "/".join(str(p) for p in exc.absolute_path) or "<root>"
            errors.append(f"{instance_path.relative_to(REPO)}: {loc}: {exc.message}")
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-jsonschema", action="store_true")
    args = parser.parse_args(argv)

    errors = check_subset() + check_instances(args.require_jsonschema)
    if errors:
        print("Schema validation FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("Schema validation passed (subset conformance + seed instances).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
