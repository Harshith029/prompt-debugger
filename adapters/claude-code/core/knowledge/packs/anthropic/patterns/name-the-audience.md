# Pattern: Name the audience and purpose

- **Id:** `pat-name-the-audience`
- **Dimension:** R2 (missing context)
- **Techniques:** T2 (add context and motivation)
- **Status:** draft

## When it applies

The prompt states a task but not who the output is for, what it is part of, or why it is needed. The model has to guess the intent, and different guesses produce materially different work.

## Transformation

Add the audience and the purpose the user actually holds. This makes existing intent explicit — it introduces no new requirements and no facts the user did not supply (rewrite-contract compliant).

## Example

**Before**

```
Explain how our caching layer works.
```

**After**

```
Explain how our caching layer works, for a new backend engineer joining the team
next week. The goal is to get them productive making changes to it, so focus on the
read/write paths and the invalidation rules rather than the history of why it was built.
```

## Why it helps

Stating the reader ("a new backend engineer") and the purpose ("get them productive making changes") lets the model select depth, tone, and emphasis instead of inferring them. Nothing about the request's meaning changed; the intent is simply no longer hidden.
