"""Runtime JSON-Schema-subset validator (M2 FR-1).

Implements exactly the restricted JSON Schema draft 2020-12 subset the contracts
commit to (core/contracts/README.md, "Schema subset (normative)"): shape keywords
only — no ``$ref``, no combinators, no conditionals, no recursion. Three layers:

- :func:`find_subset_violations` — rejects schemas that use constructs outside
  the subset (the same normative rules as the CI meta-check in ``tools/_subset.py``;
  a parity test keeps the two from drifting). The keyword set is exhaustive:
  unknown ``$``-prefixed keywords are rejected like any other unknown keyword,
  boolean subschemas are rejected (the subset has no boolean-schema semantics),
  and the closed-object rule applies to every object schema.
- :func:`validate` — validates an instance against a subset-conformant schema with
  draft 2020-12 semantics on the subset keywords. Fails closed: a schema outside
  the subset raises :class:`SubsetViolationError` instead of being half-validated.
- :func:`validate_report` / :func:`validate_history_record` — composite validation
  (invariants CV-1/CV-2): because ``$ref`` is prohibited, schemas do not embed one
  another, and a document is valid only if the envelope **and** every composed
  sub-document validate (report -> ir / event / rewrite; history record -> its
  embedded report, recursively).

Differential CI tests (``tests/test_differential_validation.py``) hold this module
to accept/reject agreement with the dev-only ``jsonschema`` package on every
repository schema and an accept/reject instance corpus; disagreement fails the
build (ARCHITECTURE section 6.7).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .paths import contracts_dir

# The normative keyword sets from core/contracts/README.md. tools/_subset.py carries
# the same sets for the CI meta-check; tests assert the two implementations agree.
ALLOWED_KEYWORDS: frozenset[str] = frozenset(
    {
        "$schema",
        "$id",
        "$comment",
        "title",
        "description",
        "type",
        "enum",
        "const",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "minItems",
        "maxItems",
        "uniqueItems",
        "pattern",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "default",
        "examples",
        "format",
    }
)

PROHIBITED_KEYWORDS: frozenset[str] = frozenset(
    {
        "$ref",
        "$defs",
        "definitions",
        "anyOf",
        "allOf",
        "oneOf",
        "not",
        "if",
        "then",
        "else",
        "patternProperties",
        "dependentSchemas",
        "dependencies",
        "propertyNames",
        "contains",
        "unevaluatedProperties",
    }
)

_REPORT_SCHEMA = "report/report.schema.json"
_IR_SCHEMA = "prompt-ir/prompt-ir.schema.json"
_EVENT_SCHEMA = "events/observable-event.schema.json"
_REWRITE_SCHEMA = "rewrite-report/rewrite-report.schema.json"
_RECORD_SCHEMA = "storage/history-record.schema.json"


class SubsetViolationError(ValueError):
    """Raised when asked to validate against a schema outside the subset.

    Fail-closed by design: silently validating only the keywords we understand
    would accept instances the schema author meant to reject.
    """

    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        super().__init__("schema is outside the restricted subset: " + "; ".join(violations))


# --- Subset conformance (schemas as data) ---------------------------------------------


_NOT_AN_OBJECT_SUBSCHEMA = (
    "subschema must be an object (boolean and other non-object subschemas are "
    "outside the restricted subset)"
)

_JSON_TYPE_NAMES = frozenset({"object", "array", "string", "integer", "number", "boolean", "null"})


def _check_keyword_value(key: str, value: Any, path: str, violations: list[str]) -> None:
    """Reject malformed values of supported keywords (fail-closed).

    The subset restricts *which* keywords are supported; retained keywords keep
    their full draft 2020-12 definitions, so each value must have the shape the
    meta-schema gives it — including unique members in ``type`` and ``required``
    arrays. A schema that fails these rules is rejected here instead of surfacing
    as a Python exception during runtime validation. ``const`` and ``default``
    accept any JSON value; ``items`` and ``additionalProperties`` are
    shape-checked by the subschema and closed-object rules respectively.
    """
    if key in ("$schema", "$id", "$comment", "title", "description", "format", "pattern"):
        if not isinstance(value, str):
            violations.append(f"{path}.{key}: value must be a string")
        elif key == "pattern":
            try:
                re.compile(value)
            except re.error:
                violations.append(f"{path}.pattern: value is not a valid regular expression")
    elif key == "type":
        names = value if isinstance(value, list) else [value]
        well_formed = (isinstance(value, str) or (isinstance(value, list) and value)) and all(
            isinstance(n, str) and n in _JSON_TYPE_NAMES for n in names
        )
        if not well_formed:
            violations.append(
                f"{path}.type: value must be a JSON type name or a non-empty list of them"
            )
        elif isinstance(value, list) and len(set(value)) != len(value):
            # Draft 2020-12 requires type-array members to be unique.
            violations.append(f"{path}.type: value must not contain duplicate type names")
    elif key == "enum":
        if not isinstance(value, list):
            violations.append(f"{path}.enum: value must be a list")
    elif key == "properties":
        if not isinstance(value, dict):
            violations.append(
                f"{path}.properties: value must be an object mapping names to subschemas"
            )
    elif key == "required":
        if not isinstance(value, list) or not all(isinstance(name, str) for name in value):
            violations.append(f"{path}.required: value must be a list of property names")
        elif len(set(value)) != len(value):
            # Draft 2020-12 requires required-array members to be unique.
            violations.append(f"{path}.required: value must not contain duplicate property names")
    elif key in ("minItems", "maxItems", "minLength", "maxLength"):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            violations.append(f"{path}.{key}: value must be a non-negative integer")
    elif key in ("minimum", "maximum"):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            violations.append(f"{path}.{key}: value must be a number")
    elif key == "uniqueItems":
        if not isinstance(value, bool):
            violations.append(f"{path}.uniqueItems: value must be a boolean")
    elif key == "examples" and not isinstance(value, list):
        violations.append(f"{path}.examples: value must be a list")


def find_subset_violations(schema: dict[str, Any]) -> list[str]:
    """Return human-readable subset violations for a schema; empty means conformant.

    The subset is exhaustive: every keyword must be explicitly allowed — unknown
    ``$``-prefixed keywords are rejected like any other unknown keyword. Boolean
    subschemas are outside the subset. The closed-object rule applies to every
    object schema: with ``properties``, ``additionalProperties: false`` is
    required; without ``properties``, the object must be a composite placeholder
    carrying ``$comment`` (contracts README, "Composite validation").
    """
    violations: list[str] = []

    def walk(node: dict[str, Any], path: str) -> None:
        for key, value in node.items():
            if key in PROHIBITED_KEYWORDS:
                violations.append(f"{path}: prohibited keyword '{key}'")
            elif key not in ALLOWED_KEYWORDS:
                violations.append(f"{path}: keyword '{key}' is outside the allowed subset")
            else:
                _check_keyword_value(key, value, path, violations)
            # Descend only into schema positions. Values of annotation keywords
            # (default, examples, const, enum) are data, not schemas.
            if key == "properties" and isinstance(value, dict):
                for prop_name, prop_schema in value.items():
                    if isinstance(prop_schema, dict):
                        walk(prop_schema, f"{path}.properties.{prop_name}")
                    else:
                        violations.append(
                            f"{path}.properties.{prop_name}: {_NOT_AN_OBJECT_SUBSCHEMA}"
                        )
            elif key == "items":
                if isinstance(value, dict):
                    walk(value, f"{path}.items")
                else:
                    violations.append(f"{path}.items: {_NOT_AN_OBJECT_SUBSCHEMA}")

    walk(schema, "$")
    _require_closed_objects(schema, "$", violations)
    return violations


def _require_closed_objects(node: dict[str, Any], path: str, violations: list[str]) -> None:
    if "additionalProperties" in node and node["additionalProperties"] is not False:
        violations.append(f"{path}: additionalProperties must be exactly false")
    declared_type = node.get("type")
    is_object = declared_type == "object" or (
        isinstance(declared_type, list) and "object" in declared_type
    )
    if is_object:
        if "properties" in node:
            if node.get("additionalProperties") is not False:
                violations.append(f"{path}: object schema must set additionalProperties: false")
        elif "$comment" not in node:
            violations.append(
                f"{path}: object schema without properties must be a composite placeholder "
                "carrying $comment (or declare properties with additionalProperties: false)"
            )
    if isinstance(node.get("properties"), dict):
        for prop_name, prop_schema in node["properties"].items():
            if isinstance(prop_schema, dict):
                _require_closed_objects(prop_schema, f"{path}.properties.{prop_name}", violations)
    if isinstance(node.get("items"), dict):
        _require_closed_objects(node["items"], f"{path}.items", violations)


# --- Instance validation ---------------------------------------------------------------


def validate(instance: object, schema: dict[str, Any]) -> list[str]:
    """Validate ``instance`` against a subset-conformant ``schema``.

    Returns a deterministic list of "<json-path>: message" strings; empty means
    valid. Raises :class:`SubsetViolationError` if the schema itself is outside
    the subset (fail-closed — see the class docstring).
    """
    violations = find_subset_violations(schema)
    if violations:
        raise SubsetViolationError(violations)
    errors: list[str] = []
    _validate_node(instance, schema, "$", errors)
    return errors


def _validate_node(value: object, schema: dict[str, Any], path: str, errors: list[str]) -> None:
    declared = schema.get("type")
    if declared is not None:
        types = declared if isinstance(declared, list) else [declared]
        if not any(_is_type(value, t) for t in types):
            errors.append(f"{path}: expected type {_type_label(types)}")

    if "const" in schema and not _json_equal(value, schema["const"]):
        errors.append(f"{path}: does not equal const {json.dumps(schema['const'])}")

    if "enum" in schema and not any(_json_equal(value, member) for member in schema["enum"]):
        errors.append(f"{path}: not one of the enum values")

    if isinstance(value, str):
        pattern = schema.get("pattern")
        # JSON Schema patterns are unanchored: regex *search*, not fullmatch.
        if pattern is not None and re.search(pattern, value) is None:
            errors.append(f"{path}: does not match pattern {pattern!r}")
        min_len = schema.get("minLength")
        if min_len is not None and len(value) < min_len:
            errors.append(f"{path}: shorter than minLength {min_len}")
        max_len = schema.get("maxLength")
        if max_len is not None and len(value) > max_len:
            errors.append(f"{path}: longer than maxLength {max_len}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            errors.append(f"{path}: less than minimum {minimum}")
        maximum = schema.get("maximum")
        if maximum is not None and value > maximum:
            errors.append(f"{path}: greater than maximum {maximum}")

    if isinstance(value, dict):
        for name in schema.get("required", []):
            if name not in value:
                errors.append(f"{path}: missing required property '{name}'")
        properties = schema.get("properties", {})
        for name, subschema in properties.items():
            if name in value:
                _validate_node(value[name], subschema, f"{path}.{name}", errors)
        if schema.get("additionalProperties") is False:
            for extra in sorted(set(value) - set(properties)):
                errors.append(f"{path}: additional property '{extra}' is not allowed")

    if isinstance(value, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for i, element in enumerate(value):
                _validate_node(element, items, f"{path}[{i}]", errors)
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            errors.append(f"{path}: fewer than minItems {min_items}")
        max_items = schema.get("maxItems")
        if max_items is not None and len(value) > max_items:
            errors.append(f"{path}: more than maxItems {max_items}")
        if schema.get("uniqueItems") is True:
            for j in range(len(value)):
                for i in range(j):
                    if _json_equal(value[i], value[j]):
                        errors.append(f"{path}[{j}]: duplicate of item {i} (uniqueItems)")
                        break


def _is_type(value: object, type_name: str) -> bool:
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "null":
        return value is None
    # JSON Schema: booleans are never integers/numbers; a float with a zero
    # fractional part (1.0) IS an integer. Both match jsonschema's behavior.
    if type_name == "integer":
        if isinstance(value, bool):
            return False
        return isinstance(value, int) or (isinstance(value, float) and value.is_integer())
    if type_name == "number":
        return not isinstance(value, bool) and isinstance(value, (int, float))
    return False


def _type_label(types: list[Any]) -> str:
    return " or ".join(f"'{t}'" for t in types)


def _json_equal(a: object, b: object) -> bool:
    """JSON-semantics equality: bools are distinct from numbers; 1 == 1.0."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a is b
    if a is None or b is None:
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_json_equal(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_json_equal(a[k], b[k]) for k in a)
    return False


