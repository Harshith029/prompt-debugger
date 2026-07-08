# Prompt Tree — visualization design

**Status:** design only (no renderer ships in v1). The data model exists at M0 so future adapters (VS Code, desktop, web) can be designed against a stable target. Contract: [`core/contracts/prompt-tree/`](../../core/contracts/prompt-tree/CONTRACT.md).

## Purpose

Give every adapter one consistent way to *show* a prompt's structure and the findings attached to each part. The Prompt Tree is a **projection of the Prompt IR** (ADR-0001) — derived, never authoritative. Analysis always operates on the IR and the Report; the tree is for humans looking at a prompt.

## The seven sections

A prompt is presented under a fixed, ordered section vocabulary. This is the stable visual grammar users learn once and see everywhere:

| Section | Holds | Sourced from IR kinds |
|---|---|---|
| **Context** | Who it's for, background, domain, motivation | `role`, `context` |
| **Objective** | The core task / what to produce | `task` |
| **Constraints** | Boundaries: length, tone, tech, do/don't | `constraint` |
| **Examples** | Few-shot examples, samples | `example` |
| **Output Format** | Required shape of the answer | `output_spec` |
| **Success Criteria** | Definition of done | `success_criteria` |
| **Notes** | Embedded data and meta commentary that doesn't map above | `data`, `meta`, `other`, unsegmented remainder |

### IR-kind → section mapping (normative)

```
role             -> Context
context          -> Context
task             -> Objective
constraint       -> Constraints
example          -> Examples
output_spec      -> Output Format
success_criteria -> Success Criteria
data             -> Notes
meta             -> Notes
other            -> Notes
(unsegmented)    -> Notes
```

A section with no matching segments is rendered as **empty/absent** — an absent "Success Criteria" or "Output Format" section is itself a signal (it often corresponds to R8/R10 findings) and adapters may surface it as a gentle prompt to the user.

## Data model

The tree is a **flat node list with `parent_id`** (not nested children), because the schema subset forbids recursion and a flat list is trivial to serialize, diff, and cycle-check. Each node names its `section`, a human `label`, the IR `segment_ids` it covers, and an `annotations` list linking report findings.

```json
{
  "tree_version": 1,
  "source_ir_version": 1,
  "nodes": [
    { "id": "n1", "parent_id": null, "section": "objective", "label": "Objective",
      "segment_ids": ["s2"], "annotations": [] },
    { "id": "n2", "parent_id": null, "section": "output_format", "label": "Output Format",
      "segment_ids": ["s3"], "annotations": [{ "finding_id": "f4" }] }
  ]
}
```

Top-level nodes are the section headers (`parent_id: null`); child nodes (optional) break a section into individual segments or grouped items. Invariants (parent references exist, no cycles, segment/finding ids resolve) are verifier-enforced — see the contract.

## Rendering guidance for adapters

- **Order** sections as listed above; keep the order fixed across adapters so users build muscle memory.
- **Badge** nodes carrying `annotations` with the finding's severity color; clicking a badge reveals the finding's evidence, explanation, and fix.
- **Empty sections** are shown as faint placeholders, not hidden — their absence is informative.
- **Never** show fabricated content: node labels are structural; segment text always comes verbatim from the source prompt (the IR guarantees this).
- Rendering is a **view**: two adapters given the same IR + Report must produce the same tree structure.

## Non-goals

- The tree does not re-analyze; it visualizes the Report.
- No editing in v1 (a future "edit in tree, re-emit prompt" flow is a roadmap idea, out of scope here).
