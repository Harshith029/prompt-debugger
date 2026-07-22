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


def test_active_entries_cite_only_verified_claims() -> None:
    # KN-2: an active technique/event must not depend on a non-verified claim.
    # The claim lifecycle is recorded/verified/stale/retired (claims.schema.json);
    # 'verified' is the citable state. The earlier version of this test compared
    # against a nonexistent 'active' claim status and could never enforce KN-2.
    claims = _load(KN / "packs" / "anthropic" / "claims.json")["claims"]
    verified = {c["id"] for c in claims if c["status"] == "verified"}
    for fname in ("techniques.json", "events.json"):
        data = _load(KN / "packs" / "anthropic" / fname)
        entries = data.get("techniques") or data.get("entries") or []
        for entry in entries:
            if entry["status"] == "active":
                for c in entry["source_claims"]:
                    assert c in verified, f"active {entry['id']} cites non-verified claim {c}"


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


# --- FR-5: pattern-library completeness (KN-9) ----------------------------------------

_PATTERNS_DIR = KN / "packs" / "anthropic" / "patterns"
_PATTERN_BODY_SECTIONS = (
    "## When it applies",
    "## Transformation",
    "## Example",
    "**Before**",
    "**After**",
    "## Why it helps",
)


def _patterns() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = _load(_PATTERNS_DIR / "index.json")["patterns"]
    return entries


def test_pattern_ids_and_files_are_unique() -> None:
    ids = [p["id"] for p in _patterns()]
    files = [p["file"] for p in _patterns()]
    assert len(ids) == len(set(ids)), "duplicate pattern ids in the index"
    assert len(files) == len(set(files)), "one body file is claimed by two index entries"


def test_pattern_index_and_bodies_are_bijective() -> None:
    # KN-9: no orphaned body files — every on-disk pattern body is indexed, and
    # (with test_pattern_files_exist) every indexed body is on disk.
    indexed = {p["file"] for p in _patterns()}
    on_disk = {f.name for f in _PATTERNS_DIR.glob("*.md") if f.name != "README.md"}
    assert on_disk == indexed, (
        f"orphaned bodies: {sorted(on_disk - indexed)}; missing: {sorted(indexed - on_disk)}"
    )


def test_pattern_bodies_are_complete_and_consistent() -> None:
    # KN-9: no stubs — every body carries the full authored structure and agrees
    # with its index entry (id, title, dimensions, techniques).
    for p in _patterns():
        body = (_PATTERNS_DIR / p["file"]).read_text(encoding="utf-8")
        for section in _PATTERN_BODY_SECTIONS:
            assert section in body, f"{p['file']} is missing section {section!r}"
        assert f"`{p['id']}`" in body, f"{p['file']} does not state its id {p['id']}"
        assert p["title"] in body, f"{p['file']} does not carry its index title"
        for ref in (*p["dimensions"], *p["techniques"]):
            assert ref in body, f"{p['file']} does not mention its indexed ref {ref}"
        assert body.count("```") >= 4, f"{p['file']} lacks before/after example blocks"


def test_pattern_library_covers_every_rubric_dimension() -> None:
    # KN-9: the library's documented completeness definition (patterns/README.md) —
    # every rubric dimension, the analyzer's finding surface, has at least one pattern.
    covered: set[str] = set()
    for p in _patterns():
        covered.update(p["dimensions"])
    assert covered == _rubric_ids(), f"uncovered dimensions: {sorted(_rubric_ids() - covered)}"


# --- FR-6: knowledge snapshot label alignment (KN-10) ---------------------------------


