# Knowledge Engine

Versioned prompt-engineering knowledge, separated from implementation. Analyzers and adapters **query** this data; they never hardcode guidance. Format contract and provenance rules: [`../contracts/knowledge/CONTRACT.md`](../contracts/knowledge/CONTRACT.md) (ADR-0007).

## Contents

| Pack | Kind | Holds |
|---|---|---|
| [`packs/common/`](packs/common/pack.json) | provider-neutral | Quality rubric (R1–R10); misuse policy, rewrite contract, and fixed notices (M1) |
| [`packs/anthropic/`](packs/anthropic/pack.json) | provider | Claim registry (dated public-doc claims), techniques (T1–T10), observable-event taxonomy, pattern library |

## Status (M1 complete — the verified baseline for M2)

Structure, schemas, and content are CI-validated and frozen as of M1 close-out ([record](../../docs/releases/M1.md)): every claim in the registry is `status: "verified"` against its live source with a `last_verified` date; the `common` pack's misuse policy, rewrite policy, and notices are authored and frozen; the taxonomy's `can/cannot_conclude` prose is complete; the pattern library is complete, one pattern per rubric dimension; and the corpus is versioned as the `2026.07-m1` snapshot. Techniques, taxonomy entries, and patterns remain `status: "draft"` by recorded decision — promotion is deferred to M2, when the analyzer first binds to entry statuses (a content change requiring a snapshot bump under KN-10).

## Rules of the road

- Machine-readable files are JSON (stdlib-parseable); `.md` companions carry extended prose under the same ids.
- Any statement about provider behavior needs a `clm-*` citation; `active` entries may cite only `verified` claims (the claim lifecycle is `recorded`/`verified`/`stale`/`retired`), and taxonomy entries cite only `verified` claims regardless of their own status.
- Adding a provider = adding a pack directory. No code changes, no edits to `common`.
