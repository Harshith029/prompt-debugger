# Contract: Prompt Tree (v1)

**Purpose.** A host-neutral data model for *visualizing* a prompt's structure, so any future adapter (VS Code, desktop, web) renders prompts the same way. It is a **projection of Prompt IR** — derived data, never a source of truth. Design rationale, section mapping, and rendering guidance: [`docs/design/prompt-tree.md`](../../../docs/design/prompt-tree.md).

## Key design points

- **Flat node list with `parent_id`**, not nested children — the schema subset prohibits recursion (`$ref`), and flat-with-parent is trivially serializable, diffable, and cycle-checkable.
- **Fixed section vocabulary** (`context`, `objective`, `constraints`, `examples`, `output_format`, `success_criteria`, `notes`) — the stable visual grammar across adapters. IR kinds map onto sections deterministically (mapping table in the design doc).
- **Findings overlay** via `annotations`: visualizers can badge nodes with the report findings that reference their segments.

## Invariants (verifier-enforced)

1. `parent_id` references an existing node; the parent graph is acyclic.
2. Every `segment_ids` member exists in the source IR.
3. Every `annotations[].finding_id` exists in the accompanying report.

## Status

Data model contract only — no renderer ships in v1 (the model exists at M0 so adapters can be designed against it; first renderer is a roadmap item).
