# Pattern: Surface the real scope

- **Id:** `pat-surface-real-scope`
- **Dimension:** R4 (scope creep)
- **Techniques:** T8 (decompose or chain complex tasks), T9 (define success criteria and constraints)
- **Status:** draft

## When it applies

The stated task is one thing, but asides — "also", "while you're at it", "might as well" — smuggle in more. The real scope is larger than the headline task, and nothing says whether the asides are requirements or wishes.

## Transformation

Make every aside a visible scope decision. A firm requirement becomes an explicit numbered item; a tentative aside ("probably", "might as well") stays tentative — it becomes an explicit question, not a silently promoted requirement. Nothing the user mentioned is dropped, and nothing tentative is hardened without the user deciding (rewrite-policy compliant).

## Example

**Before**

```
Write a migration script for the users table (we should probably handle the audit
log too while you're at it, and might as well archive the old export files).
```

**After**

```
Write a migration script for the users table.

Before starting, settle the scope of the two asides:
- <is handling the audit log part of this task, or a separate one?>
- <is archiving the old export files part of this task, or a separate one?>
```

## Why it helps

The before-prompt has one visible task and two asides that may or may not be requirements — any of the three could be skipped or half-done without clearly violating the request. The rewrite keeps the firm task firm and turns each tentative aside into an explicit decision, preserving exactly the certainty the user expressed: no wish is silently promoted, and no request is lost in a parenthesis.