def test_knowledge_snapshot_labels_agree() -> None:
    # KN-10: manifest knowledge_version covers the whole corpus snapshot (knowledge
    # contract), and no file's label may desync from its pack snapshot
    # (docs/process/policy-review.md). All snapshot labels name one corpus state.
    snapshot = _load(KN / "manifest.json")["knowledge_version"]
    labels = {
        "common pack_version": _load(COMMON / "pack.json")["pack_version"],
        "anthropic pack_version": _load(KN / "packs" / "anthropic" / "pack.json")["pack_version"],
        "rubric_version": _load(COMMON / "rubric.json")["rubric_version"],
        "taxonomy_version": _load(KN / "packs" / "anthropic" / "events.json")["taxonomy_version"],
        "misuse policy_version": _misuse()["policy_version"],
        "rewrite policy_version": _rewrite_policy()["policy_version"],
        "notices policy_version": _notices()["policy_version"],
    }
    for name, value in labels.items():
        assert value == snapshot, f"{name} is '{value}', manifest snapshot is '{snapshot}'"
    # Non-policy prose companions state the same label in their headers (the policy
    # companions' headers are already enforced by the PL-7/PL-8 tests above).
    for companion in (
        "packs/common/rubric.md",
        "packs/anthropic/techniques.md",
        "packs/anthropic/events.md",
    ):
        header = (KN / companion).read_text(encoding="utf-8").splitlines()[0]
        assert snapshot in header, f"{companion} header does not state '{snapshot}'"


# --- FR-8: promotion state of the claim-grounded classes ------------------------------


def test_fr8_promotion_state_of_claim_grounded_classes() -> None:
    # specs/M2.md FR-8 acceptance criterion, made executable: every technique and
    # event-taxonomy entry whose cited claims are all 'verified' is 'active'
    # (the KN-2 criterion applied per entry); rubric dimensions and patterns
    # remain 'draft' — they carry no claim-provenance relation, so their
    # promotion criterion is deferred as open choice O7, not silently decided.
    claim_status = {
        c["id"]: c["status"] for c in _load(KN / "packs" / "anthropic" / "claims.json")["claims"]
    }
    techniques = _load(KN / "packs" / "anthropic" / "techniques.json")["techniques"]
    for t in techniques:
        # Techniques must cite claims to leave draft at all (enforced above), so
        # the promotion criterion is only asserted where citations exist.
        if t["source_claims"] and all(claim_status[c] == "verified" for c in t["source_claims"]):
            assert t["status"] == "active", f"{t['id']}: all claims verified but not active"
    entries = _load(KN / "packs" / "anthropic" / "events.json")["entries"]
    for e in entries:
        # "Every cited claim is verified" is vacuously satisfied by an empty
        # citation list: kinds 'none'/'unknown' assert no provider behavior (the
        # KN-1 carve-out) and were promoted under the recorded FR-8 decision
        # (CHANGELOG), so entries like evt-none must be 'active' too.
        if all(claim_status[c] == "verified" for c in e["source_claims"]):
            assert e["status"] == "active", f"{e['id']}: promotion criterion holds but not active"
    for d in _load(COMMON / "rubric.json")["dimensions"]:
        assert d["status"] == "draft", f"{d['id']}: rubric promotion is deferred (O7)"
    patterns = _load(KN / "packs" / "anthropic" / "patterns" / "index.json")["patterns"]
    for p in patterns:
        assert p["status"] == "draft", f"{p['id']}: pattern promotion is deferred (O7)"


# --- FR-5.1: After examples demonstrate only permitted transformations ----------------

_PLACEHOLDER_OR_TAG = re.compile(r"<[^<>]*>")
_NUMBERED_LIST_MARKER = re.compile(r"^\s*\d+\.\s", re.MULTILINE)


def _fenced_block_after(marker: str, body: str, fname: str) -> str:
    idx = body.find(marker)
    assert idx != -1, f"{fname} has no {marker} block"
    start = body.index("```", idx) + 3
    end = body.index("```", start)
    return body[start:end]


