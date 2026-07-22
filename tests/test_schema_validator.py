"""Unit tests for the runtime schema-subset validator (M2 FR-1).

Covers the draft 2020-12 semantics that are easy to get subtly wrong — bool vs
integer, integral floats, unanchored patterns, JSON equality in enum/const/
uniqueItems — each cross-checked against the dev-only `jsonschema` package so
the semantic claims are proven, not asserted. Composite validation (CV-1/CV-2)
and the fail-closed subset rule are covered against the real contract schemas
and fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from prompt_debugger import schema as pdschema

REPO = Path(__file__).resolve().parent.parent
CONTRACTS = REPO / "core" / "contracts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _both_verdicts(instance: object, schema: dict[str, Any]) -> tuple[bool, bool]:
    """(ours, jsonschema's) accept verdicts for the same instance/schema."""
    ours = pdschema.validate(instance, schema) == []
    validator = jsonschema.Draft202012Validator(schema)
    theirs = next(validator.iter_errors(instance), None) is None
    return ours, theirs


def _assert_agree(instance: object, schema: dict[str, Any], expected_valid: bool) -> None:
    ours, theirs = _both_verdicts(instance, schema)
    assert ours == theirs, f"verdict disagreement on {instance!r}: ours={ours} jsonschema={theirs}"
    assert ours is expected_valid, f"unexpected verdict for {instance!r}: {ours}"


# --- type semantics --------------------------------------------------------------------


def test_booleans_are_not_integers_or_numbers() -> None:
    _assert_agree(True, {"type": "integer"}, False)
    _assert_agree(True, {"type": "number"}, False)
    _assert_agree(True, {"type": "boolean"}, True)


def test_integral_float_is_an_integer() -> None:
    _assert_agree(1.0, {"type": "integer"}, True)
    _assert_agree(1.5, {"type": "integer"}, False)
    _assert_agree(1, {"type": "number"}, True)


def test_nullable_type_arrays() -> None:
    nullable = {"type": ["string", "null"]}
    _assert_agree(None, nullable, True)
    _assert_agree("x", nullable, True)
    _assert_agree(3, nullable, False)


# --- equality semantics (const / enum / uniqueItems) ------------------------------------


def test_const_numeric_equality_and_bool_safety() -> None:
    _assert_agree(1.0, {"const": 1}, True)
    _assert_agree(True, {"const": 1}, False)
    _assert_agree(1, {"const": True}, False)


def test_enum_bool_safety() -> None:
    _assert_agree(True, {"enum": [1, 2]}, False)
    _assert_agree(1, {"enum": [True, 2]}, False)
    _assert_agree(2, {"enum": [True, 2]}, True)


def test_unique_items_json_equality() -> None:
    unique = {"type": "array", "uniqueItems": True}
    _assert_agree([1, True], unique, True)  # bool is distinct from 1
    _assert_agree([1, 1.0], unique, False)  # numeric equality across int/float
    _assert_agree([{"a": 1}, {"a": 1}], unique, False)  # deep equality, unhashable
    _assert_agree([{"a": 1}, {"a": 2}], unique, True)


# --- string and number keywords ---------------------------------------------------------


def test_pattern_is_unanchored_search() -> None:
    _assert_agree("xx-ab-yy", {"type": "string", "pattern": "ab"}, True)
    _assert_agree("nope", {"type": "string", "pattern": "^pd-"}, False)


def test_length_and_bounds_apply_only_to_matching_types() -> None:
    _assert_agree("ab", {"minLength": 3}, False)
    _assert_agree(5, {"minLength": 3}, True)  # minLength ignores non-strings
    _assert_agree(2, {"minimum": 3}, False)
    _assert_agree("x", {"minimum": 3}, True)  # minimum ignores non-numbers
    _assert_agree(4, {"maximum": 3}, False)


# --- object and array keywords -----------------------------------------------------------


def test_required_properties_and_closed_objects() -> None:
    obj = {
        "type": "object",
        "additionalProperties": False,
        "required": ["a"],
        "properties": {"a": {"type": "integer"}, "b": {"type": "string"}},
    }
    _assert_agree({"a": 1}, obj, True)
    _assert_agree({"b": "x"}, obj, False)  # missing required
    _assert_agree({"a": 1, "z": 0}, obj, False)  # additional property
    _assert_agree({"a": "no"}, obj, False)  # property type


def test_items_and_counts() -> None:
    arr = {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 2}
    _assert_agree(["a"], arr, True)
    _assert_agree([], arr, False)
    _assert_agree(["a", "b", "c"], arr, False)
    _assert_agree(["a", 1], arr, False)


# --- fail-closed subset rule -------------------------------------------------------------


def test_validate_fails_closed_on_non_subset_schema() -> None:
    non_subset_schemas: list[dict[str, Any]] = [
        {"anyOf": [{"type": "object"}]},
        {"$dynamicRef": "#x"},  # unknown $ keyword
        {"type": "array", "items": True},  # boolean subschema
    ]
    for schema in non_subset_schemas:
        with pytest.raises(pdschema.SubsetViolationError):
            pdschema.validate({"a": 1}, schema)


def test_subset_checker_rejects_prohibited_constructs() -> None:
    bad_schemas: list[dict[str, Any]] = [
        {"$ref": "#/x"},
        {"if": {"type": "string"}, "then": {"minLength": 1}},
        {"patternProperties": {"^x": {"type": "string"}}},
        {"type": "object", "properties": {"a": {"type": "string"}}},  # not closed
    ]
    for bad in bad_schemas:
        assert pdschema.find_subset_violations(bad), f"should be rejected: {bad}"


def test_subset_keyword_set_is_exhaustive_including_dollar_keywords() -> None:
    for bad in (
        {"$dynamicRef": "#x"},
        {"$dynamicAnchor": "a", "type": "string"},
        {"$anchor": "a", "type": "string"},
        {"$vocabulary": {}, "type": "string"},
    ):
        violations = pdschema.find_subset_violations(bad)
        assert violations, f"unknown $ keyword should be rejected: {bad}"


def test_subset_checker_rejects_boolean_subschemas() -> None:
    for bad in (
        {"type": "array", "items": True},
        {"type": "array", "items": False},
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {"a": True},
        },
    ):
        violations = pdschema.find_subset_violations(bad)
        assert any("subschema must be an object" in v for v in violations), bad


