# Pattern: Specify the output shape positively

- **Id:** `pat-specify-output-shape`
- **Dimension:** R10 (missing output specification)
- **Techniques:** T7 (specify output positively), T3 (use examples)
- **Status:** draft

## When it applies

The output's shape matters to the user but the prompt does not state it, so the model must guess the format. A short specification — or one small example — removes the guesswork.

## Transformation

State what the output should be (format, structure, sections), phrased as an instruction to follow rather than a thing to avoid. Optionally show one brief example built from placeholders — the rewrite policy permits placeholder examples only, never invented domain content presented as fact (rewrite-policy compliant).

## Example

**Before**

```
Give me the differences between the two API versions.
```

**After**

```
Give me the differences between the two API versions as a table: one row per
difference, with columns for the feature, its behavior in the first version, and
its behavior in the second. Example row:

| <feature> | <behavior in the first version> | <behavior in the second version> |
```

## Why it helps

A positive format instruction plus one placeholder row communicates the target far more reliably than leaving the shape implicit or describing it in the negative. The request's meaning is unchanged; only its expected form is now explicit — and the example row asserts no facts about the user's APIs.
