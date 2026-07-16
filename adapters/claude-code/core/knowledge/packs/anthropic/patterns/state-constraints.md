# Pattern: State the constraints you hold

- **Id:** `pat-state-constraints`
- **Dimension:** R9 (missing constraints)
- **Techniques:** T9 (define success criteria and constraints), T7 (specify output positively)
- **Status:** draft

## When it applies

The user holds real requirements — language, versions, boundaries, tone, length — but the prompt does not state them, so a correct-looking response is likely to be invalidated by a constraint the model never saw.

## Transformation

Surface the constraints the user actually has, phrased positively as instructions to follow. The angle-bracket slots mark those constraints: the rewrite records only requirements the user really holds and asks when it does not know them — a constraint the user does not hold has no place in the rewrite (rewrite-policy compliant).

## Example

**Before**

```
Write a function to dedupe these records.
```

**After**

```
Write a function to dedupe these records, where <which field or fields make two
records duplicates> and keeping <which of the duplicates should win>. Constraints
that already apply: <language and version, allowed dependencies, I/O boundaries,
error behavior — whichever of these you actually have>.
```

## Why it helps

The before-prompt would accept an answer in any language, with any dedupe key, any tie-breaking rule, and any error behavior — each a way to be wrong that the user would reject on sight. The rewrite names those decision points and fills them with the requirements that were always going to be applied, so the first response can be the acceptable one.
