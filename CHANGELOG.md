# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).
Contract and knowledge-pack versions are tracked independently; bumps are noted here.

## [Unreleased]

_Nothing yet._

## [0.2.0-alpha] — 2026-07-14

Second pre-release: **Milestone M1 — Knowledge Verification & Policy Authoring**, complete
and independently approved. Knowledge content and its executable integrity floor only — no
analyzer, rewrite, or storage behavior is implemented (those arrive in M2–M4). Every claim
verified against live sources; the declarative policy layer authored and frozen; taxonomy
prose completed; pattern library completed; corpus versioned as `2026.07-m1`. Milestone
record: [docs/releases/M1.md](docs/releases/M1.md).

### Close-out
- Project versions bumped `0.1.0-alpha` → `0.2.0-alpha` (`0.1.0a0` → `0.2.0a0`) across
  pyproject, the library, and the plugin/marketplace/adapter manifests.
- Milestone record `docs/releases/M1.md` created; all status pages report M0 complete,
  M1 complete, M2 not started.
- Post-FR-6 verification fixes: the composite report fixture's rewrite made
  rewrite-policy-compliant using the slot convention (it pinned the current policy snapshot
  while violating RG-7); `specs/M1.md` status metadata corrected; M1 progress statements
  made consistent across every status page; a stale architecture document-version reference
  removed from the docs index.
- Status promotion (spec FR-2) applied as its constraint (KN-2, executable); bulk promotion
  deliberately deferred to M2 — all entries remain `draft` (see the milestone record §10).

### Milestone M1 — FR-6 (version bookkeeping)

