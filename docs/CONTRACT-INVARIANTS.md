# Contract invariants

The [contract schemas](../core/contracts/README.md) are restricted to a recursion-free JSON-Schema subset (so the M2 runtime validator can implement them exactly). That subset checks *shape* — types, required fields, enums, patterns — but cannot express relationships *between* fields, cross-document references, or content properties. Those are captured here as named invariants.

Each invariant records where it is enforced. "Verifier" is `src/prompt_debugger/verify.py` (M2). "Storage" is the storage layer (M2). Invariants marked with a test file are guarded by an executable test today; the rest become executable when the component they govern is implemented.

## Prompt IR

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| IR-1 | Every `segments[].text` is a **verbatim substring of its reference prompt** (see PR-1 for what "reference prompt" means in a persisted record). | Verifier | M2 |
| IR-2 | Segment ids are unique within an IR. | Verifier | M2 |

## Report JSON

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| RPT-1 | Every finding `evidence[].quote` is a verbatim substring of its reference prompt. | Verifier | M2 |
| RPT-2 | Every `evidence[].segment` references an existing `ir.segments[].id`, or is null. | Verifier | M2 |
| RPT-3 | `estimates != null` ⇒ `event != null` (estimates only accompany a reported event). | Verifier | M2 |
| RPT-4 | Finding ids are unique within a report. | Verifier | M2 |

## Rewrite Report

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| RW-1 | `gate == "declined"` ⇔ `text == null`. | Verifier | `tests/test_contract_invariants.py` |
| RW-2 | `text != null` ⇒ `"non_guarantee" ∈ notices` (the non-guarantee notice is mandatory whenever a rewrite is produced). | Verifier | `tests/test_contract_invariants.py` |
| RW-3 | `gate != "passed"` ⇒ `gate_reason != null`. | Verifier | `tests/test_contract_invariants.py` |

RW-1–RW-3 are checked against fixtures now (both compliant and violating) so the rule is executable ahead of the M2 verifier.

## Observable Event

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| EV-1 | `kind ∈ {unknown, none}` ⇒ `documented_match == null`. | Verifier | `tests/test_contract_invariants.py` |
| EV-2 | `documented_match != null` ⇒ that id exists in the active event-taxonomy version. | Verifier | M2 (needs the loaded taxonomy) |
| EV-3 | The `surface` value is a host-neutral category (`web`, `cli`, `desktop`, `api`, `other`, `unspecified`); provider-specific product names live only in provider knowledge packs. | Contract + knowledge | `tests/test_knowledge_integrity.py` |

## Storage / persistence

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| PR-1 | A `raw: false` history record has `prompt_raw == null` and contains no secret/PII pattern in any field, including every content-bearing field of the embedded report. In such a record, evidence quotes and IR segment text are verbatim substrings of `prompt_redacted`. | Storage (redacts the whole record at write time) | `tests/test_privacy_invariants.py` |
| PR-2 | Record ids match `pd-<epoch-ms>-<uuid4[:8]>` and are time-ordered. | Storage | M2 |
| PR-3 | Fingerprints are `HMAC-SHA256` over the (redacted or raw) text with the per-store salt; store-local; excluded from default exports. | Storage | M2 |
| PR-4 | Writes are atomic (single `os.write` on an `O_APPEND` fd) under a per-store advisory lock. | Storage | M2 |
| PR-5 | The store directory and `history.jsonl` are not symlinks; all paths resolve within the store root. | Storage | M2 |
| PR-6 | `migrate` accepts every `record_version` ever shipped. | Storage | M2 |

## Prompt Tree

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| PT-1 | Every `parent_id` references an existing node; the parent graph is acyclic. | Verifier | M2 |
| PT-2 | Every `segment_ids` member references an existing IR segment. | Verifier | M2 |
| PT-3 | Every `annotations[].finding_id` references a finding in the accompanying report. | Verifier | M2 |

## Knowledge Engine

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| KN-1 | No provider statement (technique, event-taxonomy entry) asserts provider behavior without at least one `clm-*` claim citation. | Contract | `tests/test_knowledge_integrity.py` |
| KN-2 | An `active` technique or event-taxonomy entry must not cite a non-`active` claim (`stale`/`retired`/`recorded`). | Contract | `tests/test_knowledge_integrity.py` |
| KN-3 | Every event-taxonomy entry's `kind` is a member of the Observable Event contract's `kind` enum. | Contract | `tests/test_knowledge_integrity.py` |
| KN-4 | Rubric dimensions reference existing technique ids; the pattern index references existing techniques and dimensions. | Contract | `tests/test_knowledge_integrity.py` |
| KN-5 | The `common` pack is provider-neutral (no `provider`, no direct `clm-*` citations). | Contract | `tests/test_knowledge_integrity.py` |
| KN-6 | Every pattern named in a pattern index `file` field exists on disk (no dangling references). | Contract | `tests/test_knowledge_integrity.py` |

## Composite validation

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| CV-1 | A `report` is valid only if the envelope **and** its composed `ir`, `event`, and `rewrite` sub-documents validate against their own schemas. | Validator | `tests/test_composite_validation.py` (populated event + rewrite), `tests/test_privacy_invariants.py` (report + ir) |
| CV-2 | A `history-record` is valid only if the envelope validates **and** its embedded `report` validates recursively. | Validator | `tests/test_composite_validation.py`, `tests/test_privacy_invariants.py` |

## Version compatibility

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| VC-1 | Within a contract version, changes are additive (new optional fields only). Removing a field, changing a type, tightening an enum, or making an optional field required requires a new version. | Review + CHANGELOG | — (policy) |
| VC-2 | Readers accept all prior versions of a contract still in use; persisted records are upgraded by `migrate`. | Storage / readers | M2 |
| VC-3 | Extensible enums reserve a graceful-degradation member (`unknown` for events, `other` for IR kinds) so new realities validate instead of failing. | Contract | `tests/test_contract_invariants.py` |
| VC-4 | Library `CONTRACT_VERSIONS`, the schema `const` versions, and the adapter manifest agree. | Tooling | `tests/test_contract_versions.py` |