# --- Composite validation (CV-1 / CV-2) -------------------------------------------------


def validate_report(report: object, contracts: Path | None = None) -> list[str]:
    """CV-1: the report envelope AND its composed ir/event/rewrite must validate."""
    base = contracts if contracts is not None else contracts_dir()
    errors = [f"report{e[1:]}" for e in validate(report, _load_schema(base / _REPORT_SCHEMA))]
    if isinstance(report, dict):
        ir = report.get("ir")
        if isinstance(ir, dict):
            errors += [f"report.ir{e[1:]}" for e in validate(ir, _load_schema(base / _IR_SCHEMA))]
        event = report.get("event")
        if event is not None:
            errors += [
                f"report.event{e[1:]}" for e in validate(event, _load_schema(base / _EVENT_SCHEMA))
            ]
        rewrite = report.get("rewrite")
        if rewrite is not None:
            errors += [
                f"report.rewrite{e[1:]}"
                for e in validate(rewrite, _load_schema(base / _REWRITE_SCHEMA))
            ]
    return errors


def validate_history_record(record: object, contracts: Path | None = None) -> list[str]:
    """CV-2: the record envelope AND its embedded report (recursively) must validate."""
    base = contracts if contracts is not None else contracts_dir()
    errors = [f"record{e[1:]}" for e in validate(record, _load_schema(base / _RECORD_SCHEMA))]
    if isinstance(record, dict):
        report = record.get("report")
        if isinstance(report, dict):
            errors += [f"record.{e}" for e in validate_report(report, base)]
    return errors


def _load_schema(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data
