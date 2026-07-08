"""prompt-debugger core library (host-neutral).

Runtime is standard-library only (ADR-0006). This package holds the deterministic
core — storage, schema validation, evidence verification, redaction, sanitization,
rendering, and the CLI that adapters call. Implementation lands in Milestone M2;
at M0 this package defines only version and contract-version constants so the
scaffold imports cleanly and CI has a real module to type-check.
"""

from __future__ import annotations

__version__ = "0.1.0a0"

# Contract versions this library targets. Adapters pin against these; the
# schema files under core/contracts/ are the source of truth. Kept here so
# Python code and CI can assert alignment without parsing every schema.
CONTRACT_VERSIONS: dict[str, int] = {
    "prompt_ir": 1,
    "report": 1,
    "rewrite_report": 1,
    "observable_event": 1,
    "history_record": 1,
    "config": 1,
    "knowledge_manifest": 1,
    "adapter_manifest": 1,
    "prompt_tree": 1,
}

__all__ = ["CONTRACT_VERSIONS", "__version__"]