def test_pattern_after_examples_introduce_no_literals_absent_from_before() -> None:
    # RG-7/RG-8 made executable for the library's own examples (patterns/README.md):
    # an After may not invent dates, metrics, thresholds, or file-like names. The
    # objectively checkable slice: numeric literals and dotted tokens in the After —
    # outside angle-bracket placeholder slots/tags and numbered-list markers — must
    # already appear in the Before. Unknowable information is expressed as
    # angle-bracket slots, never as invented content.
    for p in _patterns():
        body = (_PATTERNS_DIR / p["file"]).read_text(encoding="utf-8")
        before = _fenced_block_after("**Before**", body, p["file"])
        after = _fenced_block_after("**After**", body, p["file"])
        cleaned = _PLACEHOLDER_OR_TAG.sub(" ", after)
        cleaned = _NUMBERED_LIST_MARKER.sub(" ", cleaned)
        for num in re.findall(r"\d+", cleaned):
            assert num in before, f"{p['file']}: After invents numeric literal '{num}'"
        for tok in re.findall(r"\b\w+\.\w+\b", cleaned):
            assert tok in before, f"{p['file']}: After invents dotted token '{tok}'"


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


# --- FR-3.1: extended policy integrity coverage ---------------------------------------

# The architecture (docs/design/policy-architecture.md §3) defines exactly these
# guarantees; rewrite-policy.md documents that the policy binds all of them.
_RG_SET = {f"RG-{n}" for n in range(1, 9)}

_POLICY_COMPANIONS = {
    "misuse-policy.json": "misuse-policy.md",
    "rewrite-policy.json": "rewrite-policy.md",
    "notices.json": "notices.md",
}


def test_rewrite_policy_binds_exactly_the_documented_rg_set() -> None:
    # RG membership: every guarantee_ref is a documented RG id, and all eight are bound.
    refs = {g["guarantee_ref"] for g in _rewrite_policy()["guarantees"]}
    assert refs == _RG_SET, f"bound {sorted(refs)}, documented {sorted(_RG_SET)}"


def test_every_rewrite_report_notice_has_exactly_one_text() -> None:
    # Notice coverage: the notices file covers the full Rewrite Report enum, once each.
    enum = _rewrite_report_notice_enum()
    keys = [n["notice"] for n in _notices()["notices"]]
    assert set(keys) == enum, f"texts for {sorted(set(keys))}, enum {sorted(enum)}"
    assert len(keys) == len(set(keys)), "a notice identity has more than one text"


def test_policy_versions_align_with_pack_snapshot() -> None:
    # policy-review.md: never bump one file's label out of sync with its pack snapshot.
    pack_version = _load(COMMON / "pack.json")["pack_version"]
    for fname in _POLICY_FILES:
        pv = _load(COMMON / fname)["policy_version"]
        assert pv == pack_version, f"{fname} policy_version '{pv}' != pack '{pack_version}'"


def test_policy_companions_carry_the_same_ids() -> None:
    # Each .md companion documents "Ids match one-to-one" with its JSON.
    id_lists = {
        "misuse-policy.json": _misuse_ids(),
        "rewrite-policy.json": _rewrite_ids(),
        "notices.json": [n["id"] for n in _notices()["notices"]],
    }
    for fname, companion in _POLICY_COMPANIONS.items():
        md = (COMMON / companion).read_text("utf-8")
        for entry_id in id_lists[fname]:
            assert entry_id in md, f"{companion} is missing id {entry_id} from {fname}"


def _blockquotes(companion: str) -> list[str]:
    md_lines = (COMMON / companion).read_text("utf-8").splitlines()
    return [line[2:] for line in md_lines if line.startswith("> ")]


def test_notices_md_quotes_match_json_verbatim() -> None:
    # notices.json is the single source of truth for wording; notices.md is derived and
    # quotes each text verbatim (documented in notices.md and the Rewrite Report contract).
    json_texts = [n["text"] for n in _notices()["notices"]]
    assert _blockquotes("notices.md") == json_texts, (
        "notices.md quotes have drifted from notices.json texts"
    )


