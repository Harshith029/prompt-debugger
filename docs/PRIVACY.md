# Privacy model

The design goal is simple: **your prompts are yours, and nothing leaves your machine.** This document is the honest, complete account — including limits.

> **Implementation status.** This document describes the privacy *model* the storage layer is contractually required to implement. The storage layer and its redaction, saving, and export operations are implemented in Milestone M2; they do not exist in the current pre-release. The commands referenced below (`history save`, `list`, `purge`, `strip-raw`, `archive`) name that designed interface, not a shipped one. The redaction guarantee (PR-1) is fixed as a contract now and is enforced by an executable test that the M2 implementation must satisfy.

## Data inventory

The system can touch exactly two things:

1. Text you paste into your own session (a prompt, a visible message, an error).
2. Records you explicitly choose to save to your own disk.

There are **no accounts, no identifiers, no network calls, no telemetry, and no analytics** anywhere in the codebase. This is enforced, not just promised: the shipped library passes an AST import check (no network modules) and the test suite runs with sockets blocked (see [THREAT-MODEL.md](THREAT-MODEL.md), S6).

## Defaults

- **Nothing is persisted** unless you run a save command. Analysis is otherwise ephemeral conversation.
- **On save**, redaction is applied to the **entire record**, not just the prompt. A default record contains a redacted prompt, a redacted copy of the analysis report, and a per-store salted fingerprint (for matching revisions). Redaction removes common secret shapes (API keys, tokens, PEM blocks, `password=`/`token=` assignments) and emails, replacing them with typed placeholders. Because the report embeds verbatim excerpts of the prompt (segment text and evidence quotes), those excerpts are redacted too — a secret scrubbed from the prompt cannot survive in the stored report. This is the contractual redaction invariant **PR-1** (see [CONTRACT-INVARIANTS.md](CONTRACT-INVARIANTS.md)).
- **Raw (unredacted) storage is rare, loud, and reversible:** it requires a per-save confirmation, raw records are visibly flagged in listings, and `strip-raw <id>` converts a raw record (and its embedded report) back to redacted.
- **Exports are redacted and fingerprint-free by default.** Including raw content requires an explicit flag that prints a warning.

## Data lifecycle

| Stage | What | Where | How to inspect / control |
|---|---|---|---|
| Create | redacted prompt + **redacted** report + fingerprint | `~/.prompt-debugger/stores/<key>/history.jsonl` | `history list`, or open the JSONL file |
| Opt-in project-local | same, in-repo | `<project>/.prompt-debugger/` (self-ignoring) | requires explicit opt-in; store carries its own `.gitignore` with `*` |
| Raw (opt-in) | unredacted prompt too | same record, `raw: true` | flagged in `list`; reversible via `strip-raw` |
| Export | rendered report | wherever you write it | you create it deliberately; header notes it may contain prompt text |
| Delete | — | — | `history delete <id>`, `history purge`, or delete the files by hand |
| Archive | rotated history | `stores/<key>/archive/` | `history archive` |

## Honest limits

- **Redaction is best-effort pattern matching, not a guarantee.** It will miss novel secret formats and unusual PII. Treat it as a safety net, not a vault. If a prompt contains something you must not persist, don't save it raw.
- **Content you paste into a session is processed by the provider** under your existing agreement with them. The tool adds *no additional* data flow — but it does not make the underlying conversation more private than it already is.
- **The store is a plain file you own.** Anyone with access to your machine/account can read it, just like any other local file. Protect it as you would any local data.

## Deletion is real

`purge` and manual file deletion remove the data — there is no server-side copy, because there is no server. What you delete is gone.
