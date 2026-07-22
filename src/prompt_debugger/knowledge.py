"""Knowledge Engine accessors (M2 FR-7).

The read-only query model the knowledge contract fixed at M0
(``core/contracts/knowledge/CONTRACT.md`` §Query model, ADR-0007):
``load_manifest()``, ``load_pack(provider)``, ``technique(id)``,
``rubric_dimension(id)``, ``event_entry(id)``, ``claims(status=...)``.
Consumers query packs through these accessors; nobody parses knowledge ad hoc.

- **Validate what they load:** every knowledge file is validated against its
  schema in ``core/contracts/knowledge/`` via the FR-1 validator before any
  content is returned — a missing, unparseable, or schema-invalid file is a
  fail-closed error, never a partial result. Cross-file integrity (the KN-*
  invariants) remains enforced by the contract's integrity tests, not
  re-implemented here.
- **Never mutate packs:** accessors only read. Every call parses the files
  fresh and returns new objects (no shared cache), so no caller can reach the
  corpus through a returned value.
- **Deterministic:** output is exactly the validated file content in file
  order; no wall-clock, locale, or environment dependence.

Recorded implementation decisions (the contract fixes the accessor names and
obligations; these shapes are this module's recorded choices):

- ``load_pack``'s argument is the **manifest pack id** — for provider packs it
  equals the provider identifier (``"anthropic"``), and ``"common"`` retrieves
  the provider-neutral pack.
- ``load_pack`` returns ``{"pack": <pack.json>, ...}`` plus one key per data
  file the contract's Structure section assigns to the pack's kind — common:
  ``rubric``, ``misuse_policy``, ``rewrite_policy``, ``notices``; provider:
  ``claims``, ``techniques``, ``events``, ``patterns_index`` — each the
  validated content of the corresponding file.
- Id lookups search packs in manifest order (``technique``/``event_entry``
  over provider packs, ``rubric_dimension`` over common packs) and fail closed
  when no pack defines the id.
- ``claims(status=...)`` concatenates provider packs' registries in manifest
  order; the optional filter must name a lifecycle state from the contract
  (``recorded``/``verified``/``stale``/``retired``) — an unknown status is a
  fail-closed error, not an empty result.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import contracts_dir, knowledge_dir
from .schema import validate

# The claim lifecycle fixed by the knowledge contract (§Versioning; KN-7).
_CLAIM_STATUSES = ("recorded", "verified", "stale", "retired")

# Data files per pack kind, exactly the contract's Structure section:
# result key -> (file within the pack, schema in core/contracts/knowledge/).
_COMMON_FILES: dict[str, tuple[str, str]] = {
    "rubric": ("rubric.json", "rubric.schema.json"),
    "misuse_policy": ("misuse-policy.json", "misuse-policy.schema.json"),
    "rewrite_policy": ("rewrite-policy.json", "rewrite-policy.schema.json"),
    "notices": ("notices.json", "notices.schema.json"),
}
_PROVIDER_FILES: dict[str, tuple[str, str]] = {
    "claims": ("claims.json", "claims.schema.json"),
    "techniques": ("techniques.json", "techniques.schema.json"),
    "events": ("events.json", "events.schema.json"),
    "patterns_index": ("patterns/index.json", "patterns-index.schema.json"),
}


class KnowledgeError(Exception):
    """Base class for knowledge-access failures. Every failure is specific and
    fail-closed; accessors never return partial or unvalidated content."""


class KnowledgeValidationError(KnowledgeError):
    """A knowledge file failed validation against its contract schema."""

    def __init__(self, message: str, problems: list[str]) -> None:
        self.problems = problems
        super().__init__(message + ": " + "; ".join(problems))


def load_manifest() -> dict[str, Any]:
    """The validated knowledge manifest: ``knowledge_version`` + pack index."""
    return _load_validated(knowledge_dir() / "manifest.json", "manifest.schema.json")


def load_pack(provider: str) -> dict[str, Any]:
    """One pack's validated metadata and data files, keyed as documented above.

    ``provider`` is the manifest pack id (equal to the provider identifier for
    provider packs; ``"common"`` for the provider-neutral pack)."""
    entry = _manifest_entry(provider)
    pack_dir = knowledge_dir() / entry["path"]
    result: dict[str, Any] = {"pack": _load_validated(pack_dir / "pack.json", "pack.schema.json")}
    files = _COMMON_FILES if entry["kind"] == "common" else _PROVIDER_FILES
    for key, (file_name, schema_name) in files.items():
        result[key] = _load_validated(pack_dir / file_name, schema_name)
    return result


def technique(technique_id: str) -> dict[str, Any]:
    """The technique entry with this id, searched across provider packs."""
    for pack_dir in _pack_dirs("provider"):
        data = _load_validated(pack_dir / "techniques.json", "techniques.schema.json")
        for entry in data["techniques"]:
            if entry["id"] == technique_id:
                found: dict[str, Any] = entry
                return found
    raise KnowledgeError(f"no technique '{technique_id}' in any provider pack")


def rubric_dimension(dimension_id: str) -> dict[str, Any]:
    """The rubric dimension with this id, from the common pack's rubric."""
    for pack_dir in _pack_dirs("common"):
        data = _load_validated(pack_dir / "rubric.json", "rubric.schema.json")
        for entry in data["dimensions"]:
            if entry["id"] == dimension_id:
                found: dict[str, Any] = entry
                return found
    raise KnowledgeError(f"no rubric dimension '{dimension_id}' in any common pack")


