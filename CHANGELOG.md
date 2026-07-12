# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).
Contract and knowledge-pack versions are tracked independently; bumps are noted here.

## [Unreleased]

### Milestone M0.1.1 — release polish
Resolves the verified findings from M0.1 review. No functional/analyzer work; no scope change.

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

### Milestone M0.1 — stabilization
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

## [0.1.0-alpha] — unreleased

First public pre-release: the **engineering foundation only**. No analyzer, rewrite, or
storage behavior is implemented yet (those arrive in Milestones M2–M4). This release
exists so the architecture, contracts, and knowledge engine can be reviewed in the open.

### Added
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

[Unreleased]: https://github.com/Harshith029/prompt-debugger/compare/v0.1.0-alpha...HEAD
[0.1.0-alpha]: https://github.com/Harshith029/prompt-debugger/releases/tag/v0.1.0-alpha
