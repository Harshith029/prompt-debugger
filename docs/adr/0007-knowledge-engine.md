# ADR-0007: Knowledge Engine of versioned data packs

- **Status:** Accepted
- **Date:** 2026-07-07

## Context

The tool's guidance — the quality rubric, prompt-engineering techniques, the observable-event taxonomy, and the factual claims about provider behavior — must be accurate, auditable, and updatable as provider documentation evolves. If this knowledge is embedded in analyzer code or skill prose, it cannot be versioned independently, cannot be audited to sources, and cannot be extended to new providers without code changes. The review also required (F6) versioned sources with retrieval dates and graceful handling of undocumented events.

## Decision

Introduce a **Knowledge Engine**: versioned **data packs** (`core/knowledge/`) that hold all prompt-engineering knowledge as validated data, separate from implementation. A `common` pack holds provider-neutral methodology (rubric, misuse policy, notices); provider packs (starting with `anthropic`) hold a **claim registry** (dated, sourced statements), techniques, an event taxonomy, and a pattern library. Every provider statement carries a claim id; every claim carries a URL, retrieval date, and verification status. Analyzers and adapters **query** packs; they never hardcode guidance.

## Alternatives considered

- **Hardcode rules in analyzer code / skill prose.** Rejected: unversioned, unauditable, not extensible, and it entangles "what is true about the provider" with "how we analyze."
- **A rules DSL / expert system.** Rejected as over-engineered: the knowledge is descriptive (definitions, techniques, facts), not a rules engine; JSON data + prose companions suffice.
- **YAML packs.** Rejected: YAML parsing is not in the stdlib (ADR-0006). Packs are JSON with Markdown companions.

## Trade-offs

- Indirection: guidance lives in data, not in the code that uses it. Justified by auditability and the provenance chain (observation → taxonomy → claim → URL).
- Requires discipline: CI warns when active entries cite non-active claims, and a quarterly re-verification process keeps claims current.

## Consequences

- Every explanation the tool gives is traceable to a dated public source.
- Provider documentation changes become pack version bumps, not code changes.
- A new provider is a new pack directory — no edits to `common` or to code.
- The `unknown` event kind (contract-mandated) ensures undocumented events degrade gracefully.
