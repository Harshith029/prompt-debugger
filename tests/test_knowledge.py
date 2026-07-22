"""Knowledge-accessor tests (M2 FR-7).

Covers the contract's query model (`load_manifest`, `load_pack`, `technique`,
`rubric_dimension`, `event_entry`, `claims`) against the real corpus: validated
loads, fail-closed errors for unknown packs/ids/statuses and for missing,
unparseable, or schema-invalid files (validation reuses the FR-1 validator),
determinism, and the read-only guarantee (accessors never mutate packs and
returned objects never alias the corpus).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from prompt_debugger import knowledge as pdknowledge

REPO = Path(__file__).resolve().parent.parent
KNOWLEDGE = REPO / "core" / "knowledge"


# --- query model against the real corpus ------------------------------------------------


def test_load_manifest_returns_validated_index() -> None:
    manifest = pdknowledge.load_manifest()
    assert manifest["manifest_version"] == 1
    assert manifest["knowledge_version"]
    pack_ids = {p["id"] for p in manifest["packs"]}
    assert {"common", "anthropic"} <= pack_ids


def test_load_pack_provider_carries_every_contract_file() -> None:
    pack = pdknowledge.load_pack("anthropic")
    assert pack["pack"]["provider"] == "anthropic"
    assert {"pack", "claims", "techniques", "events", "patterns_index"} == set(pack)
    assert pack["claims"]["claims"] and pack["techniques"]["techniques"]
    assert pack["events"]["entries"] and pack["patterns_index"]["patterns"]


def test_load_pack_common_carries_every_contract_file() -> None:
    pack = pdknowledge.load_pack("common")
    assert pack["pack"]["provider"] is None
    assert {"pack", "rubric", "misuse_policy", "rewrite_policy", "notices"} == set(pack)
    assert pack["rubric"]["dimensions"] and pack["notices"]["notices"]


def test_load_pack_unknown_id_fails_closed() -> None:
    with pytest.raises(pdknowledge.KnowledgeError, match="available: common, anthropic"):
        pdknowledge.load_pack("openai")


def test_technique_lookup_and_unknown_id() -> None:
    entry = pdknowledge.technique("T2")
    assert entry["name"] == "Add context and motivation"
    assert entry["source_claims"]
    with pytest.raises(pdknowledge.KnowledgeError, match="T99"):
        pdknowledge.technique("T99")


def test_rubric_dimension_lookup_and_unknown_id() -> None:
    entry = pdknowledge.rubric_dimension("R2")
    assert entry["name"] == "Missing context"
    with pytest.raises(pdknowledge.KnowledgeError, match="R99"):
        pdknowledge.rubric_dimension("R99")


def test_event_entry_lookup_and_unknown_id() -> None:
    entry = pdknowledge.event_entry("evt-model-switch-visible")
    assert entry["kind"] == "model_switch"
    with pytest.raises(pdknowledge.KnowledgeError, match="evt-nope"):
        pdknowledge.event_entry("evt-nope")


def test_claims_all_and_filtered() -> None:
    everything = pdknowledge.claims()
    assert everything
    assert all(c["status"] in ("recorded", "verified", "stale", "retired") for c in everything)
    verified = pdknowledge.claims(status="verified")
    assert verified
    assert all(c["status"] == "verified" for c in verified)
    assert len(verified) <= len(everything)


def test_claims_unknown_status_fails_closed_not_empty() -> None:
    with pytest.raises(pdknowledge.KnowledgeError, match="lifecycle"):
        pdknowledge.claims(status="active")


def test_accessors_are_deterministic() -> None:
    assert pdknowledge.load_pack("anthropic") == pdknowledge.load_pack("anthropic")
    assert pdknowledge.technique("T2") == pdknowledge.technique("T2")
    assert pdknowledge.claims(status="verified") == pdknowledge.claims(status="verified")


def test_accessors_never_mutate_packs_and_never_alias() -> None:
    def corpus_digest() -> str:
        digest = hashlib.sha256()
        for path in sorted(KNOWLEDGE.rglob("*.json")):
            digest.update(path.read_bytes())
        return digest.hexdigest()

    before = corpus_digest()
    entry = pdknowledge.technique("T2")
    entry["name"] = "mutated by caller"
    pack = pdknowledge.load_pack("common")
    pack["rubric"]["dimensions"].clear()
    # a fresh load is unaffected: returned objects never alias the corpus
    assert pdknowledge.technique("T2")["name"] == "Add context and motivation"
    assert pdknowledge.load_pack("common")["rubric"]["dimensions"]
    assert corpus_digest() == before  # nothing on disk changed


# --- fail-closed loading (validate what they load) --------------------------------------


def _write_tree(root: Path, manifest: object, files: dict[str, object]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(
        manifest if isinstance(manifest, str) else json.dumps(manifest), encoding="utf-8"
    )
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            content if isinstance(content, str) else json.dumps(content), encoding="utf-8"
        )


_TEST_MANIFEST = {
    "manifest_version": 1,
    "knowledge_version": "2026.07-test",
    "packs": [{"id": "testprov", "kind": "provider", "path": "packs/testprov"}],
}


def test_schema_invalid_knowledge_file_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_tree(
        tmp_path,
        _TEST_MANIFEST,
        {
            # additionalProperties: false everywhere -> the stray key is invalid
            "packs/testprov/techniques.json": {
                "file_version": 1,
                "techniques": [],
                "bogus": True,
            }
        },
    )
    monkeypatch.setattr(pdknowledge, "knowledge_dir", lambda: tmp_path)
    with pytest.raises(pdknowledge.KnowledgeValidationError, match="failed validation"):
        pdknowledge.technique("T1")


def test_unparseable_manifest_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_tree(tmp_path, "not json {", {})
    monkeypatch.setattr(pdknowledge, "knowledge_dir", lambda: tmp_path)
    with pytest.raises(pdknowledge.KnowledgeError, match="invalid JSON"):
        pdknowledge.load_manifest()


def test_missing_knowledge_file_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_tree(tmp_path, _TEST_MANIFEST, {})  # pack dir has no files at all
    monkeypatch.setattr(pdknowledge, "knowledge_dir", lambda: tmp_path)
    with pytest.raises(pdknowledge.KnowledgeError, match="missing"):
        pdknowledge.load_pack("testprov")
