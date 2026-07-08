---
name: history
description: Saves prompt analyses locally, compares revisions, shows trends, and exports reports. Local-first; writes only when explicitly asked. Storage is user-local by default; project-local storage is explicit opt-in.
argument-hint: "[save | list | compare <id> <id> | trends | export <format> | strip-raw <id> | delete <id>]"
disable-model-invocation: true
allowed-tools: >
  Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/run.py *)
  Bash(python ${CLAUDE_SKILL_DIR}/scripts/run.py *)
  Bash(py -3 ${CLAUDE_SKILL_DIR}/scripts/run.py *)
---

# History

> **Milestone M0 skeleton.** The launcher shim `scripts/run.py` exists; the storage
> library it dispatches to (`prompt_debugger.cli`) is implemented in Milestone M2.
> This skill is user-invocable only — Claude never persists data on its own.

Thin wrapper over the storage CLI (the only writer of history). Storage defaults to
user-local `~/.prompt-debugger/`; project-local is explicit opt-in and self-ignoring.
Raw prompt storage requires per-save confirmation and is reversible via `strip-raw`.

## Commands (dispatched to the library, M2)

| Command | Effect |
|---|---|
| `save` | Validate the current Report JSON, redact, fingerprint, append under the store lock. Prompts for confirmation before storing raw text. |
| `list` | List records in id order; raw records are visibly flagged. |
| `compare <a> <b>` | Rubric-score delta + redacted-prompt diff. |
| `trends` | Per-dimension finding counts over time. |
| `export <md\|csv\|json>` | Redacted, fingerprint-free export by default. |
| `strip-raw <id>` | Convert a raw record to redacted in place. |
| `delete <id>` / `purge` | Destroy user-owned data. |

Cross-platform launcher: `run.py` is invoked via `python3`, `python`, or `py -3`
(all three pre-approved above). See `../../core/contracts/storage/CONTRACT.md`.