def test_decline_template_md_quotes_match_json_verbatim() -> None:
    # PL-7: misuse-policy.json is the single source of truth for decline wording;
    # misuse-policy.md is derived and quotes each template verbatim.
    json_texts = [t["text"] for t in _misuse()["decline_templates"]]
    assert _blockquotes("misuse-policy.md") == json_texts, (
        "misuse-policy.md decline quotes have drifted from misuse-policy.json texts"
    )


def test_companion_headers_state_their_policy_version() -> None:
    # Each companion's title line documents its policy_version; it must match the JSON.
    for fname, companion in _POLICY_COMPANIONS.items():
        version = _load(COMMON / fname)["policy_version"]
        header = (COMMON / companion).read_text("utf-8").splitlines()[0]
        assert f"policy_version {version}" in header, (
            f"{companion} header does not state policy_version {version}"
        )


def test_policy_files_use_no_provider_names() -> None:
    # policy-review.md review expectations: no provider or product names in common-pack
    # policy files (beyond the clm- citation rule already tested above).
    for fname in list(_POLICY_FILES) + list(_POLICY_COMPANIONS.values()):
        text = (COMMON / fname).read_text("utf-8").lower()
        for banned in ("anthropic", "claude"):
            assert banned not in text, f"{fname} mentions provider name '{banned}'"


# --- FR-4: taxonomy prose completeness and provenance ---------------------------------

_EVENT_PROSE_FIELDS = ("title", "user_sees", "can_conclude", "cannot_conclude")


def _events() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = _load(KN / "packs" / "anthropic" / "events.json")["entries"]
    return entries


def test_taxonomy_prose_is_complete() -> None:
    # M1 FR-4: every entry carries complete prose, and api_correlate is present prose
    # for every entry that has an API correlate to describe (all but kind 'none').
    for e in _events():
        for field in _EVENT_PROSE_FIELDS:
            value = e[field]
            assert isinstance(value, str) and value.strip(), f"{e['id']}.{field} is empty"
        if e["kind"] == "none":
            assert e["api_correlate"] is None, "evt-none has no API correlate by definition"
        else:
            correlate = e["api_correlate"]
            assert isinstance(correlate, str) and correlate.strip(), (
                f"{e['id']}.api_correlate must describe the documented correlate"
            )


def test_events_asserting_provider_behavior_cite_claims() -> None:
    # KN-1, executable for the taxonomy: every entry other than the no-event entry
    # asserts provider behavior and must cite at least one claim.
    for e in _events():
        if e["kind"] not in {"none", "unknown"}:
            assert e["source_claims"], f"{e['id']} asserts provider behavior, cites no claim"


def test_events_cite_only_verified_claims() -> None:
    # KN-7 (FR-4.1): every observable event is backed by verified claims — every
    # cited claim must be status 'verified', regardless of the entry's own status.
    claims = {c["id"]: c for c in _load(KN / "packs" / "anthropic" / "claims.json")["claims"]}
    for e in _events():
        for cid in e["source_claims"]:
            status = claims[cid]["status"]
            assert status == "verified", f"{e['id']} cites {cid} with status '{status}'"


def test_claim_lifecycle_and_provenance() -> None:
    # KN-7 (FR-4.1): claim statuses stay within the schema's documented lifecycle,
    # and every claim carries auditable provenance (https source, ISO dates,
    # last_verified never earlier than retrieval).
    schema = _load(CONTRACTS / "knowledge" / "claims.schema.json")
    lifecycle = set(schema["properties"]["claims"]["items"]["properties"]["status"]["enum"])
    assert lifecycle == {"recorded", "verified", "stale", "retired"}, (
        "claim lifecycle changed; update KN-2/KN-7 and their tests deliberately"
    )
    date = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for c in _load(KN / "packs" / "anthropic" / "claims.json")["claims"]:
        assert c["status"] in lifecycle, f"{c['id']} has status outside the lifecycle"
        assert c["url"].startswith("https://"), f"{c['id']} source is not https"
        assert date.match(c["retrieved"]), f"{c['id']} retrieved date malformed"
        assert date.match(c["last_verified"]), f"{c['id']} last_verified date malformed"
        assert c["last_verified"] >= c["retrieved"], (
            f"{c['id']} was 'verified' before it was retrieved"
        )