def event_entry(entry_id: str) -> dict[str, Any]:
    """The event-taxonomy entry with this id, searched across provider packs."""
    for pack_dir in _pack_dirs("provider"):
        data = _load_validated(pack_dir / "events.json", "events.schema.json")
        for entry in data["entries"]:
            if entry["id"] == entry_id:
                found: dict[str, Any] = entry
                return found
    raise KnowledgeError(f"no event-taxonomy entry '{entry_id}' in any provider pack")


def claims(status: str | None = None) -> list[dict[str, Any]]:
    """Claim-registry entries from every provider pack, in manifest order.

    ``status`` optionally filters to one lifecycle state; an unknown status is
    a fail-closed error (the lifecycle is contract-fixed), never an empty list."""
    if status is not None and status not in _CLAIM_STATUSES:
        raise KnowledgeError(
            f"unknown claim status '{status}'; the contract's lifecycle is: "
            + ", ".join(_CLAIM_STATUSES)
        )
    out: list[dict[str, Any]] = []
    for pack_dir in _pack_dirs("provider"):
        data = _load_validated(pack_dir / "claims.json", "claims.schema.json")
        for claim in data["claims"]:
            if status is None or claim["status"] == status:
                out.append(claim)
    return out


# --- internals -------------------------------------------------------------------------


def _manifest_entry(pack_id: str) -> dict[str, Any]:
    manifest = load_manifest()
    for entry in manifest["packs"]:
        if entry["id"] == pack_id:
            found: dict[str, Any] = entry
            return found
    available = ", ".join(p["id"] for p in manifest["packs"])
    raise KnowledgeError(f"no pack '{pack_id}' in the manifest; available: {available}")


def _pack_dirs(kind: str) -> list[Path]:
    """Pack directories of one kind, in manifest order (the search order for
    id lookups — deterministic and recorded)."""
    manifest = load_manifest()
    return [knowledge_dir() / entry["path"] for entry in manifest["packs"] if entry["kind"] == kind]


def _load_validated(path: Path, schema_name: str) -> dict[str, Any]:
    """Load one knowledge file and validate it against its contract schema
    (FR-1) before returning it. Missing, unparseable, or invalid files are
    fail-closed errors; content is returned exactly as stored, never mutated."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise KnowledgeError(f"knowledge file missing: {path}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise KnowledgeError(f"invalid JSON in knowledge file {path}: {exc}") from exc
    schema = json.loads((contracts_dir() / "knowledge" / schema_name).read_text(encoding="utf-8"))
    errors = validate(data, schema)
    if errors:
        raise KnowledgeValidationError(f"knowledge file {path} failed validation", errors)
    result: dict[str, Any] = data
    return result
