"""Deterministic secret/PII redaction with typed placeholders (M2 FR-3).

Scrubs the secret and PII shapes ``docs/PRIVACY.md`` commits to — API keys and
tokens, PEM private-key blocks, ``password=`` / ``token=``-style assignments, and
email addresses — replacing each with a **typed placeholder** (``[REDACTED_*]``).
Redaction is:

- **deterministic and per-class stable:** the same class always maps to the same
  placeholder token (typed, never per-occurrence numbered), so the same secret
  redacts identically everywhere it appears. This is what lets the storage layer
  satisfy PR-1's requirement that redacted evidence quotes and IR segment text
  remain verbatim substrings of the redacted prompt (invariant PR-1, enforced at
  write time by the storage layer in FR-5 — this module only provides the
  mechanism).
- **idempotent:** placeholders match no pattern, so re-redacting redacted text is
  a no-op.

``redact_text`` is the atom. ``redact_report`` applies it to every content-bearing
field of a Report JSON (the "embedded report" of a history record). FR-5's storage
write path composes these onto the whole record; this module builds no record
envelope, computes no fingerprints, and performs no I/O.

**Honest limits (consistent with docs/PRIVACY.md "Honest limits").** This is
best-effort pattern matching, not a guarantee. It deliberately targets only the
classes above; it does not detect names, phone numbers, physical addresses,
credit-card numbers, novel/unprefixed key formats, or secrets split across
boundaries. Treat it as a safety net, not a vault; content that must never be
persisted should not be saved raw.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

# Each entry: (compiled pattern, replacement). Order matters — more specific
# patterns run first so a secret is not partially consumed by a broader one.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # PEM private-key / certificate blocks (multiline, most specific).
    (
        re.compile(r"-----BEGIN [A-Z0-9 ]+?-----.*?-----END [A-Z0-9 ]+?-----", re.DOTALL),
        "[REDACTED_PEM_KEY]",
    ),
    # HTTP bearer tokens: keep the scheme word, redact the credential. Runs before
    # the assignment rule so "Authorization: Bearer <token>" redacts the token, not
    # the scheme word.
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}"), "Bearer [REDACTED_TOKEN]"),
    # Sensitive-name assignments: keep the key and separator, redact the value.
    # Conservative key list (matches PRIVACY.md's "password=/token= assignments").
    # The value is a quoted string (single or double, embedded whitespace included)
    # or, unquoted, a run of non-whitespace — so quoted multi-word secrets are fully
    # redacted while unquoted behavior is unchanged.
    (
        re.compile(
            r"(?i)\b(password|passwd|pwd|secret|client_secret|token|api[_-]?key|"
            r"access[_-]?key)\b(\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|\S+)"
        ),
        r"\1\2[REDACTED_SECRET]",
    ),
    # Common vendor-prefixed API keys / tokens.
    (
        re.compile(
            r"\b(?:"
            r"(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}"  # OpenAI/Anthropic/Stripe-style
            r"|(?:ghp|gho|ghs|ghr|ghu)_[A-Za-z0-9]{20,}"  # GitHub tokens
            r"|github_pat_[A-Za-z0-9_]{20,}"  # GitHub fine-grained PAT
            r"|xox[baprs]-[A-Za-z0-9-]{10,}"  # Slack tokens
            r"|AKIA[0-9A-Z]{16}"  # AWS access key id
            r"|AIza[A-Za-z0-9_-]{35}"  # Google API key
            r")\b"
        ),
        "[REDACTED_API_KEY]",
    ),
    # Email addresses.
    (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
]


def redact_text(text: str) -> str:
    """Return ``text`` with every recognized secret/PII shape replaced by its
    typed placeholder. Deterministic and idempotent."""
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# Content-bearing string fields of a Report JSON, by location. Version ids, enum
# values (dimension, severity, kind, surface, gate, notices, confidence, technique),
# timestamps, and reference ids (segment, documented_match) are not free text and
# are left untouched.


def redact_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Return a redacted deep copy of a Report JSON: every content-bearing field
    (IR segment text/notes, finding explanation/fix and evidence quotes, event
    verbatim/notes, estimate hypothesis/reasoning, rewrite text/gate_reason and
    change descriptions) passed through :func:`redact_text`. The input is not
    mutated."""
    redacted: dict[str, Any] = _deep_copy(report)

    ir = redacted.get("ir")
    if isinstance(ir, dict):
        for segment in ir.get("segments", []):
            _redact_field(segment, "text")
            _redact_field(segment, "note")

    for finding in redacted.get("findings", []):
        _redact_field(finding, "explanation")
        _redact_field(finding, "fix")
        for evidence in finding.get("evidence", []):
            _redact_field(evidence, "quote")

    event = redacted.get("event")
    if isinstance(event, dict):
        _redact_field(event, "verbatim")
        _redact_field(event, "notes")

    estimates = redacted.get("estimates")
    if isinstance(estimates, list):
        for estimate in estimates:
            _redact_field(estimate, "hypothesis")
            _redact_field(estimate, "reasoning")

    rewrite = redacted.get("rewrite")
    if isinstance(rewrite, dict):
        _redact_field(rewrite, "text")
        _redact_field(rewrite, "gate_reason")
        for change in rewrite.get("changes", []):
            _redact_field(change, "change")
            _redact_field(change, "rationale")

    return redacted


def _redact_field(obj: Any, key: str) -> None:
    if isinstance(obj, dict) and isinstance(obj.get(key), str):
        obj[key] = redact_text(obj[key])


def _deep_copy(report: Mapping[str, Any]) -> dict[str, Any]:
    # The report is JSON by contract; a JSON round-trip is a stdlib-only deep copy
    # (the `copy` module is intentionally outside the runtime import allowlist).
    import json

    result: dict[str, Any] = json.loads(json.dumps(report))
    return result
