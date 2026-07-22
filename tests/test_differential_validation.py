"""Differential validation: the runtime subset validator vs `jsonschema` (M2 FR-1).

ARCHITECTURE section 6.7 bounds the risk of owning a validator by proving it
equivalent to the real `jsonschema` package on everything the repository ships:

- every repository schema is accepted by both (jsonschema's meta-validation and
  our subset conformance), and our conformance verdicts stay in parity with the
  CI meta-check in tools/_subset.py;
- for an accept/reject instance corpus — every seed instance the repository
  already validates in CI (accept) plus deterministic mutants of each (reject) —
  both validators must return the same accept/reject verdict for every case.

Any disagreement fails the build. This suite runs under pytest, which CI runs
on every PR and on main.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema

from prompt_debugger import schema as pdschema

REPO = Path(__file__).resolve().parent.parent
CONTRACTS = REPO / "core" / "contracts"
BENCHMARKS = REPO / "benchmarks"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# tools/ is not a package; validate_schemas self-inserts its dir to import _subset.
sys.path.insert(0, str(REPO / "tools"))
import _subset  # noqa: E402
import validate_schemas  # noqa: E402


def _load(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _schema_files() -> list[Path]:
    files = sorted(CONTRACTS.rglob("*.schema.json")) + sorted(BENCHMARKS.glob("*.schema.json"))
    assert files, "no schema files found"
    return files


def _corpus_pairs() -> list[tuple[Path, Path]]:
    """The repository's own (instance, schema) pairs, plus the report/record fixtures."""
    pairs = list(validate_schemas._instance_pairs())
    pairs.append((FIXTURES / "report-full.json", CONTRACTS / "report" / "report.schema.json"))
    for fixture in ("history-record-redacted.json", "history-record-leaky.json"):
        pairs.append((FIXTURES / fixture, CONTRACTS / "storage" / "history-record.schema.json"))
    return pairs


def _verdicts(instance: object, schema: dict[str, Any]) -> tuple[bool, bool]:
    ours = pdschema.validate(instance, schema) == []
    validator = jsonschema.Draft202012Validator(schema)
    theirs = next(validator.iter_errors(instance), None) is None
    return ours, theirs


def _mutants(instance: dict[str, Any], schema: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Deterministic reject-side mutants of a valid root-object instance."""
    mutants: list[tuple[str, dict[str, Any]]] = []

    extra = copy.deepcopy(instance)
    extra["__differential_mutant__"] = 1
    mutants.append(("additional-property", extra))

    required = schema.get("required", [])
    if required:
        dropped = copy.deepcopy(instance)
        dropped.pop(required[0], None)
        mutants.append((f"missing-required:{required[0]}", dropped))

        retyped = copy.deepcopy(instance)
        retyped[required[0]] = [[]]
        mutants.append((f"retyped:{required[0]}", retyped))

    return mutants


# --- schemas: both sides accept the whole corpus; parity with the CI meta-check ---------


def test_every_repository_schema_is_valid_and_subset_conformant() -> None:
    for sf in _schema_files():
        schema = _load(sf)
        jsonschema.Draft202012Validator.check_schema(schema)  # raises on invalid
        assert pdschema.find_subset_violations(schema) == [], sf.name


def test_subset_conformance_parity_with_ci_meta_check() -> None:
    # The library and tools/_subset.py must never drift apart.
    for sf in _schema_files():
        schema = _load(sf)
        assert pdschema.find_subset_violations(schema) == _subset.find_subset_violations(schema), (
            sf.name
        )
    out_of_subset: list[dict[str, Any]] = [
        {"$ref": "#/x"},
        {"allOf": [{"type": "object"}]},
        # unknown $ keywords (the subset keyword set is exhaustive)
        {"$dynamicRef": "#x"},
        {"$anchor": "a", "type": "string"},
        # boolean subschemas
        {"type": "array", "items": True},
        {"type": "object", "additionalProperties": False, "properties": {"a": True}},
        # closed-object rule: with properties, without properties, and non-false values
        {"type": "object", "properties": {"a": {"type": "string"}}},
        {"type": "object"},
        {"type": "object", "properties": {"a": {"type": "string"}}, "additionalProperties": True},
        # malformed values of supported keywords (fail-closed, never a Python exception)
        {"type": "object", "additionalProperties": False, "properties": []},
        {"enum": 1},
        {"required": {}},
        {"type": "array", "items": []},
        {"type": "object", "properties": {"a": {"type": "string"}}, "additionalProperties": []},
        {"type": "string", "minLength": "3"},
        {"type": "integer", "minimum": "0"},
        {"type": "string", "pattern": "("},
        {"type": []},
        {"type": "array", "uniqueItems": "yes"},
        # duplicate members in type/required arrays (unique per draft 2020-12)
        {"type": ["string", "string"]},
        {"type": "object", "additionalProperties": False, "required": ["a", "a"]},
    ]
    for bad in out_of_subset:
        ours = pdschema.find_subset_violations(bad)
        theirs = _subset.find_subset_violations(bad)
        assert ours == theirs, f"parity break on {bad}: {ours} vs {theirs}"
        assert ours, f"should be rejected by both: {bad}"


# --- instances: accept and reject corpus, verdicts must agree ---------------------------


def test_accept_corpus_agrees() -> None:
    for instance_path, schema_path in _corpus_pairs():
        instance = _load(instance_path)
        schema = _load(schema_path)
        ours, theirs = _verdicts(instance, schema)
        assert ours == theirs, f"disagreement on {instance_path.name}: {ours} vs {theirs}"
        assert ours is True, f"{instance_path.name} unexpectedly invalid against its schema"


def test_reject_corpus_agrees() -> None:
    for instance_path, schema_path in _corpus_pairs():
        instance = _load(instance_path)
        schema = _load(schema_path)
        for label, mutant in _mutants(instance, schema):
            ours, theirs = _verdicts(mutant, schema)
            assert ours == theirs, (
                f"disagreement on {instance_path.name} mutant {label}: {ours} vs {theirs}"
            )
            if label.startswith(("additional-property", "missing-required")):
                assert ours is False, (
                    f"{instance_path.name} mutant {label} unexpectedly valid on both sides"
                )
