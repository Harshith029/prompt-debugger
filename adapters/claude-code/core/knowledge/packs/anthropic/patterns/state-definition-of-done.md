# Pattern: State the definition of done

- **Id:** `pat-state-definition-of-done`
- **Dimension:** R8 (weak objective)
- **Techniques:** T9 (define success criteria and constraints)
- **Status:** draft

## When it applies

The prompt names an activity — "improve", "review", "clean up" — without saying what a successful result contains. Success is unknowable from the prompt, so the model optimizes for its own guess of what "better" means.

## Transformation

State the outcome the user is actually after and what the finished response must contain. The angle-bracket slots mark the success criteria only the user can supply: the rewrite writes down criteria the user already holds and asks when it does not know them — it never invents a definition of done (rewrite-policy compliant).

## Example

**Before**

```
Improve this README.
```

**After**

```
Improve this README so that <the outcome you want — who should be able to do what,
unaided>. Done means the README contains <the specific things a successful version
must include>.
```

## Why it helps

"Improve" admits hundreds of readings — shorter, prettier, more formal. The rewrite replaces the bare activity with an outcome slot and a checkable-contents slot, both filled by the user's real bar. Once filled, the model can verify its own work against the success criteria the user always had but never wrote down.
