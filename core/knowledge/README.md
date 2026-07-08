# Knowledge Engine

Versioned prompt-engineering knowledge, separated from implementation. Analyzers and adapters **query** this data; they never hardcode guidance. Format contract and provenance rules: [`../contracts/knowledge/CONTRACT.md`](../contracts/knowledge/CONTRACT.md) (ADR-0007).

## Contents

| Pack | Kind | Holds |
|---|---|---|
| [`packs/common/`](packs/common/pack.json) | provider-neutral | Quality rubric (R1–R10); misuse policy, rewrite contract, and fixed notices (M1) |
| [`packs/anthropic/`](packs/anthropic/pack.json) | provider | Claim registry (dated public-doc claims), techniques (T1–T10), observable-event taxonomy, pattern library |

## Status at M0

Structure, schemas, and seed content exist and are CI-validated. Seed entries are `status: "draft"` / claims `status: "recorded"` — **Milestone M1 performs the verification pass**: re-check every claim against its live source, promote to `verified`/`active`, expand taxonomy `can/cannot_conclude` prose, populate the pattern library, and add the `common` pack's misuse policy, rewrite contract, and notices files.

## Rules of the road

- Machine-readable files are JSON (stdlib-parseable); `.md` companions carry extended prose under the same ids.
- Any statement about provider behavior needs a `clm-*` citation; CI warns when active entries cite non-active claims.
- Adding a provider = adding a pack directory. No code changes, no edits to `common`.
