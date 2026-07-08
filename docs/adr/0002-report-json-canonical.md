# ADR-0002: Report JSON is canonical; Markdown is a rendered view

- **Status:** Accepted
- **Date:** 2026-07-07

## Context

An analysis result must be shown to a human (readable Markdown) *and* be saved, compared across revisions, trended over time, validated, and regression-tested. The v0.1 design produced only Markdown, which the independent review flagged (F2): prose cannot be reliably persisted, diffed, validated, or asserted on.

## Decision

Every analysis produces a **Report JSON** object conforming to the Report contract; it is the **single system of record**. The Markdown a user reads is a **projection** of that object, produced by the renderer. Persistence, comparison, trends, and tests operate exclusively on Report JSON.

## Alternatives considered

- **Markdown as the artifact (v0.1).** Rejected per F2: unstructured text is not a stable interface for storage, diffing, or testing, and it makes evidence unverifiable.
- **Two independent artifacts (model emits both Markdown and JSON separately).** Rejected: they would drift. One canonical object with a deterministic projection guarantees the human view and the stored view agree.
- **A binary/columnar store.** Rejected: over-engineered for the volume; JSON Lines is inspectable, diff-friendly, and stdlib-native.

## Trade-offs

- The analysis layer (an LLM) must emit valid structured JSON. We bound the risk with schema validation at save time, an evidence-substring verifier, and a documented validate→repair→revalidate loop.
- A rendering step is required to show results; but that step is deterministic and cheap, and lets every future adapter render natively from the same object.

## Consequences

- History records embed Report JSON; comparison and trends are well-defined.
- Regression and calibration suites assert on structured fields, not prose.
- Any adapter renders its own Markdown/UI from the canonical object — rendering is never a source of truth.
- The renderer is a required core-library component (M2).
