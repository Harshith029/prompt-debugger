# Contract invariants

The [contract schemas](../core/contracts/README.md) are restricted to a recursion-free JSON-Schema subset (so the M2 runtime validator can implement them exactly). That subset checks *shape* — types, required fields, enums, patterns — but cannot express relationships *between* fields, cross-document references, or content properties. Those are captured here as named invariants.

Each invariant records where it is enforced. "Verifier" is `src/prompt_debugger/verify.py` (M2). "Storage" is the storage layer (M2). Invariants marked with a test file are guarded by an executable test today; the rest become executable when the component they govern is implemented.

## Prompt IR

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| IR-1 | Every `segments[].text` is a **verbatim substring of its reference prompt** (see PR-1 for what "reference prompt" means in a persisted record). | Verifier (`src/prompt_debugger/verify.py`, M2 FR-2) | `tests/test_verify.py` |
| IR-2 | Segment ids are unique within an IR. | Verifier (`src/prompt_debugger/verify.py`, M2 FR-2) | `tests/test_verify.py` |

## Report JSON

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| RPT-1 | Every finding `evidence[].quote` is a verbatim substring of its reference prompt. | Verifier (`src/prompt_debugger/verify.py`, M2 FR-2) | `tests/test_verify.py` |
| RPT-2 | Every `evidence[].segment` references an existing `ir.segments[].id`, or is null. | Verifier (`src/prompt_debugger/verify.py`, M2 FR-2) | `tests/test_verify.py` |
| RPT-3 | `estimates != null` ⇒ `event != null` (estimates only accompany a reported event). | Verifier (`src/prompt_debugger/verify.py`, M2 FR-2) | `tests/test_verify.py` |
| RPT-4 | Finding ids are unique within a report. | Verifier (`src/prompt_debugger/verify.py`, M2 FR-2) | `tests/test_verify.py` |

## Rewrite Report

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| RW-1 | `gate == "declined"` ⇔ `text == null`. | Verifier (`src/prompt_debugger/verify.py`, M2 FR-2) | `tests/test_verify.py`, `tests/test_contract_invariants.py` |
| RW-2 | `text != null` ⇒ `"non_guarantee" ∈ notices` (the non-guarantee notice is mandatory whenever a rewrite is produced). | Verifier (`src/prompt_debugger/verify.py`, M2 FR-2) | `tests/test_verify.py`, `tests/test_contract_invariants.py` |
| RW-3 | `gate != "passed"` ⇒ `gate_reason != null`. | Verifier (`src/prompt_debugger/verify.py`, M2 FR-2) | `tests/test_verify.py`, `tests/test_contract_invariants.py` |

RW-1–RW-3 are enforced at runtime by the M2 verifier and also checked against fixtures (both compliant and violating) by the reference checker in `tests/test_contract_invariants.py`; the verifier is held to agree with that reference checker on the shared fixtures.

