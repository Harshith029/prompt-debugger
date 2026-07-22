"""Contract schema subset checker (stdlib only).

Verifies that a JSON Schema uses only the keyword subset the M2 runtime validator
implements (see core/contracts/README.md). This is a meta-check on the schemas
themselves, independent of validating instances against them.

The subset is exhaustive: every keyword must be explicitly allowed — unknown
``$``-prefixed keywords are rejected like any other unknown keyword. Boolean
subschemas (draft 2020-12 ``true``/``false`` schemas) are outside the subset and
rejected. The closed-object rule applies to every object schema: an object with
``properties`` must set ``additionalProperties: false``; an object without
``properties`` must be a composite placeholder carrying ``$comment`` (the
documented form for fields governed by another contract); ``additionalProperties``
may never hold any value other than ``false``.

src/prompt_debugger/schema.py implements the same rules for the runtime;
tests/test_differential_validation.py holds the two in parity.
"""

from __future__ import annotations

import re
from typing import Any

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
    """Return a list of human-readable violations; empty means conformant."""
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
