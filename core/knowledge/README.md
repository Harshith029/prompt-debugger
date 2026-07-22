# Knowledge Engine

Versioned prompt-engineering knowledge, separated from implementation. Analyzers and adapters **query** this data; they never hardcode guidance. Format contract and provenance rules: [`../contracts/knowledge/CONTRACT.md`](../contracts/knowledge/CONTRACT.md) (ADR-0007).

## Contents

| Pack | Kind | Holds |
|---|---|---|
| [`packs/common/`](packs/common/pack.json) | provider-neutral | Quality rubric (R1–R10); misuse policy, rewrite contract, and fixed notices (M1) |
| [`packs/anthropic/`](packs/anthropic/pack.json) | provider | Claim registry (dated public-doc claims), techniques (T1–T10), observable-event taxonomy, pattern library |

## Status (M1 verified; claim-grounded classes promoted in M2)

Structure, schemas, and content are CI-validated: every claim in the registry is `status: "verified"` against its live source with a `last_verified` date (M1 close-out, [record](../../docs/releases/M1.md)); the `common` pack's misuse policy, rewrite policy, and notices are authored and frozen; the taxonomy's `can/cannot_conclude` prose is complete; and the pattern library is complete, one pattern per rubric dimension. The M2 FR-8 promotion pass made every **technique and event-taxonomy entry** `status: "active"` (each cites only `verified` claims — the KN-2 criterion; decision recorded in the CHANGELOG) and bumped the corpus to the `2026.07-m2` snapshot per KN-10. **Rubric dimensions and patterns remain `status: "draft"`**: they carry `status` fields but no claim-provenance relation, so no repository artifact grounds a promotion criterion for them — defining one is an open governance decision (specs/M2.md, open choice O7), not silently decided.

## Rules of the road

- Machine-readable files are JSON (stdlib-parseable); `.md` companions carry extended prose under the same ids.
- Any statement about provider behavior needs a `clm-*` citation; `active` entries may cite only `verified` claims (the claim lifecycle is `recorded`/`verified`/`stale`/`retired`), and taxonomy entries cite only `verified` claims regardless of their own status.
- Adding a provider = adding a pack directory. No code changes, no edits to `common`.
