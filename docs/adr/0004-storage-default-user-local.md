# ADR-0004: Default storage is user-local

- **Status:** Accepted
- **Date:** 2026-07-07

## Context

History must be saved somewhere. A project-local default directory (for example `.prompt-debugger/` inside the working repository) risks accidental commits of prompt history — potentially sensitive text — into shared repositories.

## Decision

Default storage is **user-local**: `~/.prompt-debugger/stores/<project-key>/`, where `project-key` keeps stores separated per project while living outside any repository. Project-local storage (`<project>/.prompt-debugger/`) is available but requires **explicit opt-in** (config `storage_scope: project` plus an acknowledgement flag), and when chosen the store directory is created **self-ignoring** (contains a `.gitignore` with `*` and a warning README).

## Alternatives considered

- **Project-local default.** Rejected: too easy to `git add .` prompt history into a shared repository.
- **User-local only, no project option.** Rejected: some users legitimately want history to travel with a project; forbidding it outright is paternalistic. Opt-in with guardrails serves them safely.
- **A single global store (not per-project).** Rejected: mixes unrelated projects' history and makes per-project trends meaningless.

## Trade-offs

- The per-project store lives away from the project, so it is less discoverable. Mitigated by documentation and a stable, inspectable path.
- Project-key derivation must be stable across sessions; the storage layer computes it from the project path.

## Consequences

- The default path can never be accidentally committed.
- Project-local opt-in is safe by construction (self-ignoring).
- PRIVACY.md documents exact locations so users can inspect and delete data by hand.
- The default location is safe by construction: it cannot be accidentally committed to a project repository.
