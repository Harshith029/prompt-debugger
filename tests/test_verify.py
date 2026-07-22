"""Unit tests for the runtime invariant verifier (M2 FR-2).

Positive, negative, and edge cases for every in-scope invariant (IR-1/2,
RPT-1..4, RW-1..3, EV-1/2, PT-1..3), plus the spec-required agreement check: the
verifier must produce the same verdicts as the existing reference checkers in
``tests/test_contract_invariants.py`` on the same fixtures.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

from prompt_debugger import verify

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
KN = REPO / "core" / "knowledge"

# The FR-2 spec requires agreement with the existing reference checkers; import
# them (and their fixtures) directly so agreement is proven against the real
# implementations, not copies.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_contract_invariants import (  # noqa: E402
    _RW_CONDITIONAL,
    _RW_DECLINED,
    _RW_PASSED,
    _event,
    check_observable_event,
    check_rewrite_report,
)

REFERENCE_PROMPT = "Explain how our caching layer works."


def _load(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _taxonomy_ids() -> set[str]:
    entries = _load(KN / "packs" / "anthropic" / "events.json")["entries"]
    return {e["id"] for e in entries}


def _report() -> dict[str, Any]:
    return _load(FIXTURES / "report-full.json")


def _ids(violations: list[verify.Violation]) -> set[str]:
    return {v.invariant for v in violations}


# --- positive: the composite fixture upholds every invariant ---------------------------


def test_full_report_fixture_has_no_violations() -> None:
    assert verify.verify_report(_report(), REFERENCE_PROMPT, taxonomy_ids=_taxonomy_ids()) == []


def test_violation_records_are_structured() -> None:
    report = _report()
    report["ir"]["segments"][0]["text"] = "text absent from the prompt"
    violations = verify.verify_report(report, REFERENCE_PROMPT, taxonomy_ids=_taxonomy_ids())
    assert len(violations) == 1
    v = violations[0]
    assert (v.invariant, v.path) == ("IR-1", "$.ir.segments[0].text")
    assert isinstance(v.message, str) and v.message


# --- Prompt IR ------------------------------------------------------------------------


def test_ir1_non_substring_segment_is_flagged() -> None:
    ir = {
        "ir_version": 1,
        "unsegmented_remainder": False,
        "segments": [{"id": "s1", "kind": "task", "text": "not in the prompt"}],
    }
    assert _ids(verify.verify_ir(ir, REFERENCE_PROMPT)) == {"IR-1"}


def test_ir1_substring_segment_passes() -> None:
    ir = {
        "ir_version": 1,
        "unsegmented_remainder": True,
        "segments": [{"id": "s1", "kind": "task", "text": "caching layer"}],
    }
    assert verify.verify_ir(ir, REFERENCE_PROMPT) == []


def test_ir2_duplicate_segment_ids_flagged() -> None:
    ir = {
        "ir_version": 1,
        "unsegmented_remainder": False,
        "segments": [
            {"id": "s1", "kind": "task", "text": "caching"},
            {"id": "s1", "kind": "context", "text": "layer"},
        ],
    }
    assert _ids(verify.verify_ir(ir, REFERENCE_PROMPT)) == {"IR-2"}


# --- Report JSON ----------------------------------------------------------------------


def test_rpt1_non_substring_evidence_quote_flagged() -> None:
    report = _report()
    report["findings"][0]["evidence"][0]["quote"] = "fabricated quote"
    assert "RPT-1" in _ids(
        verify.verify_report(report, REFERENCE_PROMPT, taxonomy_ids=_taxonomy_ids())
    )


def test_rpt2_dangling_evidence_segment_flagged() -> None:
    report = _report()
    report["findings"][0]["evidence"][0]["segment"] = "s99"
    assert "RPT-2" in _ids(
        verify.verify_report(report, REFERENCE_PROMPT, taxonomy_ids=_taxonomy_ids())
    )


def test_rpt2_null_segment_is_allowed() -> None:
    report = _report()
    report["findings"][0]["evidence"][0]["segment"] = None
    assert "RPT-2" not in _ids(
        verify.verify_report(report, REFERENCE_PROMPT, taxonomy_ids=_taxonomy_ids())
    )


def test_rpt3_estimates_without_event_flagged() -> None:
    report = _report()
    report["event"] = None
    assert "RPT-3" in _ids(
        verify.verify_report(report, REFERENCE_PROMPT, taxonomy_ids=_taxonomy_ids())
    )


def test_rpt3_no_estimates_and_no_event_passes() -> None:
    report = _report()
    report["event"] = None
    report["estimates"] = None
    assert "RPT-3" not in _ids(
        verify.verify_report(report, REFERENCE_PROMPT, taxonomy_ids=_taxonomy_ids())
    )


def test_rpt4_duplicate_finding_ids_flagged() -> None:
    report = _report()
    report["findings"].append(copy.deepcopy(report["findings"][0]))
    assert "RPT-4" in _ids(
        verify.verify_report(report, REFERENCE_PROMPT, taxonomy_ids=_taxonomy_ids())
    )


# --- Rewrite Report -------------------------------------------------------------------


def test_rw1_declined_with_text_flagged() -> None:
    # A declined rewrite carrying text also lacks the non_guarantee notice, so RW-2
    # fires alongside RW-1 (the reference checker agrees); assert RW-1 is present.
    assert "RW-1" in _ids(verify.verify_rewrite({**_RW_DECLINED, "text": "sneaky"}))


def test_rw1_passed_with_null_text_flagged() -> None:
    assert _ids(verify.verify_rewrite({**_RW_PASSED, "text": None})) >= {"RW-1"}


def test_rw2_missing_non_guarantee_flagged() -> None:
    assert "RW-2" in _ids(verify.verify_rewrite({**_RW_PASSED, "notices": []}))


def test_rw3_conditional_without_reason_flagged() -> None:
    assert "RW-3" in _ids(verify.verify_rewrite({**_RW_CONDITIONAL, "gate_reason": None}))


# --- Observable Event -----------------------------------------------------------------


def test_ev1_unknown_kind_with_match_flagged() -> None:
    event = {
        "event_version": 1,
        "kind": "unknown",
        "surface": "web",
        "verbatim": "x",
        "documented_match": "evt-refusal-visible",
    }
    assert "EV-1" in _ids(verify.verify_event(event, taxonomy_ids=_taxonomy_ids()))


def test_ev2_unknown_taxonomy_id_flagged() -> None:
    event = {
        "event_version": 1,
        "kind": "refusal_message",
        "surface": "web",
        "verbatim": "x",
        "documented_match": "evt-does-not-exist",
    }
    assert _ids(verify.verify_event(event, taxonomy_ids=_taxonomy_ids())) == {"EV-2"}


def test_ev2_is_fail_closed_on_empty_taxonomy() -> None:
    event = {
        "event_version": 1,
        "kind": "refusal_message",
        "surface": "web",
        "verbatim": "x",
        "documented_match": "evt-refusal-visible",
    }
    assert "EV-2" in _ids(verify.verify_event(event, taxonomy_ids=frozenset()))


def test_ev_none_kind_with_null_match_passes() -> None:
    event = {
        "event_version": 1,
        "kind": "none",
        "surface": "unspecified",
        "verbatim": None,
        "documented_match": None,
    }
    assert verify.verify_event(event, taxonomy_ids=_taxonomy_ids()) == []


# --- Prompt Tree ----------------------------------------------------------------------


def _tree_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    ir = {
        "ir_version": 1,
        "unsegmented_remainder": False,
        "segments": [
            {"id": "s1", "kind": "task", "text": "caching"},
            {"id": "s2", "kind": "context", "text": "layer"},
        ],
    }
    report = {"findings": [{"id": "f1"}, {"id": "f2"}]}
    tree = {
        "tree_version": 1,
        "source_ir_version": 1,
        "nodes": [
            {
                "id": "n1",
                "parent_id": None,
                "section": "objective",
                "label": "root",
                "segment_ids": ["s1"],
                "annotations": [{"finding_id": "f1"}],
            },
            {
                "id": "n2",
                "parent_id": "n1",
                "section": "context",
                "label": "child",
                "segment_ids": ["s2"],
                "annotations": [],
            },
        ],
    }
    return tree, ir, report


def test_prompt_tree_positive() -> None:
    tree, ir, report = _tree_inputs()
    assert verify.verify_prompt_tree(tree, ir=ir, report=report) == []


def test_pt1_dangling_parent_flagged() -> None:
    tree, ir, report = _tree_inputs()
    tree["nodes"][1]["parent_id"] = "n99"
    assert "PT-1" in _ids(verify.verify_prompt_tree(tree, ir=ir, report=report))


def test_pt1_cycle_flagged() -> None:
    tree, ir, report = _tree_inputs()
    tree["nodes"][0]["parent_id"] = "n2"  # n1 -> n2 -> n1
    assert "PT-1" in _ids(verify.verify_prompt_tree(tree, ir=ir, report=report))


def test_pt2_dangling_segment_id_flagged() -> None:
    tree, ir, report = _tree_inputs()
    tree["nodes"][0]["segment_ids"] = ["s99"]
    assert "PT-2" in _ids(verify.verify_prompt_tree(tree, ir=ir, report=report))


def test_pt3_dangling_finding_id_flagged() -> None:
    tree, ir, report = _tree_inputs()
    tree["nodes"][0]["annotations"] = [{"finding_id": "f99"}]
    assert "PT-3" in _ids(verify.verify_prompt_tree(tree, ir=ir, report=report))


# --- agreement with the existing reference checkers (FR-2 requirement) -----------------


def _reference_ids(messages: list[str]) -> set[str]:
    return {m.split(":", 1)[0] for m in messages}


def test_verify_rewrite_agrees_with_reference_checker() -> None:
    fixtures: list[dict[str, Any]] = [
        _RW_PASSED,
        _RW_DECLINED,
        _RW_CONDITIONAL,
        {**_RW_DECLINED, "text": "sneaky"},
        {**_RW_PASSED, "notices": []},
        {**_RW_CONDITIONAL, "gate_reason": None},
        {**_RW_PASSED, "text": None},
    ]
    for fixture in fixtures:
        assert _ids(verify.verify_rewrite(fixture)) == _reference_ids(
            check_rewrite_report(fixture)
        ), fixture


def test_verify_event_agrees_with_reference_checker() -> None:
    taxonomy_ids = _taxonomy_ids()
    fixtures = [
        _event("unknown", None),
        _event("refusal_message", "evt-refusal-visible"),
        _event("none", None),
        _event("unknown", "evt-refusal-visible"),
    ]
    for fixture in fixtures:
        # Reference checker covers EV-1 only; the shared fixtures use real (or null)
        # documented_match values, so EV-2 never fires and the verdicts match.
        assert _ids(verify.verify_event(fixture, taxonomy_ids=taxonomy_ids)) == _reference_ids(
            check_observable_event(fixture)
        ), fixture