#### Changed
- **Knowledge snapshot label bumped: `2026.07-draft` → `2026.07-m1`**, reflecting the
  M1 content change from the M0 seed: the claim registry fully verified and extended
  (FR-1, FR-4, FR-4.1: 12 claims, all `verified`), the authored policy layer
  (FR-3/3.1/3.2: misuse policy, rewrite policy, notices), the completed taxonomy
  prose (FR-4/4.1), and the completed pattern library (FR-5/5.1). Bumped coordinately
  in every authoritative field — `manifest.json` `knowledge_version`, both packs'
  `pack_version`, `rubric_version`, `taxonomy_version`, and the three
  `policy_version` fields — plus the six prose-companion headers, per the
  label-alignment rule (never desync a file's label from its pack snapshot). Test
  fixtures and the architecture example were aligned to the same label. The `-m1`
  tag is kept (rather than a bare `2026.07`) because per-entry `status` promotion is
  a separate, not-yet-performed pass; the label names the milestone content
  snapshot, not entry maturity.

#### Added
- **Invariant KN-10 with an executable test:** all knowledge snapshot labels —
  manifest, both packs, rubric, taxonomy, and the three policy files — must name one
  corpus snapshot, and the prose companions must state the same label in their
  headers. Label desynchronization now fails CI instead of relying on discipline.

### Milestone M1 — FR-5.1 (rewrite correctness in pattern examples)

Content correction only: the pattern library's own examples now satisfy the rewrite
guarantees they demonstrate. No contract, schema, policy, or architecture change.

#### Fixed
- **Fabricated content removed from every After example (RG-7/RG-8).** The After
  examples invented information absent from their Before — dates, metrics, thresholds,
  audiences, priorities, technologies, API details, domain facts (e.g. an invented
  "p95 / 2026-07-10 / June baseline / 10%" resolution; an invented audience "a new
  backend engineer joining next week"; an invented tech stack "Python 3.10, stdlib
  only, dedupe by email"; an invented example table row "Pagination offset/cursor").
  Information the user holds but the prompt lacks is now expressed as explicit
  angle-bracket slots (`<what the user would supply>`) or an explicit question —
  the convention is documented in `patterns/README.md`.
- **Intent preserved exactly (RG-1/RG-2).** "every function" → "every public
  function" (narrowing) corrected; tentative asides ("should probably", "might as
  well") are no longer silently promoted to firm requirements — they become explicit
  scope questions; an added "quote the log lines" instruction absent from the Before
  was removed; conflicting requirements are surfaced for the user's priority rather
  than resolved by invented context; "Prompt 1/2" labels replaced with "First/Second
  prompt" (no literals absent from the Before).
- Documentation kept strong, examples corrected to match it (not vice versa):
  `patterns/README.md` now states the After-content rule and the slot convention;
  KN-9 extended accordingly.

#### Added
- **Executable enforcement of the objective RG-7/RG-8 slice:** a new integrity test
  extracts each Before/After pair and rejects any After whose numeric literals or
  dotted (file-like) tokens do not appear in its Before, after excluding
  angle-bracket slots/tags and numbered-list markers. No heuristic quality judgment
  — only objectively checkable fabrication.

### Milestone M1 — FR-5 (pattern completion)

Knowledge content and its executable integrity floor; no runtime code, no contract changes.

#### Added
- **Seven new patterns**, completing the library to one per rubric dimension R1–R10
  (the analyzer's finding surface — the documented completeness definition in
  `patterns/README.md`): `pat-resolve-ambiguity` (R1/T1),
  `pat-reconcile-contradictions` (R3/T1), `pat-surface-real-scope` (R4/T8+T9),
  `pat-separate-instructions-from-data` (R6/T4+T6), `pat-state-goals-not-steps`
  (R7/T10), `pat-state-definition-of-done` (R8/T9), `pat-state-constraints` (R9/T9+T7).
  Every body is a complete before/after example whose After makes existing intent
  explicit — never fabricated context — per the rewrite policy. All `draft` pending
  the status-promotion pass.
- **Invariant KN-9 with four executable tests:** rubric-dimension coverage is total;
  index and on-disk bodies are bijective (no orphaned bodies); pattern ids and files
  are unique; every body carries the full authored structure and agrees with its
  index entry (id, title, dimensions, techniques) — so a stub or drifted body cannot
  pass CI.

#### Fixed
- The three original pattern bodies said "rewrite-contract compliant"; the artifact
  has been named the **rewrite policy** since FR-3 — wording corrected. The library
  README now documents the completeness definition, the authoring rules against the
  real policy file, and why T5 has no dedicated pattern (no rubric dimension maps
  to it).

### Milestone M1 — FR-4.2 (formatter determinism and claim-graph closure)

Resolves the verified findings of the second independent FR-4 review.

#### Fixed
- **Formatter gate non-determinism (P0), root cause found and reproduced:**
  `requirements-dev.txt` pinned `ruff>=0.5` — a floating lower bound. Ruff's formatter
  style evolves between versions (the assert-message wrapping style changed: older ruff
  parenthesizes the asserted condition, newer ruff parenthesizes the message), so two
  environments that both satisfy the declared range disagree on the same tree. Reproduced
  concretely: ruff 0.15.20 and 0.15.21 pass on this tree with exit 0 and an empty `--diff`;
  ruff 0.5.0 — fully conforming to the old bound — fails it (`tests/test_frontmatter.py`,
  `tests/test_knowledge_integrity.py` would be reformatted). Line endings were ruled out
  (`git ls-files --eol`: uniformly LF). The discrepancy between the FR-4.1 report and the
  independent verification was therefore **repository-caused**: both environments were
  self-consistent; the repo failed to make the gate reproducible. Fix: ruff is pinned
  exactly (`ruff==0.15.21`), the tree verifies clean under the pin, and version bumps are
  documented as deliberate pin-update-plus-reformat changes. The FR-4.1 "does not
  reproduce" record is superseded accordingly.
- **Orphaned cookbook claim (P1):** `clm-cookbook-fallback-billing` was verified but cited
  by no structured artifact. Integrated with real provenance: `evt-api-refusal-stop-reason`
  now documents the `fallback_credit_token` that `stop_details` may carry on a blocked
  request with a billable cached prefix (a user-visible response field), citing the claim.

#### Added
- **Executable orphan detection (P1), invariant KN-8:** the suite fails if any `verified`
  claim is cited by no technique or event-taxonomy entry, so the claim graph cannot
  silently accumulate dead verified claims that quarterly re-verification would maintain
  for nothing.

### Milestone M1 — FR-4.1 (taxonomy accuracy stabilization)

Resolves the verified findings of the independent FR-4 review. Knowledge content, tests,
and documentation truthfulness only; the frozen policy layer is untouched.

#### Fixed
- **Consumer-surface fallback overstatement (P0):** the taxonomy generalized a page-scoped
  verified negative into "consumer-surface fallback is not publicly documented" — falsified
  by the FR-4.1 survey of official sources. Product-specific documentation does cover it:
  the Claude Code docs document automatic model fallback with a visible transcript notice
  (new claim `clm-claude-code-fallback`), and the Claude Help Center documents the consumer
  apps' automatic switching, notice, and model label (new claim `clm-webapp-switch-notice`);
  the official Cookbook fallback/billing guide is captured as `clm-cookbook-fallback-billing`
  (developer-surface scope, per-platform availability). `clm-consumer-surface-fallback` is
  revised to exactly its evidence — the platform page's coverage — with explicit pointers to
  where product behavior IS documented. The model-switch taxonomy entry and the events
  companion now distinguish scopes per surface and never borrow one surface's documentation
  for another. Re-verification against the updated platform page (2026-07-14) also extended
  `clm-fallback-block` (usage.iterations; sticky routing serves fallback turns with no block)
  and `clm-refusal-stop-reason` (explanation not stable; batch results may carry null
  stop_details on a refusal).
- **Claim lifecycle drift (P1):** the KN-2 test compared entries against a nonexistent
  `active` claim status (the lifecycle is `recorded`/`verified`/`stale`/`retired`) and could
  never enforce the invariant. The test now treats `verified` as the citable state; KN-2's
  wording is corrected in the invariants catalogue, the knowledge contract, the contracts
  README, the policy-architecture design, and the policy-review process doc.
- **Event boundary ambiguity (P1):** `evt-refusal-visible` (surfaces included `api`) and
  `evt-api-refusal-stop-reason` could both match one observation. Resolved with the
  documented **observation-channel rule** (events companion): raw API response fields →
  `api_*` entries (surfaces exactly `["api"]`); rendered product-surface messages →
  `refusal_message`/`model_switch` (never `api`). Surface sets of paired entries are now
  disjoint; recorded as invariant EV-4 and enforced by tests.
- **Repository truthfulness (P1):** README (status banner, project status, roadmap table,
  ADR count now nine), docs/ROADMAP.md, docs/ARCHITECTURE.md (§2 facts updated to verified
  status with the corrected error-code list and the truncation/stop-reason distinction;
  §15 source list extended), and core/knowledge/README.md (status section reflects M1
  progress) now describe the repository as it exists today.

#### Added
- **Verified-claim integrity (P1), invariant KN-7 with executable tests:** every taxonomy
  entry cites only `verified` claims regardless of its own status; claim statuses stay
  within the schema lifecycle; every claim has an https source, ISO dates, and
  `last_verified >= retrieved`. Plus EV-4 tests: unique kinds and disjoint
  observation-channel surfaces.

#### Verified
- **`ruff format --check` (P0):** did not reproduce under ruff 0.15.20 (exit 0, zero-diff,
  all 23 tracked Python files in scope). **Superseded by FR-4.2**, which found the real root
  cause: the formatter version was unpinned, so the verdict was version-dependent — this
  check was correct for one environment, not for the gate.

### Milestone M1 — FR-4 (taxonomy prose)

Knowledge content only (per the M1 spec: no runtime code, no contract changes).

#### Added
- **`clm-stop-reasons`** (verified 2026-07-14 against the live handling-stop-reasons page):
  all seven documented `stop_reason` values with their meanings and follow-ups. Resolves the
  FR-1 deferral recorded in `clm-api-errors` (2026-07-12 fetch limit).
- **ADR-0009:** truncation observables (`max_tokens`, `model_context_window_exceeded`) are
  claim-backed but get no taxonomy kind while the v1 event contract is frozen; they flow
  through the `unknown`-kind honesty path until M2's contract review revisits the enum.
- Events prose companion: a "two families of *something stopped*" section separating HTTP
  errors from stop conditions, so analysis-layer adapters cannot conflate them.
- Three taxonomy integrity tests: prose completeness (`api_correlate` null only for
  `evt-none`), KN-1 made executable for events (non-`none` entries cite ≥1 claim), and
  inline `clm-*` mentions in prose must resolve to the registry *and* be cited in that
  entry's `source_claims`.

#### Changed
- **Taxonomy prose completed for all six entries** (`core/knowledge/packs/anthropic/events.json`),
  reflecting FR-1 verification outcomes: refusal entries state the HTTP-200 (not error)
  framing, documented `stop_details` categories, and the no-rephrasing-guarantee boundary;
  the model-switch entry replaces its stale "until clm-consumer-surface-fallback is
  verified" wording with the verified-negative outcome (consumer-surface mechanism is
  undocumented — user observation, never asserted mechanism); the error entry's boundary
  now cites `clm-stop-reasons` to separate truncation from HTTP errors; `evt-none` states
  that no estimates layer may attach. Statuses remain `draft` (promotion is FR-2).
- `clm-api-errors` notes updated: the stop-reasons deferral is resolved.

### Milestone M1 — FR-3.2 (policy consistency polish)

Resolves the minor consistency findings of the FR-3.1 review. No schema, semantic, or
functional change.

#### Fixed
- **Decline-template source of truth (Issue 1):** aligned with the notices philosophy —
  `misuse-policy.json` is canonical for decline wording; `misuse-policy.md` now declares
  itself derived and quotes both templates verbatim (it previously said the wording was
  "fixed here"), with a drift test. Invariant PL-7 generalized to cover all fixed
  user-facing wording (notice texts + decline templates).
- **Documentation consistency (Issue 2):** the artifact table in
  `docs/design/policy-architecture.md` no longer links `.json` labels to `.md` files —
  every label now links to the file it names, schemas link to their actual schema files,
  data and companions are separate rows, and the invariants row reads PL-1..PL-8.

#### Added
- **Companion parity tests (Issue 3):** decline-template quotes in `misuse-policy.md`
  must match `misuse-policy.json` byte-for-byte, and each companion's header must state
  the same `policy_version` as its JSON (both relationships were already documented).

### Milestone M1 — FR-3.1 (policy layer stabilization)

Resolves the verified findings of the independent FR-3 review. No redesign, no new features.

#### Fixed
- **Report version pinning (Issue 1):** the Report JSON contract can now represent the
  documented `policy_version` pinning — `report.knowledge.policy_version` added as an
  optional, nullable field (additive within Report v1 per its compatibility rule). Contract
  prose, the knowledge contract, and `docs/COMPATIBILITY.md` now agree; the composite
  fixture exercises the populated field, the history-record fixtures the absent one.
- **Single source of truth for notices (Issue 2):** `notices.json` is authoritative for
  notice wording; `notices.md` is explicitly derived, quotes each text verbatim, and an
  integrity test fails on any drift. The Rewrite Report contract's pointer corrected from
  `notices.md` to `notices.json`.
- **Architecture documentation drift (Issue 3):** `docs/design/policy-architecture.md`
  updated to the implemented state — status header, §4.2 note that the procedure is data
  as an ordered prose checklist (dispatch lives in analyzer code), §6 rewritten to defer to
  `policy-schemas.md` and the real artifacts (the superseded `on_yes`/`on_no` field sketch
  and the resolved Option-A/B decision box removed), closing section reflects FR-3 completion.
- **Provider-name leak:** `rewrite-policy.md` referred to "the Anthropic techniques file";
  now provider-neutral ("the active provider pack's techniques file"), per KN-5 and the
  governance neutrality rule — enforced by a new test.

#### Added
- **Integrity coverage (Issue 4):** seven new tests — RG binding equals the documented
  RG-1..RG-8 set; the notices file covers the complete Rewrite Report enum exactly once;
  `policy_version` aligns across the three files and their pack snapshot; every registry id
  appears in its `.md` companion; `notices.md` quotes match `notices.json` byte-for-byte;
  no provider names in policy files; the `policy_version` pattern is shared and
  calendar-valid. Recorded as invariants PL-7/PL-8.
- **Version validation (Issue 5):** the `policy_version` pattern in all three policy schemas
  now rejects calendar-impossible months (`00`, `13`–`99`). Formally a pattern-tightening,
  taken in-version under the alpha pre-release rule because no valid instance existed in the
  rejected space; the exception is recorded in `docs/design/policy-schemas.md`.

### Milestone M1 — FR-3 (policy authoring)

Adds the provider-neutral policy layer as declarative data, per
[docs/design/policy-schemas.md](docs/design/policy-schemas.md). No analyzer, rewrite, or
storage behavior is implemented (that remains M2–M4); the policy files are inert data the
future engine will interpret.

#### Added
- Three additive knowledge schemas under `core/contracts/knowledge/`: `misuse-policy.schema.json`,
  `rewrite-policy.schema.json`, `notices.schema.json`. Recursion-free subset, `additionalProperties:
  false` on every object; purely declarative (closed enums and prose only — no branching fields,
  expressions, or embedded logic).
- Three `common`-pack policy files plus Markdown companions: `misuse-policy.json`/`.md`
  (legitimacy classification: three classes, the neutral ordered procedure, the ask-don't-guess
  elicitation rule, fixed decline templates), `rewrite-policy.json`/`.md` (allowed and prohibited
  transformations, the RG-1..RG-8 guarantees with hard/judged mode, notice-attachment rules), and
  `notices.json`/`.md` (fixed notice texts keyed to the Rewrite Report `notices` enum).
- Every policy entry carries a **stable, permanent registry id** (`MISUSE-###` / `RW-###` /
  `NOTICE-###`), never reused, distinct from any closed semantic role (`class`, `notice`,
  `guarantee_ref`).
- Every policy entry carries a maintainer-facing `rationale`, documented and schema-annotated as
  **documentation only — not read at runtime**.
- Policy invariants PL-1..PL-6 in `docs/CONTRACT-INVARIANTS.md`, and integrity tests in
  `tests/test_knowledge_integrity.py` (id uniqueness/form; three complete classes; `notice`
  values ⊆ Rewrite Report enum; notice rules resolve to notice texts; technique references and
  `guarantee_ref`s well-formed; provider-neutrality of the new files).
- [docs/process/policy-review.md](docs/process/policy-review.md) — maintainer governance for
  policy evolution: contribution workflow, review and evidence expectations, compatibility and
  versioning rules, schema evolution discipline, rationale standards, regression requirements,
  and the approval process. Documentation only; no runtime effect.

#### Changed
- Policy files use **`schema_version`** (format axis) alongside **`policy_version`** (content
  axis) to keep schema evolution and policy evolution independent; the knowledge contract records
  the divergence from the older `file_version` spelling.
- `core/knowledge/packs/common/pack.json` description updated to present-tense (the policy files
  now exist); the pack stays on the `2026.07-draft` snapshot.
- `tools/validate_schemas.py` validates the three new policy files against their schemas;
  `core/contracts/knowledge/CONTRACT.md` lists them in the structure tree.

## [0.1.0-alpha] — 2026-07-12

First public pre-release: the **engineering foundation**. No analyzer, rewrite, or storage
behavior is implemented yet (those arrive in Milestones M2–M4). This tag bundles the M0
foundation with the M0.1 and M0.1.1 stabilization passes so the architecture, contracts, and
knowledge engine can be reviewed in the open. Milestone record: [docs/releases/M0.md](docs/releases/M0.md).

### Stabilization — M0.1.1 (release polish)
Resolves the verified findings from independent review. No functional/analyzer work; no scope change.

#### Fixed
- **Architecture accuracy:** the architecture document no longer describes M2 library modules
  (`store`/`schema`/`verify`/`redact`/`sanitize`/`render`/`cli`) in the present tense, and no
  longer references files that do not exist (`core/sources/claims.yaml`, a flat `core/schemas/`,
  `core/guides/`, `INSTALL.md`/`SECURITY-REVIEW.md`). §5 now shows the actual current tree with
  a separate "planned additions" list; the claim registry is correctly located at
  `core/knowledge/packs/anthropic/claims.json`; M2/M5 components are labelled as future work.
- **Pattern library integrity:** the three patterns named in the Anthropic pattern index now
  have authored markdown bodies (Option A); a new integrity test asserts every indexed pattern
  file exists, so there can be no dangling reference.
- **Release gate parity:** the release workflow now runs `check_versions.py` (version
  consistency) as part of a gate identical to PR CI, then additionally verifies the plugin,
  marketplace, and adapter-manifest versions against the git tag. The release gate is no longer
  weaker than the PR gate. `check_release_version.py`'s docstring corrected to reflect that it
  already validates the adapter manifest.

#### Added
- Concrete composite-validation fixtures and `tests/test_composite_validation.py`: a Report JSON
  with populated `event` and `rewrite` sub-documents, validated through the full composite chain
  (report → ir → event → rewrite, and embedded in a history record), plus a case proving a
  schema-valid-but-invariant-violating rewrite is caught by the reference checker.
- Invariants KN-6 (pattern files exist) and refreshed CV-1/CV-2 test references in
  `docs/CONTRACT-INVARIANTS.md`.

### Stabilization — M0.1
Correctness, consistency, and privacy-safety of the M0 foundation. No functional/analyzer
work; no scope change.

#### Fixed
- **Privacy (PR-1):** persisted history records embedded the full Report JSON, whose IR
  segment text and evidence quotes carry verbatim prompt substrings — so a secret scrubbed
  from `prompt_redacted` could survive in the embedded report. The storage contract now
  requires redaction of the **entire record** for a `raw: false` save, the `raw` flag's
  semantics were clarified to govern the whole record, and the invariant is guarded by an
  executable test (`tests/test_privacy_invariants.py`) with compliant and leak fixtures.

#### Changed
- **Host-neutral core:** the Observable Event contract's `surface` enum no longer encodes
  provider product names (`claude_ai`, `claude_code`). It now uses host-neutral categories
  (`web`, `cli`, `desktop`, `api`, `other`, `unspecified`); the Anthropic pack maps its
  product surfaces onto them. (Pre-release interface change, permitted under alpha.)
- Documentation synchronized with implementation: the architecture repository tree is
  labelled as the target layout, and the performance section marks the benchmark store
  generators as M2 work rather than present.
- Report and Prompt IR contracts clarify that the verbatim-substring rule references the
  redacted prompt inside a persisted `raw: false` record.

#### Added
- `docs/CONTRACT-INVARIANTS.md` — the catalogue of invariants the schema subset cannot
  express, each with its enforcement point and test.
- `tests/test_contract_invariants.py` and `tests/test_privacy_invariants.py` — executable
  enforcement of the rewrite-report, observable-event, and persisted-redaction invariants.
- `tools/check_versions.py` — verifies all version-bearing files agree; wired into CI and
  the local gate. `tools/check_release_version.py` now also checks the adapter manifest.
- Strengthened knowledge-integrity tests: provider-neutral surface enum, taxonomy surface
  categories, and the active-cites-active claim-provenance rule.

### Foundation — M0

- **Repository foundation** separating host-neutral core, adapters, contracts, knowledge,
  benchmarks, evals, tests, tooling, docs, and CI.
- **Versioned contracts (v1):** Prompt IR, Report JSON, Rewrite Report, Observable Event,
  Storage (history record + config), Knowledge Engine file formats, Plugin/Adapter API,
  Prompt Tree — each a JSON schema (restricted, recursion-free subset) plus a prose contract.
- **Knowledge Engine:** versioned data packs — a provider-neutral `common` rubric pack
  (R1–R10) and an `anthropic` provider pack (dated claim registry, techniques T1–T10,
  observable-event taxonomy, pattern-library index). Seed content is `draft`/`recorded`,
  pending the M1 verification pass.
- **Claude Code adapter** scaffold: plugin and marketplace manifests, adapter manifest,
  four skill skeletons (`analyze`, `rewrite`, `history`, `pd`) with a corrected
  tool-permission model, and a CI-verified vendored copy of `core/`.
- **Benchmark corpus** across nine categories with a schema-validated runner, wired into CI.
- **Semantic-evaluation protocols** (meaning preservation, red-team rewrite, rubric
  calibration) as documented stubs for the release gate.
- **Tooling:** schema/subset validation, AST import-policy check, relative-link check,
  plugin vendor sync, and release-version verification.
- **Documentation:** architecture, eight ADRs, data flow, glossary, threat model, privacy
  model, roadmap, compatibility policy, ethics/use policy, and the Prompt Tree design.
- **CI/CD:** three-OS × two-Python matrix gate; release workflow skeleton with checksums
  and build-provenance attestations.

### Security & privacy
- Shipped code performs no runtime network I/O — enforced by an AST import allowlist and a
  socket-blocking test harness, not by convention.
- Storage defaults to user-local; project-local storage is explicit opt-in and self-ignoring.

### Notes
- This is `alpha`: interfaces may still change before `v1.0.0`. Every such change will be
  recorded here.

[Unreleased]: https://github.com/Harshith029/prompt-debugger/compare/v0.2.0-alpha...HEAD
[0.2.0-alpha]: https://github.com/Harshith029/prompt-debugger/releases/tag/v0.2.0-alpha
[0.1.0-alpha]: https://github.com/Harshith029/prompt-debugger/releases/tag/v0.1.0-alpha
