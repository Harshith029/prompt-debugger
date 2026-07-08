"""Contract-version alignment: library constants match the shipped schemas and the
Claude Code adapter manifest pins the versions that exist in the repo.
"""

from __future__ import annotations

import json
from pathlib import Path

from prompt_debugger import CONTRACT_VERSIONS

REPO = Path(__file__).resolve().parent.parent
CONTRACTS = REPO / "core" / "contracts"
ADAPTER_MANIFEST = REPO / "adapters" / "claude-code" / "adapter-manifest.json"

# Maps CONTRACT_VERSIONS keys to the schema file whose const version must match.
SCHEMA_VERSION_FIELD = {
    "prompt_ir": (CONTRACTS / "prompt-ir" / "prompt-ir.schema.json", "ir_version"),
    "report": (CONTRACTS / "report" / "report.schema.json", "report_version"),
    "rewrite_report": (
        CONTRACTS / "rewrite-report" / "rewrite-report.schema.json",
        "rewrite_version",
    ),
    "observable_event": (CONTRACTS / "events" / "observable-event.schema.json", "event_version"),
    "history_record": (CONTRACTS / "storage" / "history-record.schema.json", "record_version"),
    "config": (CONTRACTS / "storage" / "config.schema.json", "config_version"),
    "knowledge_manifest": (CONTRACTS / "knowledge" / "manifest.schema.json", "manifest_version"),
    "adapter_manifest": (
        CONTRACTS / "plugin-api" / "adapter-manifest.schema.json",
        "adapter_api_version",
    ),
    "prompt_tree": (CONTRACTS / "prompt-tree" / "prompt-tree.schema.json", "tree_version"),
}


def _const_version(schema_path: Path, field: str) -> int:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return int(schema["properties"][field]["const"])


def test_library_constants_match_schema_const_versions() -> None:
    for key, (schema_path, field) in SCHEMA_VERSION_FIELD.items():
        assert CONTRACT_VERSIONS[key] == _const_version(schema_path, field), key


def test_adapter_manifest_pins_current_versions() -> None:
    manifest = json.loads(ADAPTER_MANIFEST.read_text(encoding="utf-8"))
    consumes = manifest["consumes"]
    assert consumes["prompt_ir"] == CONTRACT_VERSIONS["prompt_ir"]
    assert consumes["report"] == CONTRACT_VERSIONS["report"]
    assert consumes["rewrite_report"] == CONTRACT_VERSIONS["rewrite_report"]
    assert consumes["observable_event"] == CONTRACT_VERSIONS["observable_event"]
    assert consumes["storage"] == CONTRACT_VERSIONS["history_record"]
    assert consumes["knowledge"] == CONTRACT_VERSIONS["knowledge_manifest"]
    assert consumes["prompt_tree"] == CONTRACT_VERSIONS["prompt_tree"]


def test_adapter_manifest_capabilities_match_skills() -> None:
    manifest = json.loads(ADAPTER_MANIFEST.read_text(encoding="utf-8"))
    caps = set(manifest["capabilities"])
    assert caps == {"analyze", "rewrite", "history"}
