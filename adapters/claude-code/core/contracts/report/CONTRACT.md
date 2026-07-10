# Contract: Report JSON (v1)

**Purpose.** The canonical, machine-readable record of one analysis. Persistence, comparison, trends, regression testing, and rendering all operate on this object; the Markdown a user reads is a **projection** of it, regenerable by `render` (M2). See ADR-0002.

**Producer:** the analysis layer. **Consumers:** Storage (embedded in history records), `render`, `compare`/`trends`, evals and benchmarks, future adapters.

## Semantics

- `knowledge` pins the Knowledge Engine versions used, making every report reproducible against a specific rubric/taxonomy state.
- `event` is `null` for pure quality reviews (no observable event was reported).
- `estimates` exist **only** when an event was reported, and are hypotheses with confidence labels — the honesty architecture's "Estimated" layer. The "Observed" layer is the `event` object.
- `findings[].evidence[].quote` is verbatim-substring-verified against the source prompt; `segment` ties evidence to Prompt IR structure.
- `rewrite` is `null` when no rewrite was requested; see the Rewrite Report contract for gate semantics.
- Composite validation per [`../README.md`](../README.md): `ir`, `event`, `rewrite` validate against their own schemas.

## Invariants (verifier-enforced, beyond schema)

1. Every evidence quote is a verbatim substring of its **reference prompt**. The reference prompt depends on context: for a **live** report it is the original prompt; for a report **embedded in a persisted `raw: false` history record** it is the redacted prompt (`prompt_redacted`), because persistence redacts all report content (storage invariant PR-1). The substring relationship holds in both contexts against the appropriate reference.
2. Every `evidence[].segment` id exists in `ir.segments` (or is null).
3. `estimates != null` ⇒ `event != null`.
4. Finding ids are unique.
5. IR segment text follows the same reference-prompt rule as evidence quotes (invariant 1).

## Compatibility

Additive optional fields allowed within v1. Changing severity/confidence enums, finding shape, or the composite-field set is breaking → v2.
