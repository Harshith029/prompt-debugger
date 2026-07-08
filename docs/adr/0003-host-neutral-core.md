# ADR-0003: Host-neutral core with thin adapters

- **Status:** Accepted
- **Date:** 2026-07-07

## Context

The product's first surface is a Claude Code plugin. Binding contracts, storage, and tests directly to host-specific skill files would lock the project to one host and make tests, storage, and any future surface (CLI, MCP, editor) depend on prose. A project intended to last should not be architecturally married to a single host.

## Decision

Separate the system into three layers:

1. **Core contracts** (`core/`) — versioned, host-neutral schemas, taxonomy, rubric, policy, and claim registry.
2. **Core library** (`src/prompt_debugger/`) — stdlib-only deterministic logic (storage, validation, verification, redaction, sanitization, rendering, CLI).
3. **Adapters** (`adapters/`) — thin, host-specific glue. Claude Code is one adapter. Nothing in layers 1–2 may reference a specific host.

The Plugin/Adapter API contract defines what any adapter must consume and produce.

## Alternatives considered

- **Skills as the architecture.** Rejected: unhostable elsewhere, untestable without a model, and storage semantics buried in prose.
- **Ship multiple host runtimes in v1 (also stand up CLI + MCP now).** Rejected as speculative generality (YAGNI): building adapters for hosts with no validated demand, before the primary UX is proven, is unproven complexity. The *contracts* make those adapters cheap later; that is the property worth having now.
- **Core library with a runtime dependency (e.g. pydantic) for models/validation.** Rejected in favor of stdlib-only (ADR-0006); the contract subset + a small validator keep the runtime dependency-free.

## Trade-offs

- The judgment layer (analysis, rewriting) is inherently an LLM function and cannot be made a pure library. "Host-neutral" for that layer means neutral *contracts* plus a portable methodology (the Agent Skills open standard), not a second engine. We accept that the v1 judgment runs in the Claude Code adapter.
- More directories and indirection than a single-skill layout. Justified by testability and longevity.

## Consequences

- Tests, storage, benchmarks, and future adapters bind to `core/` contracts, never to a skill file.
- Adding an adapter never edits `core/` or `src/`.
- The Claude Code adapter must vendor `core/` for self-containment (ADR-0008).
- Roadmap CLI/MCP adapters (v1.3) reuse the same contracts and library unchanged.
