# Roadmap

Each milestone is validated against a fixed engineering review checklist; no milestone closes with open accepted findings. Full detail: [ARCHITECTURE.md](ARCHITECTURE.md) §12.

## Milestones to v1.0

| M | Focus | State |
|---|---|---|
| **M0** | Engineering foundation: repo, contracts, schemas, Knowledge Engine structure, benchmarks, tooling, tests, ADRs, docs, CI | **complete (this milestone)** |
| M1 | Knowledge verification pass: verify every claim against its live source, promote to active, author misuse policy + rewrite contract + notices, expand taxonomy prose, populate pattern library, resolve the consumer-surface fallback claim | next |
| M2 | Core library: storage (locking, atomic append, doctor, migrate, archive), schema-subset validator, evidence verifier, redaction, sanitization, rendering, CLI + benchmarks | |
| M3 | `analyze` + `rewrite` skills; trigger evals; adversarial, injection, meaning-preservation, and rubric-calibration suites | |
| M4 | `history` skill wiring; privacy verifications (raw UX, export redaction, permission profile) | |
| M5 | Docs completion, examples, packaging, release-trust pipeline (checksums + attestations); 3-OS install tests | |
| M6 | Final security/privacy review; v1.0.0 | |

## Post-v1

- **v1.1** — Prompt Tree renderer (local HTML), trends visualization, config UX polish.
- **v1.2** — Prompt-template library per task family (coding, research, writing) as additional knowledge content.
- **v1.3** — MCP server adapter and/or standalone CLI adapter, binding to the same core contracts and library.
- **Deferred** — Browser extension, only if an official client API exposes observable events (ADR-0005), with its own security/privacy review.

## Continuous

- Quarterly claim-registry re-verification (issue template + checklist) keeps the taxonomy honest as provider documentation changes.
- Knowledge-pack and contract version bumps are logged in [CHANGELOG.md](../CHANGELOG.md).