def test_no_orphaned_verified_claims() -> None:
    # KN-8 (FR-4.2): every verified claim is consumed by at least one structured
    # knowledge artifact (a technique or an event-taxonomy entry). An orphaned
    # verified claim is dead weight the quarterly re-verification would maintain
    # for nothing — either integrate it with provenance or retire it.
    cited: set[str] = set()
    for fname in ("techniques.json", "events.json"):
        data = _load(KN / "packs" / "anthropic" / fname)
        for entry in data.get("techniques") or data.get("entries") or []:
            cited.update(entry["source_claims"])
    for c in _load(KN / "packs" / "anthropic" / "claims.json")["claims"]:
        if c["status"] == "verified":
            assert c["id"] in cited, f"verified claim {c['id']} is cited by no artifact"


def test_event_kinds_are_unique() -> None:
    # EV-4 (FR-4.1): one observation must never have two equally valid entries;
    # a duplicated kind would reintroduce that ambiguity.
    kinds = [e["kind"] for e in _events()]
    assert len(kinds) == len(set(kinds)), f"duplicate taxonomy kinds: {sorted(kinds)}"


def test_observation_channel_rule_is_disjoint() -> None:
    # EV-4 (FR-4.1): the observation-channel selection rule (events.md) — API-native
    # entries list exactly the 'api' surface; rendered-message entries never list it.
    # Disjoint surface sets make classification deterministic for the paired kinds.
    for e in _events():
        if e["kind"].startswith("api_"):
            assert e["surfaces"] == ["api"], (
                f"{e['id']} is API-native and must list exactly the 'api' surface"
            )
        elif e["kind"] in {"refusal_message", "model_switch"}:
            assert "api" not in e["surfaces"], (
                f"{e['id']} is a rendered-surface entry and must not list 'api'"
            )


def test_inline_claim_references_resolve_and_are_cited() -> None:
    # Provenance chain: a claim id named inline in taxonomy prose must exist in the
    # registry AND appear in that entry's source_claims (no dangling or uncited mentions).
    claims = _claim_ids()
    for e in _events():
        for field in (*_EVENT_PROSE_FIELDS, "api_correlate"):
            value = e[field]
            if value is None:
                continue
            for ref in re.findall(r"clm-[a-z0-9-]+", value):
                assert ref in claims, f"{e['id']}.{field} references unknown claim {ref}"
                assert ref in e["source_claims"], (
                    f"{e['id']}.{field} mentions {ref} but does not cite it"
                )


def test_policy_version_pattern_is_shared_and_calendar_valid() -> None:
    # FR-3.1 Issue 5: the three schemas share one policy_version pattern that rejects
    # calendar-impossible months while accepting every shipped label.
    patterns = set()
    for name in ("misuse-policy", "rewrite-policy", "notices"):
        schema = _load(CONTRACTS / "knowledge" / f"{name}.schema.json")
        patterns.add(schema["properties"]["policy_version"]["pattern"])
    assert len(patterns) == 1, f"policy_version patterns diverge: {patterns}"
    pattern = patterns.pop()
    for good in ("2026.01", "2026.07-draft", "2026.12", "1999.10-rc1"):
        assert re.fullmatch(pattern, good), f"'{good}' should validate"
    for bad in ("2026.00", "2026.13", "2026.7", "2026.07-", "2026.07-DRAFT", "26.07"):
        assert not re.fullmatch(pattern, bad), f"'{bad}' should be rejected"
