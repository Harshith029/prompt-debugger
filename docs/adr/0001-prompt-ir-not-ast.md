# ADR-0001: Prompt IR instead of a full Prompt AST

- **Status:** Accepted
- **Date:** 2026-07-07

## Context

Findings must point at *parts* of a prompt, revisions must be comparable, and future adapters must visualize prompt structure consistently. That argues for a structured representation of a prompt rather than treating it as an opaque string. The question is *how* structured.

A prompt is natural language, not a formal language. It has no grammar, no guaranteed sections, and enormous surface variety (chat messages, instructions with embedded code, pasted documents, few-shot examples). The producer of the representation, in the v1 adapter, is an LLM.

## Decision

Use a **pragmatic Prompt IR**: an ordered list of *typed segments*, where each segment's text is a **verbatim substring** of the source prompt. Segmentation may be partial (`unsegmented_remainder`). We explicitly do **not** build a full Abstract Syntax Tree with a grammar, nested nodes, and exhaustive tiling.

## Alternatives considered

- **Full Prompt AST (grammar + parser).** Rejected: there is no grammar for natural-language prompts to parse against. Any "AST" would be an LLM's imposed structure dressed up as parse output — implying a rigor that does not exist, and brittle on the long tail of prompt shapes.
- **No structure (operate on raw text; findings carry character offsets).** Rejected: offsets are exactly what LLMs are unreliable at (arithmetic over text), so evidence would frequently be wrong and undetectably so. Comparison and visualization would have nothing to hang on.
- **Rich nested tree now.** Rejected as premature: nesting adds schema complexity (and, under our recursion-free schema subset, is awkward) for structure the v1 features do not consume. The Prompt Tree (ADR-adjacent, separate contract) provides a nested *projection* for visualization when needed, derived from the flat IR.

## Trade-offs

- The IR carries less structure than a tree; consumers that want hierarchy derive it (Prompt Tree projection).
- Segmentation quality depends on the LLM. We accept this because the **verbatim-substring rule makes it checkable**: a substring that isn't in the source is caught deterministically by the verifier, converting "hallucinated structure" from a silent failure into a caught one.

## Consequences

- Evidence in reports is verifiable without trusting the model (substring check).
- The IR schema is simple, recursion-free, and fits the contract subset.
- Non-exhaustive segmentation keeps unusual prompts from breaking analysis.
- A future need for deeper structure is served by extending the Prompt Tree projection, not by re-basing analysis on a grammar.
