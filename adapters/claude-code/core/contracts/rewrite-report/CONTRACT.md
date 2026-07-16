# Contract: Rewrite Report (v1)

**Purpose.** The structured result of a rewrite request, embedded in Report JSON at `report.rewrite`. It encodes the legitimacy-gate outcome so gate behavior is testable (red-team evals assert `gate` values), and it forces every change to be explained.

## Gate semantics

| `gate` | Meaning | `text` |
|---|---|---|
| `passed` | Legitimate intent; rewrite produced | rewritten prompt |
| `conditional` | Rewrite produced, **and** the report explicitly states the same visible behavior may still occur under provider policy | rewritten prompt |
| `declined` | Circumvention intent or no plausible legitimate reading; rewrite refused per the misuse policy | `null` |

`gate_reason` is required prose whenever `gate != passed` (verifier-enforced).

## Notices

`notices` lists which fixed texts accompany the rewrite. The texts themselves are versioned Knowledge Engine content — **`core/knowledge/packs/common/notices.json` is the single source of truth for the wording**; its `notices.md` companion is derived from it and drift-checked by an integrity test — not free-form model output, so the non-guarantee wording is stable and testable. `non_guarantee` is **mandatory whenever `text != null`** (verifier-enforced).

## Invariants (verifier-enforced)

1. `gate == "declined"` ⇔ `text == null`.
2. `text != null` ⇒ `"non_guarantee" ∈ notices`.
3. `gate != "passed"` ⇒ `gate_reason != null`.

## Transformation rules

What a rewrite may and may not do is defined in the misuse policy and rewrite contract knowledge files (M1: `core/knowledge/packs/common/`). Binding invariant: **a rewrite may make intent more explicit, never less, and may only use facts the user actually supplied.**

## Compatibility

Adding a notice enum member is additive (consumers ignore unknown notices when rendering). Changing gate members is breaking → v2.
