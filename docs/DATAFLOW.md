# Data flow

How a request moves through the system. Nothing here performs network I/O; every box runs on the user's machine.

## Analyze flow (the main path)

```
user input (prompt and/or pasted visible event)
      │
      ▼
[adapter: analyze skill]  ── wraps user text as DATA, not instructions
      │
      ├─ Observe ──▶ classify event vs Knowledge Engine taxonomy ──▶ Observable Event (or kind=unknown)
      │
      ├─ Gate ─────▶ misuse decision procedure (Knowledge Engine misuse policy)
      │                 ├─ circumvention → explain event, decline rewrite, stop
      │                 └─ legitimate/uncertain → continue (ask if purpose missing)
      │
      ├─ Segment ──▶ Prompt IR (typed, verbatim segments)
      │
      ├─ Analyze ──▶ findings vs rubric (R1–R10), each with verbatim evidence
      │
      ├─ Estimate ─▶ (only if event present) confidence-labeled hypotheses + epistemic notice
      │
      └─ Rewrite ──▶ (only if legitimate) techniques T1–T10 under transformation rules,
                       per-change log, non-guarantee notice, conditional flag if applicable
      │
      ▼
Report JSON  ◀── canonical (validated against Report contract; evidence substring-verified)
      │
      ├─▶ render ──▶ Markdown shown to the user (a projection)
      │
      └─▶ (optional) Prompt Tree projection for visualization
      │
      ▼
offer save ──▶ user says yes ──▶ [library CLI: storage.append]
                                     redact ▶ fingerprint ▶ validate ▶ atomic append under lock
                                     │
                                     ▼
                          ~/.prompt-debugger/stores/<key>/history.jsonl
```

## Trust boundaries

| Boundary | Untrusted side | Control |
|---|---|---|
| User-pasted prompt/event → analysis | the pasted text | wrapped as data; adapters run with `disallowed-tools: Write Edit NotebookEdit Bash` |
| Model output → Report | LLM-produced JSON | schema validation + evidence substring verification before it is trusted or stored |
| Stored record → display/export | file on disk (could be hand-edited) | schema-validate + sanitize on read; `doctor` quarantines bad lines |
| Export → external viewer (Excel, etc.) | export consumer | CSV formula-escaping; control-char/ANSI stripping |

## Knowledge resolution

Every guidance value (rubric text, technique, taxonomy fact, notice, policy rule) is read from the Knowledge Engine packs — never hardcoded. The provenance chain for any factual claim is: report → taxonomy entry → claim id → dated public URL.

## What never happens

- No bytes leave the machine (no network I/O anywhere; enforced by import policy + socket-block tests).
- No persistence without an explicit user "save".
- No raw prompt stored without a per-save confirmation.
