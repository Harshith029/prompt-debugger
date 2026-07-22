"""Executable checks for contract invariants that the schema subset cannot express.

These reference checkers mirror the rules `src/prompt_debugger/verify.py` will implement
in M2. Encoding them now — with both compliant and violating fixtures — freezes the
semantics and guards against contract drift. See docs/CONTRACT-INVARIANTS.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
CONTRACTS = REPO / "core" / "contracts"


def _load(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


# --- Reference checkers (M2 verify.py implements the same rules) ---------------------


def check_rewrite_report(rw: dict[str, Any]) -> list[str]:
    """RW-1..RW-3 from docs/CONTRACT-INVARIANTS.md."""
    v: list[str] = []
    gate = rw.get("gate")
    text = rw.get("text")
    notices = rw.get("notices", [])
    gate_reason = rw.get("gate_reason")
    if gate == "declined" and text is not None:
        v.append("RW-1: gate=declined requires text=null")
    if gate != "declined" and text is None:
        v.append("RW-1: text=null is only allowed when gate=declined")
    if text is not None and "non_guarantee" not in notices:
        v.append("RW-2: a produced rewrite must carry the non_guarantee notice")
    if gate != "passed" and gate_reason is None:
        v.append("RW-3: gate!=passed requires gate_reason")
    return v


def check_observable_event(ev: dict[str, Any]) -> list[str]:
    """EV-1 from docs/CONTRACT-INVARIANTS.md."""
    v: list[str] = []
    if ev.get("kind") in {"unknown", "none"} and ev.get("documented_match") is not None:
        v.append("EV-1: kind unknown/none requires documented_match=null")
    return v


# --- RW invariants ------------------------------------------------------------------

_RW_PASSED = {
    "rewrite_version": 1,
    "gate": "passed",
    "gate_reason": None,
    "text": "Refactor normalize_records to reduce complexity; keep behavior identical.",
    "changes": [{"change": "stated the constraint", "technique": "T9", "rationale": "clarity"}],
    "notices": ["non_guarantee"],
}
_RW_DECLINED = {
    "rewrite_version": 1,
    "gate": "declined",
    "gate_reason": "The request's stated purpose is to defeat a safeguard.",
    "text": None,
    "changes": [],
    "notices": ["gate_declined"],
}
_RW_CONDITIONAL = {
    "rewrite_version": 1,
    "gate": "conditional",
    "gate_reason": "The same visible behavior may still occur under provider policy.",
    "text": "Explain the memory-safety bug in this C function so I can fix it.",
    "changes": [{"change": "made intent explicit", "technique": "T2", "rationale": "clarity"}],
    "notices": ["non_guarantee", "gate_conditional"],
}


def test_rw_compliant_fixtures_pass() -> None:
    for fixture in (_RW_PASSED, _RW_DECLINED, _RW_CONDITIONAL):
        assert check_rewrite_report(fixture) == [], fixture["gate"]


def test_rw1_declined_with_text_is_rejected() -> None:
    bad = {**_RW_DECLINED, "text": "sneaky rewrite"}
    assert any(x.startswith("RW-1") for x in check_rewrite_report(bad))


def test_rw2_missing_non_guarantee_is_rejected() -> None:
    bad = {**_RW_PASSED, "notices": []}
    assert any(x.startswith("RW-2") for x in check_rewrite_report(bad))


def test_rw3_conditional_without_reason_is_rejected() -> None:
    bad = {**_RW_CONDITIONAL, "gate_reason": None}
    assert any(x.startswith("RW-3") for x in check_rewrite_report(bad))


# --- EV invariants ------------------------------------------------------------------


def _event(kind: str, documented_match: str | None) -> dict[str, Any]:
    return {
        "event_version": 1,
        "kind": kind,
        "surface": "web",
        "verbatim": "x",
        "documented_match": documented_match,
    }


def test_ev_compliant_fixtures_pass() -> None:
    assert check_observable_event(_event("unknown", None)) == []
    assert check_observable_event(_event("refusal_message", "evt-refusal-visible")) == []


def test_ev1_unknown_with_match_is_rejected() -> None:
    bad = _event("unknown", "evt-refusal-visible")
    assert any(x.startswith("EV-1") for x in check_observable_event(bad))


# --- VC-3: extensible enums reserve a graceful-degradation member --------------------


def test_event_kind_enum_reserves_unknown() -> None:
    schema = _load(CONTRACTS / "events" / "observable-event.schema.json")
    assert "unknown" in schema["properties"]["kind"]["enum"]


def test_ir_kind_enum_reserves_other() -> None:
    schema = _load(CONTRACTS / "prompt-ir" / "prompt-ir.schema.json")
    kind_schema = schema["properties"]["segments"]["items"]["properties"]["kind"]
    assert "other" in kind_schema["enum"]


# --- FR-9 (ADR-0010): truncation kind re-deferred; event kind enum unchanged in M2 ----


def test_event_kind_enum_unchanged_truncation_re_deferred() -> None:
    # ADR-0010 (M2 FR-9 revisit of ADR-0009) re-deferred the truncation/stop-condition
    # kind: M2 adds no `kind` member and no taxonomy entry. The frozen v1 enum stands
    # exactly as at M0/M1. Adding a stop-condition kind is a superseding-ADR decision and
    # a contract version bump (Observable Event contract, Compatibility) — never a silent
    # edit. This guards the re-deferral from regression.
    schema = _load(CONTRACTS / "events" / "observable-event.schema.json")
    kinds = set(schema["properties"]["kind"]["enum"])
    assert kinds == {
        "refusal_message",
        "model_switch",
        "api_refusal_stop_reason",
        "api_fallback_block",
        "error",
        "unknown",
        "none",
    }
    # event_version stays 1: no contract evolution accompanied the re-deferral.
    assert schema["properties"]["event_version"]["const"] == 1
