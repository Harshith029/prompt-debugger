"""Unit tests for the redaction module (M2 FR-3).

True-positive corpus (each PRIVACY.md secret/PII class is scrubbed), false-positive
corpus (benign text is left intact), determinism/idempotency, the PR-1 substring
property redaction must support, and whole-report field coverage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from prompt_debugger import redact

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

_PEM = (
    "-----BEGIN RSA PRIVATE KEY-----\n"
    "MIIEowIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF0qN\n"
    "-----END RSA PRIVATE KEY-----"
)

# (label, input, placeholder that must appear, secret fragment that must vanish)
_TRUE_POSITIVES: list[tuple[str, str, str, str]] = [
    (
        "openai-key",
        "use sk-ABCDEFGHIJKLMNOP1234 now",
        "[REDACTED_API_KEY]",
        "sk-ABCDEFGHIJKLMNOP1234",
    ),
    ("aws-key", "id AKIAIOSFODNN7EXAMPLE here", "[REDACTED_API_KEY]", "AKIAIOSFODNN7EXAMPLE"),
    (
        "github-token",
        "token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345",
        "[REDACTED_API_KEY]",
        "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345",
    ),
    ("pem-block", f"key:\n{_PEM}\nend", "[REDACTED_PEM_KEY]", "MIIEowIBAAKCAQEA"),
    ("password-assign", "password=hunter2 rest", "[REDACTED_SECRET]", "hunter2"),
    ("token-assign-colon", "token: abc123XYZ890", "[REDACTED_SECRET]", "abc123XYZ890"),
    ("api-key-assign", "api_key = MYSUPERSECRETVALUE", "[REDACTED_SECRET]", "MYSUPERSECRETVALUE"),
    ("bearer", "Authorization: Bearer eyJhbGciOiJIUzI1", "[REDACTED_TOKEN]", "eyJhbGciOiJIUzI1"),
    ("email", "reach me at alice@example.com please", "[REDACTED_EMAIL]", "alice@example.com"),
]

_FALSE_POSITIVES: list[str] = [
    "Explain how our caching layer works.",
    "The formula e=mc2 is famous.",
    "well-being and long-term planning",
    "meet at 3=00 or 4:30",
    "version 2026.07-m1 shipped",
    "the @mention feature and user@host without a tld",
    "primary key of the table is the id column",
    "R10 severity high with dimension R2",
]


def test_true_positive_corpus() -> None:
    for label, text, placeholder, secret in _TRUE_POSITIVES:
        out = redact.redact_text(text)
        assert placeholder in out, f"{label}: placeholder missing: {out!r}"
        assert secret not in out, f"{label}: secret survived: {out!r}"


def test_false_positive_corpus_is_untouched() -> None:
    for text in _FALSE_POSITIVES:
        assert redact.redact_text(text) == text, f"benign text was altered: {text!r}"


def test_redaction_is_deterministic_and_class_stable() -> None:
    text = "keys sk-ABCDEFGHIJKLMNOP1234 and sk-ZZZZZZZZZZZZZZZZ9999"
    first = redact.redact_text(text)
    assert first == redact.redact_text(text)  # deterministic
    # per-class stable: both keys collapse to the same typed placeholder
    assert first.count("[REDACTED_API_KEY]") == 2
    assert "sk-" not in first


def test_redaction_is_idempotent() -> None:
    for _, text, _, _ in _TRUE_POSITIVES:
        once = redact.redact_text(text)
        assert redact.redact_text(once) == once


def test_supports_pr1_substring_property() -> None:
    # A whole secret shared by the prompt and an evidence-quote substring collapses
    # to the same placeholder in both, so the redacted quote stays a substring of
    # the redacted prompt — the consistency PR-1 (enforced by storage in FR-5) needs.
    prompt = "connect using key sk-ABCDEFGHIJKLMNOP1234 today"
    quote = "key sk-ABCDEFGHIJKLMNOP1234 today"  # verbatim substring of prompt
    assert quote in prompt
    assert redact.redact_text(quote) in redact.redact_text(prompt)


# (input, the quoted secret whose every word must be gone)
_QUOTED_ASSIGNMENTS: list[tuple[str, str]] = [
    ('password = "correct horse battery staple"', "correct horse battery staple"),
    ('token: "multiple words here"', "multiple words here"),
    ('api_key = "value with spaces"', "value with spaces"),
    ("secret = 'single quoted words'", "single quoted words"),
]


def test_quoted_assignment_values_are_fully_redacted() -> None:
    for text, secret in _QUOTED_ASSIGNMENTS:
        out = redact.redact_text(text)
        assert "[REDACTED_SECRET]" in out, f"placeholder missing: {out!r}"
        assert secret not in out, f"quoted secret survived whole: {out!r}"
        for word in secret.split():  # no partial-word leak past the first space
            assert word not in out, f"leaked word {word!r} in {out!r}"
        assert out == redact.redact_text(text)  # deterministic


def test_unquoted_assignment_behavior_is_unchanged() -> None:
    assert redact.redact_text("password=hunter2 rest") == "password=[REDACTED_SECRET] rest"
    assert redact.redact_text("token: abc123XYZ890") == "token: [REDACTED_SECRET]"


def test_redact_report_inherits_quoted_assignment_fix() -> None:
    report: dict[str, Any] = {
        "report_version": 1,
        "created_at": "2026-07-07T12:00:00Z",
        "knowledge": {"knowledge_version": "x", "provider": "anthropic", "rubric_version": "x"},
        "ir": {
            "ir_version": 1,
            "unsegmented_remainder": True,
            "segments": [
                {"id": "s1", "kind": "task", "text": 'password = "correct horse battery staple"'}
            ],
        },
        "findings": [],
    }
    blob = json.dumps(redact.redact_report(report))
    assert "horse battery staple" not in blob
    assert "[REDACTED_SECRET]" in blob


# --- redact_report --------------------------------------------------------------------


def _report_with_secrets() -> dict[str, Any]:
    return {
        "report_version": 1,
        "created_at": "2026-07-07T12:00:00Z",
        "knowledge": {
            "knowledge_version": "2026.07-m1",
            "provider": "anthropic",
            "rubric_version": "2026.07-m1",
        },
        "event": {
            "event_version": 1,
            "kind": "error",
            "surface": "cli",
            "verbatim": "error contacting bob@example.com",
            "documented_match": "evt-user-visible-error",
            "notes": "user pasted password=leaked123",
        },
        "ir": {
            "ir_version": 1,
            "unsegmented_remainder": True,
            "segments": [
                {
                    "id": "s1",
                    "kind": "task",
                    "text": "deploy with sk-ABCDEFGHIJKLMNOP1234",
                    "note": "email carol@example.com",
                }
            ],
        },
        "findings": [
            {
                "id": "f1",
                "dimension": "R2",
                "severity": "medium",
                "evidence": [{"segment": "s1", "quote": "sk-ABCDEFGHIJKLMNOP1234"}],
                "explanation": "leaks token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345",
                "fix": "rotate the key api_key=OLDSECRETVALUE",
            }
        ],
        "estimates": [
            {
                "hypothesis": "prompt contained dave@example.com",
                "confidence": "low",
                "reasoning": "saw secret=abc",
            }
        ],
        "rewrite": {
            "rewrite_version": 1,
            "gate": "passed",
            "gate_reason": None,
            "text": "redeploy using Bearer eyJhbGciOiJIUzI1",
            "changes": [
                {
                    "change": "removed token=xyz789abc",
                    "technique": "T2",
                    "rationale": "hid eve@example.com",
                }
            ],
            "notices": ["non_guarantee"],
        },
    }


def test_redact_report_scrubs_every_content_field() -> None:
    redacted = redact.redact_report(_report_with_secrets())
    blob = json.dumps(redacted)
    for secret in (
        "sk-ABCDEFGHIJKLMNOP1234",
        "bob@example.com",
        "carol@example.com",
        "dave@example.com",
        "eve@example.com",
        "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345",
        "leaked123",
        "OLDSECRETVALUE",
        "xyz789abc",
        "eyJhbGciOiJIUzI1",
        "secret=abc",
    ):
        assert secret not in blob, f"secret survived redaction: {secret}"


def test_redact_report_preserves_structure_and_does_not_mutate_input() -> None:
    original = _report_with_secrets()
    snapshot = json.dumps(original)
    redacted = redact.redact_report(original)
    # input untouched
    assert json.dumps(original) == snapshot
    # non-content fields preserved exactly
    assert redacted["report_version"] == 1
    assert redacted["findings"][0]["dimension"] == "R2"
    assert redacted["findings"][0]["evidence"][0]["segment"] == "s1"
    assert redacted["event"]["kind"] == "error"
    assert redacted["rewrite"]["notices"] == ["non_guarantee"]
    assert redacted["rewrite"]["changes"][0]["technique"] == "T2"


def test_redact_report_is_noop_on_clean_fixture() -> None:
    clean = json.loads((FIXTURES / "report-full.json").read_text(encoding="utf-8"))
    assert redact.redact_report(clean) == clean
