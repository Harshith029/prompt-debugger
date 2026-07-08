# Contract: Observable Event (v1)

**Purpose.** Represents the "Observed" layer of the honesty architecture: a fact about what the user saw, classified against the versioned event taxonomy in the Knowledge Engine (`core/knowledge/packs/<provider>/events.json`). Embedded in Report JSON at `report.event`.

## Semantics

- `verbatim` is the user's evidence, quoted exactly. The analysis layer asks for it when missing and accepts "not available" (`null`).
- `documented_match` links the observation to a taxonomy entry — the entry, in turn, links to dated claims in the claim registry. That chain (observation → taxonomy entry → claim → public URL) is what makes every explanation auditable.
- **`kind: "unknown"` is a first-class outcome, not a failure.** When no taxonomy entry matches, the contract requires classification as `unknown` with `documented_match: null`, and the report proceeds with quality analysis while making no causal claims. Provider documentation changes must degrade gracefully, never silently mis-classify.
- The flagship scenario — a visible model-switch notice after a safeguard decline (e.g., Fable 5 request visibly answered by Opus 4.8) — is `kind: "model_switch"` with the surface the user reported. The *citation* attached via the taxonomy stays within documented API mechanisms; the taxonomy entry records what can and cannot be concluded for each surface.

## Invariants (verifier-enforced)

1. `kind ∈ {unknown, none}` ⇒ `documented_match == null`.
2. `documented_match != null` ⇒ the id exists in the active taxonomy version.

## Compatibility

Adding a `kind` member is a version bump (consumers switch on it); the `unknown` member exists precisely so bumps are rare.
