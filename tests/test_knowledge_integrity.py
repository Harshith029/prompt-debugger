"""Knowledge Engine cross-reference integrity (the provenance chain holds).

These tests enforce the rules the Knowledge Engine contract promises:
- every technique cites existing claims (unless draft with none);
- every rubric dimension references existing techniques;
- every event taxonomy entry cites existing claims and uses a kind in the
  Observable Event contract enum;
- the pattern index references existing techniques and dimensions;
- taxonomy/rubric ids referenced by findings shape (R*/T*) are internally consistent.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
KN = REPO / "core" / "knowledge"
CONTRACTS = REPO / "core" / "contracts"
COMMON = KN / "packs" / "common"


def _load(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _claim_ids() -> set[str]:
    data = _load(KN / "packs" / "anthropic" / "claims.json")
    return {c["id"] for c in data["claims"]}


def _technique_ids() -> set[str]:
    data = _load(KN / "packs" / "anthropic" / "techniques.json")
    return {t["id"] for t in data["techniques"]}


def _rubric_ids() -> set[str]:
    data = _load(KN / "packs" / "common" / "rubric.json")
    return {d["id"] for d in data["dimensions"]}


def _event_contract_kinds() -> set[str]:
    schema = _load(CONTRACTS / "events" / "observable-event.schema.json")
    return set(schema["properties"]["kind"]["enum"])


def test_manifest_lists_present_packs() -> None:
    manifest = _load(KN / "manifest.json")
    for pack in manifest["packs"]:
        assert (KN / pack["path"] / "pack.json").is_file(), pack["path"]


def test_techniques_cite_existing_claims() -> None:
    claims = _claim_ids()
    data = _load(KN / "packs" / "anthropic" / "techniques.json")
    for t in data["techniques"]:
        if t["status"] != "draft":
            assert t["source_claims"], f"{t['id']} is non-draft but cites no claims"
        for c in t["source_claims"]:
            assert c in claims, f"{t['id']} cites unknown claim {c}"


def test_rubric_references_existing_techniques() -> None:
    techniques = _technique_ids()
    data = _load(KN / "packs" / "common" / "rubric.json")
    for d in data["dimensions"]:
        for t in d["techniques"]:
            assert t in techniques, f"{d['id']} references unknown technique {t}"


def test_events_cite_claims_and_valid_kinds() -> None:
    claims = _claim_ids()
    kinds = _event_contract_kinds()
    data = _load(KN / "packs" / "anthropic" / "events.json")
    for e in data["entries"]:
        assert e["kind"] in kinds, f"{e['id']} uses kind '{e['kind']}' absent from event contract"
        for c in e["source_claims"]:
            assert c in claims, f"{e['id']} cites unknown claim {c}"


def _event_contract_surfaces() -> set[str]:
    schema = _load(CONTRACTS / "events" / "observable-event.schema.json")
    surfaces: set[str] = set(schema["properties"]["surface"]["enum"])
    return surfaces


def test_core_surface_enum_is_provider_neutral() -> None:
    # EV-3: the host-neutral core must not encode provider product names as surfaces.
    surfaces = _event_contract_surfaces()
    for value in surfaces:
        assert "claude" not in value.lower() and "anthropic" not in value.lower(), (
            f"core surface enum must be provider-neutral; found '{value}'"
        )


def test_event_surfaces_use_contract_categories() -> None:
    # EV-3: provider taxonomy surfaces must all be valid host-neutral categories.
    allowed = _event_contract_surfaces()
    data = _load(KN / "packs" / "anthropic" / "events.json")
    for e in data["entries"]:
        for s in e["surfaces"]:
            assert s in allowed, f"{e['id']} uses surface '{s}' absent from the core enum"


def test_active_entries_cite_only_active_claims() -> None:
    # KN-2: an active technique/event must not depend on a non-active claim.
    claims = _load(KN / "packs" / "anthropic" / "claims.json")["claims"]
    active_claims = {c["id"] for c in claims if c["status"] == "active"}
    non_active = {c["id"] for c in claims if c["status"] != "active"}
    for fname in ("techniques.json", "events.json"):
        data = _load(KN / "packs" / "anthropic" / fname)
        entries = data.get("techniques") or data.get("entries") or []
        for entry in entries:
            if entry["status"] == "active":
                for c in entry["source_claims"]:
                    assert c not in non_active or c in active_claims, (
                        f"active {entry['id']} cites non-active claim {c}"
                    )


def test_pattern_index_references_resolve() -> None:
    techniques = _technique_ids()
    dims = _rubric_ids()
    data = _load(KN / "packs" / "anthropic" / "patterns" / "index.json")
    for p in data["patterns"]:
        for t in p["techniques"]:
            assert t in techniques, f"{p['id']} references unknown technique {t}"
        for d in p["dimensions"]:
            assert d in dims, f"{p['id']} references unknown dimension {d}"


def test_pattern_files_exist() -> None:
    # No dangling references: every file named in the pattern index must exist on disk.
    patterns_dir = KN / "packs" / "anthropic" / "patterns"
    data = _load(patterns_dir / "index.json")
    for p in data["patterns"]:
        assert (patterns_dir / p["file"]).is_file(), (
            f"{p['id']} references missing file {p['file']}"
        )


def test_no_provider_leak_in_common_pack() -> None:
    # The common pack must stay provider-neutral: no provider field, no anthropic-only ids.
    pack = _load(KN / "packs" / "common" / "pack.json")
    assert pack["provider"] is None
    rubric_text = (KN / "packs" / "common" / "rubric.json").read_text("utf-8").lower()
    assert "clm-" not in rubric_text, "common rubric must not cite provider claims directly"


# --- Policy files (M1 FR-3): misuse-policy, rewrite-policy, notices -------------------

_POLICY_FILES = ("misuse-policy.json", "rewrite-policy.json", "notices.json")
_RW_LIST_KEYS = (
    "allowed_transformations",
    "prohibited_transformations",
    "guarantees",
    "notice_rules",
)


def _misuse() -> dict[str, Any]:
    return _load(COMMON / "misuse-policy.json")


def _rewrite_policy() -> dict[str, Any]:
    return _load(COMMON / "rewrite-policy.json")


def _notices() -> dict[str, Any]:
    return _load(COMMON / "notices.json")


def _rewrite_report_notice_enum() -> set[str]:
    schema = _load(CONTRACTS / "rewrite-report" / "rewrite-report.schema.json")
    enum: set[str] = set(schema["properties"]["notices"]["items"]["enum"])
    return enum


def _misuse_ids() -> list[str]:
    data = _misuse()
    ids = [c["id"] for c in data["classes"]]
    ids += [s["id"] for s in data["procedure"]]
    ids += [t["id"] for t in data["decline_templates"]]
    return ids


def _rewrite_ids() -> list[str]:
    data = _rewrite_policy()
    ids: list[str] = []
    for key in _RW_LIST_KEYS:
        ids += [e["id"] for e in data[key]]
    return ids


def test_policy_stable_ids_unique_and_well_formed() -> None:
    # Refinement 1: one permanent registry per file; ids well-formed and never duplicated.
    misuse_ids = _misuse_ids()
    assert all(re.match(r"^MISUSE-[0-9]{3}$", i) for i in misuse_ids), misuse_ids
    assert len(misuse_ids) == len(set(misuse_ids)), "duplicate MISUSE id"

    rewrite_ids = _rewrite_ids()
    assert all(re.match(r"^RW-[0-9]{3}$", i) for i in rewrite_ids), rewrite_ids
    assert len(rewrite_ids) == len(set(rewrite_ids)), "duplicate RW id"

    notice_ids = [n["id"] for n in _notices()["notices"]]
    assert all(re.match(r"^NOTICE-[0-9]{3}$", i) for i in notice_ids), notice_ids
    assert len(notice_ids) == len(set(notice_ids)), "duplicate NOTICE id"


def test_misuse_classes_are_complete_and_distinct() -> None:
    classes = {c["class"] for c in _misuse()["classes"]}
    assert classes == {"legitimate", "ambiguous", "prohibited"}, classes


def test_policy_notice_values_subset_of_rewrite_report_enum() -> None:
    # The notice semantic key links to the frozen Rewrite Report notices enum.
    allowed = _rewrite_report_notice_enum()
    for n in _notices()["notices"]:
        assert n["notice"] in allowed, (
            f"notices.json uses '{n['notice']}' absent from the Rewrite Report enum"
        )
    for r in _rewrite_policy()["notice_rules"]:
        assert r["notice"] in allowed, (
            f"rewrite-policy notice_rule uses '{r['notice']}' absent from the Rewrite Report enum"
        )


def test_rewrite_notice_rules_resolve_to_notice_texts() -> None:
    # Every notice a rule attaches must have fixed text defined in notices.json.
    defined = {n["notice"] for n in _notices()["notices"]}
    for r in _rewrite_policy()["notice_rules"]:
        assert r["notice"] in defined, (
            f"notice_rule references notice '{r['notice']}' with no text in notices.json"
        )


def test_rewrite_policy_techniques_resolve() -> None:
    techniques = _technique_ids()
    for t in _rewrite_policy()["allowed_transformations"]:
        for tech in t["techniques"]:
            assert tech in techniques, f"{t['id']} references unknown technique {tech}"


def test_rewrite_policy_guarantee_refs_wellformed_and_unique() -> None:
    refs = [g["guarantee_ref"] for g in _rewrite_policy()["guarantees"]]
    assert all(re.match(r"^RG-[0-9]+$", r) for r in refs), refs
    assert len(refs) == len(set(refs)), "duplicate guarantee_ref binding"


def test_policy_files_are_provider_neutral() -> None:
    # KN-5: common-pack policy files must not cite provider claims directly.
    for fname in _POLICY_FILES:
        text = (COMMON / fname).read_text("utf-8").lower()
        assert "clm-" not in text, f"{fname} must not cite provider claims directly"
