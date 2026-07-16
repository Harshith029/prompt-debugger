# Pattern: Split unrelated tasks into separate prompts

- **Id:** `pat-split-unrelated-tasks`
- **Dimension:** R5 (multiple unrelated tasks)
- **Techniques:** T8 (decompose or chain complex tasks)
- **Status:** draft

## When it applies

A single prompt bundles independent goals that would each be served better on their own. If removing one goal leaves the others fully intact, they are separable.

## Transformation

Separate the independent requests so each can be answered well. Splitting preserves every original request — nothing is dropped or reworded away (rewrite-policy compliant). Where the tasks are dependent rather than merely bundled, state the sequence instead of splitting.

## Example

**Before**

```
Set up the database schema for the orders service, and also write a launch tweet for it.
```

**After**

```
First prompt: Set up the database schema for the orders service.
Second prompt: Write a launch tweet for the orders service.
```

## Why it helps

The schema task and the marketing task need different context, tone, and success criteria. Answering them separately lets each get the model's full attention and the right framing, without one bleeding into the other. Both original requests are retained in full.
