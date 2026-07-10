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
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
KN = REPO / "core" / "knowledge"
CONTRACTS = REPO / "core" / "contracts"


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


def test_no_provider_leak_in_common_pack() -> None:
    # The common pack must stay provider-neutral: no provider field, no anthropic-only ids.
    pack = _load(KN / "packs" / "common" / "pack.json")
    assert pack["provider"] is None
    rubric_text = (KN / "packs" / "common" / "rubric.json").read_text("utf-8").lower()
    assert "clm-" not in rubric_text, "common rubric must not cite provider claims directly"
