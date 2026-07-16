# Pattern: Reconcile contradictory instructions

- **Id:** `pat-reconcile-contradictions`
- **Dimension:** R3 (contradictory instructions)
- **Techniques:** T1 (be clear and direct)
- **Status:** draft

## When it applies

Two instructions cannot both be satisfied — or the same concept appears under different names, forcing the model to decide silently whether they are the same thing. Left unresolved, the model must privilege one instruction over the other without telling the user which.

## Transformation

Surface the conflict explicitly and let the user's actual priority resolve it. Neither requirement is weakened, dropped, or resolved by guesswork: the rewrite states the conflict and carries the user's decision as the resolution — when the priority is unknown, it asks (rewrite-policy compliant).

## Example

**Before**

```
Summarize the audit in detail, covering all twelve findings thoroughly. Keep the
whole summary under 100 words.
```

**After**

```
Summarize the audit, covering all twelve findings. <"In detail, thoroughly" and
"under 100 words" conflict at this size — which takes priority? The rewrite keeps
the prioritized requirement exactly as stated and relaxes only the other.>
```

## Why it helps

"Thorough detail on twelve findings" and "under 100 words" cannot both hold; before the rewrite, the model had to break one rule silently. The rewrite makes the conflict visible and hands the choice to the only party entitled to make it. Both requirements survive verbatim until the user says which one bends — nothing is invented and nothing is quietly dropped.