## Observable Event

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| EV-1 | `kind ∈ {unknown, none}` ⇒ `documented_match == null`. | Verifier (`src/prompt_debugger/verify.py`, M2 FR-2) | `tests/test_verify.py`, `tests/test_contract_invariants.py` |
| EV-2 | `documented_match != null` ⇒ that id exists in the active event-taxonomy version. | Verifier (`src/prompt_debugger/verify.py`, M2 FR-2; taxonomy id set supplied by the caller) | `tests/test_verify.py` |
| EV-3 | The `surface` value is a host-neutral category (`web`, `cli`, `desktop`, `api`, `other`, `unspecified`); provider-specific product names live only in provider knowledge packs. | Contract + knowledge | `tests/test_knowledge_integrity.py` |
| EV-4 | One observation matches at most one taxonomy entry: kinds are unique, API-native entries (`api_*` kinds) list exactly the `api` surface, and rendered-message entries (`refusal_message`, `model_switch`) never list it (the observation-channel selection rule, documented in the provider pack's events companion). | Knowledge | `tests/test_knowledge_integrity.py` |

## Storage / persistence

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| PR-1 | A `raw: false` history record has `prompt_raw == null` and contains no secret/PII pattern in any field, including every content-bearing field of the embedded report. In such a record, evidence quotes and IR segment text are verbatim substrings of `prompt_redacted`. | Storage (`src/prompt_debugger/store.py` `append`/`strip_raw`/`doctor`, M2 FR-5 — redacts the whole record at write time, re-verifies the substring relations post-redaction fail-closed, and `doctor` quarantines retained raw:false records that violate either clause: broken substring relations, non-null `prompt_raw`, or content that is not a fixed point of the committed redactor) | `tests/test_store.py`, `tests/test_privacy_invariants.py` |
| PR-2 | Record ids match `pd-<epoch-ms>-<uuid4[:8]>` and are time-ordered. | Storage (`src/prompt_debugger/store.py`, M2 FR-5) | `tests/test_store.py` |
| PR-3 | Fingerprints are `HMAC-SHA256` over the (redacted or raw) text with the per-store salt; store-local; excluded from default exports. | Storage (`src/prompt_debugger/store.py`, M2 FR-5) | `tests/test_store.py` |
| PR-4 | Writes are atomic (single `os.write` on an `O_APPEND` fd) under a per-store advisory lock. | Storage (`src/prompt_debugger/store.py`, M2 FR-5) | `tests/test_store.py` |
| PR-5 | The store directory and `history.jsonl` are not symlinks; all paths resolve within the store root. | Storage (`src/prompt_debugger/store.py`, M2 FR-5) | `tests/test_store.py` |
| PR-6 | `migrate` accepts every `record_version` ever shipped. | Storage (`src/prompt_debugger/store.py`, M2 FR-5) | `tests/test_store.py` |

## Prompt Tree

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| PT-1 | Every `parent_id` references an existing node; the parent graph is acyclic. | Verifier (`src/prompt_debugger/verify.py`, M2 FR-2) | `tests/test_verify.py` |
| PT-2 | Every `segment_ids` member references an existing IR segment. | Verifier (`src/prompt_debugger/verify.py`, M2 FR-2) | `tests/test_verify.py` |
| PT-3 | Every `annotations[].finding_id` references a finding in the accompanying report. | Verifier (`src/prompt_debugger/verify.py`, M2 FR-2) | `tests/test_verify.py` |

## Knowledge Engine

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| KN-1 | No provider statement (technique, event-taxonomy entry) asserts provider behavior without at least one `clm-*` claim citation. | Contract | `tests/test_knowledge_integrity.py` |
| KN-2 | An `active` technique or event-taxonomy entry must not cite a non-`verified` claim (`recorded`/`stale`/`retired`). The claim lifecycle has no `active` state; `verified` is the citable state. | Contract | `tests/test_knowledge_integrity.py` |
| KN-3 | Every event-taxonomy entry's `kind` is a member of the Observable Event contract's `kind` enum. | Contract | `tests/test_knowledge_integrity.py` |
| KN-4 | Rubric dimensions reference existing technique ids; the pattern index references existing techniques and dimensions. | Contract | `tests/test_knowledge_integrity.py` |
| KN-5 | The `common` pack is provider-neutral (no `provider`, no direct `clm-*` citations). | Contract | `tests/test_knowledge_integrity.py` |
| KN-6 | Every pattern named in a pattern index `file` field exists on disk (no dangling references). | Contract | `tests/test_knowledge_integrity.py` |
| KN-7 | Every event-taxonomy entry cites only `verified` claims (regardless of the entry's own status); claim statuses stay within the schema lifecycle (`recorded`/`verified`/`stale`/`retired`); every claim carries an https source, ISO retrieval and verification dates, and `last_verified >= retrieved`. | Contract | `tests/test_knowledge_integrity.py` |
| KN-8 | No orphaned verified claims: every `verified` claim is cited by at least one structured knowledge artifact (technique or event-taxonomy entry). | Contract | `tests/test_knowledge_integrity.py` |
| KN-9 | Pattern-library completeness and example integrity: every rubric dimension is covered by at least one pattern; index entries and on-disk bodies are bijective (no dangling references, no orphaned bodies); ids and files are unique; every body carries the full authored structure (sections + before/after example) and agrees with its index entry (id, title, dimensions, techniques); and every After demonstrates only rewrite-policy-permitted transformations — unknowable information appears as angle-bracket slots, and an After's numeric/file-like literals must already appear in its Before (the executable RG-7/RG-8 slice). | Knowledge | `tests/test_knowledge_integrity.py` |
| KN-10 | Knowledge snapshot labels agree: the manifest's `knowledge_version` covers the whole corpus snapshot, and `pack_version` (both packs), `rubric_version`, `taxonomy_version`, and the three `policy_version` fields all name that same snapshot; prose companions state the same label in their headers. | Knowledge | `tests/test_knowledge_integrity.py` |

## Policy files (common pack)

The `misuse-policy`, `rewrite-policy`, and `notices` files are declarative data (see [policy-schemas.md](design/policy-schemas.md)); these invariants hold across them.

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| PL-1 | Every policy entry carries a stable registry `id` matching its file prefix (`MISUSE-###` / `RW-###` / `NOTICE-###`); ids are unique within a file and are never reused or renumbered. | Contract + review | `tests/test_knowledge_integrity.py` (uniqueness/form); never-reused is a review rule |
| PL-2 | A misuse-policy `classes` array holds exactly the three classes `legitimate`, `ambiguous`, `prohibited`. | Contract | `tests/test_knowledge_integrity.py` |
| PL-3 | Every `notice` value (in `notices.json` and in `rewrite-policy` `notice_rules`) is a member of the Rewrite Report `notices` enum. | Contract | `tests/test_knowledge_integrity.py` |
| PL-4 | Every `rewrite-policy` `notice_rules[].notice` has fixed text defined in `notices.json`. | Contract | `tests/test_knowledge_integrity.py` |
| PL-5 | Every technique referenced by an allowed transformation exists in the techniques file; every `guarantee_ref` matches `^RG-[0-9]+$` and binds at most once. | Contract | `tests/test_knowledge_integrity.py` |
| PL-6 | `rationale` fields are maintainer documentation only; no decision (gate, classification, transformation, notice attachment) reads them. | Verifier / engine | M2 (executable once the engine exists) |
| PL-7 | Fixed user-facing wording is canonical in JSON: `notices.json` for notice texts (covering the complete Rewrite Report `notices` enum with exactly one text per notice) and `misuse-policy.json` for decline templates. The derived `.md` companions quote each fixed text verbatim, and each companion's header states the same `policy_version` as its JSON. | Contract | `tests/test_knowledge_integrity.py` |
| PL-8 | The three policy files carry one shared `policy_version`, equal to the `common` pack's snapshot label; the rewrite policy binds exactly the documented RG-1..RG-8 set; each `.md` companion carries every registry id of its JSON; policy files name no provider or product. | Contract | `tests/test_knowledge_integrity.py` |

## Composite validation

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| CV-1 | A `report` is valid only if the envelope **and** its composed `ir`, `event`, and `rewrite` sub-documents validate against their own schemas. | Validator (`src/prompt_debugger/schema.py` `validate_report`, M2 FR-1) | `tests/test_schema_validator.py`, `tests/test_composite_validation.py` (populated event + rewrite), `tests/test_privacy_invariants.py` (report + ir) |
| CV-2 | A `history-record` is valid only if the envelope validates **and** its embedded `report` validates recursively. | Validator (`src/prompt_debugger/schema.py` `validate_history_record`, M2 FR-1) | `tests/test_schema_validator.py`, `tests/test_composite_validation.py`, `tests/test_privacy_invariants.py` |

## Version compatibility

| ID | Invariant | Enforced by | Test |
|---|---|---|---|
| VC-1 | Within a contract version, changes are additive (new optional fields only). Removing a field, changing a type, tightening an enum, or making an optional field required requires a new version. | Review + CHANGELOG | — (policy) |
| VC-2 | Readers accept all prior versions of a contract still in use; persisted records are upgraded by `migrate`. | Storage / readers | M2 |
| VC-3 | Extensible enums reserve a graceful-degradation member (`unknown` for events, `other` for IR kinds) so new realities validate instead of failing. | Contract | `tests/test_contract_invariants.py` |
| VC-4 | Library `CONTRACT_VERSIONS`, the schema `const` versions, and the adapter manifest agree. | Tooling | `tests/test_contract_versions.py` |
