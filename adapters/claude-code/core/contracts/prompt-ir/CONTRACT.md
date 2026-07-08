# Contract: Prompt IR (v1)

**Purpose.** A pragmatic intermediate representation of an analyzed prompt: an ordered list of typed segments. It exists so findings can point at *parts* of a prompt, revisions can be compared structurally, and visualizations (Prompt Tree) can be projected — without the fragility of a full grammar. See ADR-0001.

**Producer:** the analysis layer (an LLM in the Claude Code adapter). **Consumers:** Report JSON, Prompt Tree projection, history comparison, future adapters.

## Semantics

- `segments[].text` is a **verbatim substring** of the source prompt. This is the contract's load-bearing integrity rule: it makes LLM-produced structure *machine-checkable* (substring verification), so hallucinated evidence is caught deterministically.
- Segments are listed in prompt order. Overlaps are prohibited in spirit but not schema-checked in v1; the verifier warns on them.
- Segmentation may be partial: `unsegmented_remainder: true` signals that untyped spans remain. Full tiling is deliberately not required — unusual prompts must not break analysis.
- `kind` is a closed enum in v1. `success_criteria` is distinct from `constraint`: constraints bound the work, success criteria define "done". `data` marks embedded material to be operated on (documents, code, logs); `meta` marks commentary about the prompt itself.

## Example instance

```json
{
  "ir_version": 1,
  "segments": [
    { "id": "s1", "kind": "role", "text": "You are a security reviewer.", "note": null },
    { "id": "s2", "kind": "task", "text": "Review this login handler for vulnerabilities.", "note": null },
    { "id": "s3", "kind": "output_spec", "text": "Reply as a numbered list.", "note": null }
  ],
  "unsegmented_remainder": false
}
```

## Compatibility

v1 is frozen per the rules in [`../README.md`](../README.md). Adding a new `kind` member is a **breaking change** (closed enum) → v2. Adding an optional segment field is additive.
