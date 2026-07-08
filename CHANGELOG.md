# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).
Contract and knowledge-pack versions are tracked independently; bumps are noted here.

## [Unreleased]

_Nothing yet._

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