_MALFORMED_KEYWORD_SCHEMAS: list[dict[str, Any]] = [
    {"type": "object", "additionalProperties": False, "properties": []},
    {"enum": 1},
    {"required": {}},
    {"required": ["a", 1]},
    {"type": "array", "items": []},
    {"type": "object", "properties": {"a": {"type": "string"}}, "additionalProperties": []},
    {"type": "string", "minLength": "3"},
    {"type": "array", "minItems": -1},
    {"type": "integer", "minimum": "0"},
    {"type": "string", "pattern": 5},
    {"type": "string", "pattern": "("},
    {"type": 5},
    {"type": []},
    {"type": ["object", 5]},
    {"type": "not-a-type"},
    {"type": "array", "uniqueItems": "yes"},
    {"title": 5, "type": "string"},
    {"examples": 1, "type": "string"},
    # Draft 2020-12: type/required array members must be unique.
    {"type": ["string", "string"]},
    {"required": ["a", "a"]},
]


def test_malformed_supported_keyword_values_are_rejected() -> None:
    # Fail-closed: a schema that cannot be interpreted according to the subset is
    # rejected during subset scanning, never surfaced as a Python exception later.
    for bad in _MALFORMED_KEYWORD_SCHEMAS:
        assert pdschema.find_subset_violations(bad), f"should be rejected: {bad}"


def test_malformed_schemas_raise_subset_error_not_python_exceptions() -> None:
    for bad in _MALFORMED_KEYWORD_SCHEMAS:
        with pytest.raises(pdschema.SubsetViolationError):
            pdschema.validate({"a": 1}, bad)
        with pytest.raises(pdschema.SubsetViolationError):
            pdschema.validate([1, "x"], bad)


def test_non_duplicate_type_and_required_arrays_remain_conformant() -> None:
    assert pdschema.find_subset_violations({"type": ["string", "null"]}) == []
    closed: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["a", "b"],
        "properties": {"a": {"type": "integer"}, "b": {"type": "string"}},
    }
    assert pdschema.find_subset_violations(closed) == []


def test_closed_object_rule_applies_to_every_object_schema() -> None:
    # Bare open object (no properties, no $comment) is rejected.
    assert pdschema.find_subset_violations({"type": "object"})
    # additionalProperties may never hold a value other than false.
    assert pdschema.find_subset_violations(
        {"type": "object", "properties": {"a": {"type": "string"}}, "additionalProperties": True}
    )
    assert pdschema.find_subset_violations({"type": "string", "additionalProperties": True})
    # The documented composite-placeholder form is accepted.
    placeholder: dict[str, Any] = {
        "type": ["object", "null"],
        "$comment": "Validated against another contract (composite validation).",
        "default": None,
    }
    assert pdschema.find_subset_violations(placeholder) == []


# --- composite validation (CV-1 / CV-2) ---------------------------------------------------


def test_full_report_fixture_passes_composite() -> None:
    report = _load(FIXTURES / "report-full.json")
    assert pdschema.validate_report(report, CONTRACTS) == []


def test_composite_catches_invalid_event_subdocument() -> None:
    report = _load(FIXTURES / "report-full.json")
    report["event"]["kind"] = "not-a-kind"
    errors = pdschema.validate_report(report, CONTRACTS)
    assert any(e.startswith("report.event") for e in errors), errors


def test_composite_catches_invalid_rewrite_subdocument() -> None:
    report = _load(FIXTURES / "report-full.json")
    del report["rewrite"]["gate"]
    errors = pdschema.validate_report(report, CONTRACTS)
    assert any(e.startswith("report.rewrite") for e in errors), errors


def test_history_record_fixture_passes_composite() -> None:
    record = _load(FIXTURES / "history-record-redacted.json")
    assert pdschema.validate_history_record(record, CONTRACTS) == []


def test_composite_record_catches_broken_embedded_report() -> None:
    record = _load(FIXTURES / "history-record-redacted.json")
    del record["report"]["knowledge"]
    errors = pdschema.validate_history_record(record, CONTRACTS)
    assert any(e.startswith("record.report") for e in errors), errors


def test_default_contracts_dir_resolves() -> None:
    # The composite entry points work without an explicit contracts path.
    report = _load(FIXTURES / "report-full.json")
    assert pdschema.validate_report(report) == []
