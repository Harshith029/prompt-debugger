# Pattern: State goals and constraints, not micromanaged steps

- **Id:** `pat-state-goals-not-steps`
- **Dimension:** R7 (excessive complexity / over-prescription)
- **Techniques:** T10 (avoid over-prescription)
- **Status:** draft

## When it applies

The prompt scripts the model's every move — numbered micro-steps, ALL-CAPS emphasis, "CRITICAL"/"MUST"/"NEVER" scaffolding, nested conditionals — where a goal statement plus real constraints would say the same thing. On current models, this scaffolding is followed literally and can degrade the output it was meant to protect.

## Transformation

Keep every requirement that is real; delete only the emphasis and the step-scripting that restates it. The requirements themselves are preserved exactly — neither narrowed, broadened, weakened, nor strengthened (rewrite-policy compliant).

## Example

**Before**

```
CRITICAL: You MUST read parser.py FIRST. Then you MUST list EVERY function. DO NOT
skip ANY function, this is VERY IMPORTANT. Then for EACH function you MUST write
what it does. NEVER write more than two lines per function. ALWAYS check you did
not miss one. FAILURE TO FOLLOW THESE STEPS EXACTLY IS UNACCEPTABLE.
```

**After**

```
Document every function in parser.py: at most two lines per function on what it
does. Skip none.
```

## Why it helps

The before-prompt has two real requirements — cover every function, at most two lines each — wrapped in eight lines of enforcement theater that current models follow literally at the expense of judgment. The rewrite keeps both requirements at exactly their original strength ("every function", "skip none") and deletes only the duplicated, shouted forms of the same demands.
