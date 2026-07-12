# Pattern: Specify the output shape positively

- **Id:** `pat-specify-output-shape`
- **Dimension:** R10 (missing output specification)
- **Techniques:** T7 (specify output positively), T3 (use examples)
- **Status:** draft

## When it applies

The output's shape matters to the user but the prompt does not state it, so the model must guess the format. A short specification — or one small example — removes the guesswork.

## Transformation

State what the output should be (format, structure, sections), phrased as an instruction to follow rather than a thing to avoid. Optionally show one brief example. This adds a constraint the user actually holds; it does not change the substance of the request (rewrite-contract compliant).

## Example

**Before**

```
Give me the differences between the two API versions.
```

**After**

```
Give me the differences between the two API versions as a table with three columns:
Feature, v1 behavior, v2 behavior. One row per feature that changed. Example row:

| Feature      | v1 behavior            | v2 behavior              |
|--------------|------------------------|--------------------------|
| Pagination   | offset-based          | cursor-based             |
```

## Why it helps

A positive format instruction ("a table with three columns…") plus one example communicates the target far more reliably than leaving the shape implicit or describing it in the negative. The request's meaning is unchanged; only its expected form is now explicit.
