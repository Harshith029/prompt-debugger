# Contract: Storage (v1)

**Purpose.** The persistence layer's public API and on-disk formats. Adapters never touch files directly; they invoke the library CLI (`prompt_debugger.cli`, M2), which is the only writer.

## On-disk layout

```
~/.prompt-debugger/
├── config.json                      # config.schema.json
└── stores/<project-key>/            # project-key = slug + short HMAC of project path
    ├── salt                         # 32 random bytes, created at store init (0600 where supported)
    ├── history.jsonl                # one History Record per line (history-record.schema.json)
    ├── history.rejects.jsonl        # quarantined lines from doctor
    └── archive/history-<date>.jsonl # rotated files
```

Project-local opt-in (`storage_scope: project` **and** `project_local_acknowledged: true`) relocates the store to `<project>/.prompt-debugger/`, which is created **self-ignoring**: the store directory contains a `.gitignore` with `*` plus a warning README. (ADR-0004.)

## Operations (the storage API)

| Operation | Semantics |
|---|---|
| `append` | Validate (schema + composite + verifier invariants) → **redact the whole record** → fingerprint → single atomic write under the store lock. Refuses unvalidated payloads. For a default (`raw: false`) save, redaction is applied to **every free-text field of the record, not just the top-level prompt** — including the embedded report's IR segment text, finding evidence quotes, event verbatim, and rewrite text/changes. This closes the leak where a secret scrubbed from `prompt_redacted` could otherwise survive in an unredacted copy inside the embedded report (invariant PR-1). A `raw: true` save is written only after explicit per-save confirmation and stores unredacted content throughout. |
| `list` | Records in id order; raw records visibly flagged. |
| `get <id>` | One record. All read paths schema-validate and sanitize records before display (records are untrusted input). |
| `compare <a> <b>` | Rubric-score delta + unified diff of redacted prompts. |
| `trends` | Per-dimension finding counts over time. |
| `export <fmt>` | Markdown/CSV/JSON. **Redacted and fingerprint-free by default**; including raw requires an explicit flag that prints a warning. CSV output formula-escapes cells. |
| `delete <id>` / `purge` | User-owned data must be destroyable. |
| `strip-raw <id>` | Convert a raw record to redacted in place (reversibility of the loud raw opt-in). |
| `doctor` | Validate every line; quarantine invalid/corrupt lines to `history.rejects.jsonl` with reasons. |
| `migrate` | Upgrade records to the current `record_version`; timestamped backup first. |
| `archive` | Rotate `history.jsonl` into `archive/`. |

## Integrity rules

- **Redaction (invariant PR-1):** a `raw: false` record is fully redacted. `prompt_raw` is null, and no secret or PII pattern survives in any field of the record — including every content-bearing field of the embedded report (IR segment text, finding evidence quotes, event verbatim, rewrite text and change descriptions). In a `raw: false` record, evidence quotes and IR segment text are verbatim substrings of `prompt_redacted`, not of the original prompt. This invariant is not expressible in the schema subset; it is enforced by the storage layer at write time and guarded by an executable test (`tests/test_privacy_invariants.py`). See [docs/CONTRACT-INVARIANTS.md](../../../docs/CONTRACT-INVARIANTS.md).
- **Locking:** advisory lock file per store (`fcntl` on POSIX, `msvcrt.locking` on Windows) around all writes.
- **Atomic appends:** one serialized record = one `os.write` on an `O_APPEND` descriptor; readers tolerate and report a trailing partial line.
- **Ids:** `pd-<epoch-ms>-<uuid4[:8]>` — time-ordered without a dependency (UUIDv7 is not in the 3.10 stdlib).
- **Fingerprints:** HMAC-SHA256 with the per-store salt; store-local only (dictionary-attack resistance; see threat model).
- **Symlink refusal:** the store directory and `history.jsonl` must not be symlinks; paths are resolved and containment-checked against the store root.

## Compatibility

`record_version` governs record shape; `migrate` must accept every version ever shipped. Config unknown keys are rejected (additionalProperties: false) — new options require a config version bump or an optional-field addition noted in CHANGELOG.
