# Pattern: Resolve ambiguous referents and terms

- **Id:** `pat-resolve-ambiguity`
- **Dimension:** R1 (ambiguity)
- **Techniques:** T1 (be clear and direct)
- **Status:** draft

## When it applies

The prompt uses referents or terms with more than one plausible reading — "it", "the other one", "looks off" — and the readings lead to materially different work. It fails the colleague test: a colleague with minimal context would have to ask which one you meant.

## Transformation

Replace each ambiguous referent with the specific thing the user actually means, and each vague judgment word with the concrete criterion the user actually holds. The angle-bracket slots mark exactly those places: the rewrite fills them only with the user's own referents and criteria, and asks when it does not know them — it never guesses (rewrite-policy compliant).

## Example

**Before**

```
Take the numbers from the last run and compare them with the baseline. If it looks
off, flag it.
```

**After**

```
Take the <which numbers, exactly> from the last run and compare them with
<which baseline>. Flag a result when <the concrete criterion you mean by "looks
off">, and flag it by <what flagging should produce>.
```

## Why it helps

Every ambiguous token is now a named decision instead of a silent guess: which numbers, which baseline, what "off" means, and what "flag it" produces. The request's meaning is unchanged — the reading the user always intended becomes the only one available, once the user's own answers fill the slots.
