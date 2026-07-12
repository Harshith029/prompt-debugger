"""Composite validation with concrete populated Event and Rewrite sub-documents (CV-1/CV-2).

The schema subset forbids `$ref`, so a Report JSON does not embed its sub-schemas; validity
is defined as the envelope AND each composed sub-document validating against its own schema
(contracts README → Composite validation). Earlier fixtures left `event` and `rewrite` null,
so those two composition edges were unexercised. This module fills that gap with a report
whose `event` and `rewrite` are populated, validates the whole chain, and then ties the
schema-valid fixture to the semantic invariant checkers — demonstrating the layered model
where the schema checks shape and the verifier (M2) checks the relationships schemas cannot.

The two reference checkers below are intentionally duplicated from
``tests/test_contract_invariants.py`` (rather than imported) to keep this module free of
sibling-test imports; both mirror the same rules from docs/CONTRACT-INVARIANTS.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CONTRACTS = REPO / "core" / "contracts"


def _load(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _check_rewrite_report(rw: dict[str, Any]) -> list[str]:
    """RW-1..RW-3 from docs/CONTRACT-INVARIANTS.md."""
    v: list[str] = []
    gate, text = rw.get("gate"), rw.get("text")
    if gate == "declined" and text is not None:
        v.append("RW-1: gate=declined requires text=null")
    if gate != "declined" and text is None:
        v.append("RW-1: text=null is only allowed when gate=declined")
    if text is not None and "non_guarantee" not in rw.get("notices", []):
        v.append("RW-2: a produced rewrite must carry the non_guarantee notice")
    if gate != "passed" and rw.get("gate_reason") is None:
        v.append("RW-3: gate!=passed requires gate_reason")
    return v


def _check_observable_event(ev: dict[str, Any]) -> list[str]:
    """EV-1 from docs/CONTRACT-INVARIANTS.md."""
    if ev.get("kind") in {"unknown", "none"} and ev.get("documented_match") is not None:
        return ["EV-1: kind unknown/none requires documented_match=null"]
    return []


def _validate_report_composite(report: dict[str, Any]) -> None:
    """CV-1: envelope + composed ir, event, rewrite all validate against their schemas."""
    jsonschema.validate(report, _load(CONTRACTS / "report" / "report.schema.json"))
    jsonschema.validate(report["ir"], _load(CONTRACTS / "prompt-ir" / "prompt-ir.schema.json"))
    if report.get("event") is not None:
        jsonschema.validate(
            report["event"], _load(CONTRACTS / "events" / "observable-event.schema.json")
        )
    if report.get("rewrite") is not None:
        jsonschema.validate(
            report["rewrite"],
            _load(CONTRACTS / "rewrite-report" / "rewrite-report.schema.json"),
        )


def test_full_report_has_populated_event_and_rewrite() -> None:
    report = _load(FIXTURES / "report-full.json")
    assert report["event"] is not None
    assert report["rewrite"] is not None
    assert report["estimates"] is not None  # RPT-3: estimates accompany a reported event


def test_full_report_composite_validates() -> None:
    _validate_report_composite(_load(FIXTURES / "report-full.json"))


def test_full_report_satisfies_semantic_invariants() -> None:
    report = _load(FIXTURES / "report-full.json")
    assert _check_observable_event(report["event"]) == []
    assert _check_rewrite_report(report["rewrite"]) == []


def test_full_report_embeds_in_history_record_composite() -> None:
    # CV-2: the report composes into a history-record, validated recursively.
    report = _load(FIXTURES / "report-full.json")
    record = {
        "record_version": 1,
        "id": "pd-1751884800002-c3d4e5f6",
        "created_at": "2026-07-07T12:00:00Z",
        "raw": False,
        "fingerprints": {"alg": "hmac-sha256", "prompt": "0" * 64, "rewrite": "1" * 64},
        "prompt_redacted": "Explain how our caching layer works.",
        "prompt_raw": None,
        "parent_id": None,
        "report": report,
    }
    jsonschema.validate(record, _load(CONTRACTS / "storage" / "history-record.schema.json"))
    _validate_report_composite(report)


def test_schema_valid_but_invariant_violating_rewrite_is_caught() -> None:
    # The layered model: a rewrite with gate=declined AND text!=null is schema-valid (the
    # subset cannot express RW-1) but must be rejected by the verifier's checker.
    bad_rewrite = {
        "rewrite_version": 1,
        "gate": "declined",
        "gate_reason": "declined for policy reasons",
        "text": "a rewrite that should not exist for a declined gate",
        "changes": [],
        "notices": ["gate_declined"],
    }
    jsonschema.validate(
        bad_rewrite, _load(CONTRACTS / "rewrite-report" / "rewrite-report.schema.json")
    )
    assert any(x.startswith("RW-1") for x in _check_rewrite_report(bad_rewrite))
