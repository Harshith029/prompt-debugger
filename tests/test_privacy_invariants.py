"""Executable enforcement of the persisted-record redaction invariant (PR-1).

PR-1 (see docs/CONTRACT-INVARIANTS.md and core/contracts/storage/CONTRACT.md): a
history record with ``raw == false`` must carry no secret or PII pattern in ANY field,
including every content-bearing field of the embedded report (IR segment text, finding
evidence quotes, event verbatim, rewrite text). ``prompt_raw`` must be null.

This test is the guard the M2 storage/redaction implementation must satisfy. It uses an
independent reference secret scanner (below) — deliberately separate from the future
runtime redactor — plus two fixtures:

- ``history-record-redacted.json``: a compliant record; the scanner must find nothing.
- ``history-record-leaky.json``: a record with a secret planted inside an embedded IR
  segment (the exact leak PR-1 exists to prevent) but ``raw == false``; the scanner must
  detect it. This proves the invariant is enforced, not vacuous, and documents the shape
  of record the storage layer must never produce.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import jsonschema

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CONTRACTS = REPO / "core" / "contracts"

# Reference secret/PII patterns. Independent of the future runtime redactor; this is the
# test's own detector for what a redacted record must never contain.
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{12,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    re.compile(r"(?i)(password|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*\S{6,}"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
)


def _load(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _walk_strings(node: Any, path: str = "$") -> list[tuple[str, str]]:
    """Collect (json-path, string-value) for every string anywhere in the structure."""
    out: list[tuple[str, str]] = []
    if isinstance(node, str):
        out.append((path, node))
    elif isinstance(node, dict):
        # Object keys are field names, not user content, so they are not scanned.
        for key, value in node.items():
            out.extend(_walk_strings(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for i, item in enumerate(node):
            out.extend(_walk_strings(item, f"{path}[{i}]"))
    return out


def find_secrets(record: dict[str, Any]) -> list[tuple[str, str]]:
    """Return (path, matched-text) for every secret pattern found anywhere in the record."""
    hits: list[tuple[str, str]] = []
    for path, value in _walk_strings(record):
        for pattern in SECRET_PATTERNS:
            match = pattern.search(value)
            if match:
                hits.append((path, match.group(0)))
    return hits


def _validate_composite(record: dict[str, Any]) -> None:
    """Validate the record envelope plus its composed report and IR sub-documents."""
    hist_schema = _load(CONTRACTS / "storage" / "history-record.schema.json")
    report_schema = _load(CONTRACTS / "report" / "report.schema.json")
    ir_schema = _load(CONTRACTS / "prompt-ir" / "prompt-ir.schema.json")
    jsonschema.validate(record, hist_schema)
    jsonschema.validate(record["report"], report_schema)
    jsonschema.validate(record["report"]["ir"], ir_schema)


def test_reference_scanner_detects_a_known_secret() -> None:
    # The detector must actually work, or every PR-1 assertion below is vacuous.
    assert find_secrets({"x": "here is sk-EXAMPLENOTAREALKEY0000 leaked"})


def test_redacted_fixture_is_structurally_valid() -> None:
    _validate_composite(_load(FIXTURES / "history-record-redacted.json"))


def test_redacted_fixture_satisfies_pr1() -> None:
    record = _load(FIXTURES / "history-record-redacted.json")
    assert record["raw"] is False
    # PR-1 clause 1: raw==false implies prompt_raw is null.
    assert record["prompt_raw"] is None
    # PR-1 clause 2: no secret survives anywhere in the record, incl. the embedded report.
    hits = find_secrets(record)
    assert hits == [], f"redacted record must contain no secrets, found: {hits}"


def test_leaky_fixture_violates_pr1_and_is_detected() -> None:
    # This fixture is what the storage layer must NEVER produce: raw==false, yet a secret
    # is present inside an embedded IR segment. The guard must catch it.
    record = _load(FIXTURES / "history-record-leaky.json")
    assert record["raw"] is False
    hits = find_secrets(record)
    assert hits, "PR-1 guard failed to detect a secret embedded in the report"
    # The leak is specifically inside the embedded report, not the top-level prompt.
    assert any(".report.ir." in path for path, _ in hits), hits


def test_leaky_fixture_top_level_prompt_is_clean() -> None:
    # Demonstrates the exact defect PR-1 addresses: prompt_redacted is scrubbed, but the
    # embedded report copy is not. A prompt-only check would miss it.
    record = _load(FIXTURES / "history-record-leaky.json")
    assert find_secrets({"prompt_redacted": record["prompt_redacted"]}) == []
    assert find_secrets(record["report"]) != []
