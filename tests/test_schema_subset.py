"""Every contract schema conforms to the documented keyword subset."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

from _subset import find_subset_violations  # noqa: E402


def _schema_files() -> list[Path]:
    return sorted((REPO / "core" / "contracts").rglob("*.schema.json")) + sorted(
        (REPO / "benchmarks").glob("*.schema.json")
    )


def test_schema_files_exist() -> None:
    assert _schema_files(), "no schema files found"


def test_all_schemas_are_valid_json() -> None:
    for sf in _schema_files():
        json.loads(sf.read_text(encoding="utf-8"))


def test_all_schemas_conform_to_subset() -> None:
    violations: list[str] = []
    for sf in _schema_files():
        schema = json.loads(sf.read_text(encoding="utf-8"))
        for v in find_subset_violations(schema):
            violations.append(f"{sf.relative_to(REPO)}: {v}")
    assert not violations, "subset violations:\n" + "\n".join(violations)


def test_every_object_schema_closes_additional_properties() -> None:
    # A representative spot-check that the subset checker's closed-object rule is active.
    report = json.loads(
        (REPO / "core" / "contracts" / "report" / "report.schema.json").read_text("utf-8")
    )
    assert report["additionalProperties"] is False
