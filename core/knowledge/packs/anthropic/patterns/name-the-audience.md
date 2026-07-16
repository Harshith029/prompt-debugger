# Pattern: Name the audience and purpose

- **Id:** `pat-name-the-audience`
- **Dimension:** R2 (missing context)
- **Techniques:** T2 (add context and motivation)
- **Status:** draft

## When it applies

The prompt states a task but not who the output is for, what it is part of, or why it is needed. The model has to guess the intent, and different guesses produce materially different work.

## Transformation

Make the audience and purpose the user actually holds explicit. The angle-bracket slots below mark information the user has but the prompt lacks: the rewrite fills them only with facts the user actually supplied, and asks when it does not have them — it invents nothing (rewrite-policy compliant).

## Example

**Before**

```
Explain how our caching layer works.
```

**After**

```
Explain how our caching layer works, for <who will read this — their role and
familiarity with the system>, so that <what the reader should be able to do with
the explanation>.
```

## Why it helps

Stating the reader and the purpose lets the model select depth, tone, and emphasis instead of inferring them. The slots are filled with the audience and goal the user really has — nothing about the request's meaning changes; the intent is simply no longer hidden.
