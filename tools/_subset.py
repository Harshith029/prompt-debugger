"""Contract schema subset checker (stdlib only).

Verifies that a JSON Schema uses only the keyword subset the M2 runtime validator
will implement (see core/contracts/README.md). This is a meta-check on the schemas
themselves, independent of validating instances against them.
"""

from __future__ import annotations

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


def find_subset_violations(schema: dict[str, Any]) -> list[str]:
    """Return a list of human-readable violations; empty means conformant."""
    violations: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in PROHIBITED_KEYWORDS:
                    violations.append(f"{path}: prohibited keyword '{key}'")
                elif (
                    key not in ALLOWED_KEYWORDS
                    and not key.startswith("$")
                    # Property *names* under 'properties' are data, not keywords.
                    and not _is_property_name_context(path)
                ):
                    violations.append(f"{path}: keyword '{key}' is outside the allowed subset")
                # Descend, but do not treat property names as keywords.
                if key == "properties" and isinstance(value, dict):
                    for prop_name, prop_schema in value.items():
                        walk(prop_schema, f"{path}.properties.{prop_name}")
                elif key in {"items"} or isinstance(value, dict):
                    walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]")

    walk(schema, "$")
    # 'additionalProperties: false' is required on every object schema.
    _require_closed_objects(schema, "$", violations)
    return violations


def _is_property_name_context(path: str) -> bool:
    return path.endswith(".properties") or ".properties." in path.rsplit(".", 1)[0]


def _require_closed_objects(node: Any, path: str, violations: list[str]) -> None:
    if isinstance(node, dict):
        declared_type = node.get("type")
        is_object = declared_type == "object" or (
            isinstance(declared_type, list) and "object" in declared_type
        )
        if is_object and "properties" in node and node.get("additionalProperties") is not False:
            violations.append(f"{path}: object schema must set additionalProperties: false")
        if isinstance(node.get("properties"), dict):
            for prop_name, prop_schema in node["properties"].items():
                _require_closed_objects(prop_schema, f"{path}.properties.{prop_name}", violations)
        if "items" in node:
            _require_closed_objects(node["items"], f"{path}.items", violations)
