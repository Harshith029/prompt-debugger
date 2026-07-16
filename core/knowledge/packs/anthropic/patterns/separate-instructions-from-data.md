# Pattern: Separate instructions from data

- **Id:** `pat-separate-instructions-from-data`
- **Dimension:** R6 (poor formatting)
- **Techniques:** T4 (structure with XML tags), T6 (long-context ordering)
- **Status:** draft

## When it applies

Instructions and pasted material are interleaved in one block: a log or document sits mid-sentence, the question is buried before or inside the data, and nothing marks where the user's words end and the material begins.

## Transformation

Wrap the pasted material in a labeled tag, place long material before the questions, and list the questions at the end. Every sentence of the original — instruction and data alike — survives; only the arrangement changes, and no instruction is added (rewrite-policy compliant). (The `<build-log>` tags below are literal output structure demonstrated by this pattern, not placeholder slots.)

## Example

**Before**

```
Why did the nightly build fail I'm pasting the log ERROR: task :api:compileJava
FAILED ... [190 more lines] ... also what should we change so this stops happening
```

**After**

```
<build-log>
ERROR: task :api:compileJava FAILED
... [190 more lines] ...
</build-log>

The log above is from the nightly build.

1. Why did the build fail?
2. What should we change so this stops happening?
```

## Why it helps

Tagged data cannot be mistaken for instructions, and instructions cannot drown in the data. Long-material-first ordering with the questions last matches the documented long-context guidance. Both original questions are intact and unmodified; the log is byte-for-byte the user's own.
