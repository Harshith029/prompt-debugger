# Techniques — prose companion (anthropic pack, 2026.07-m2)

Extended guidance for the techniques in [`techniques.json`](techniques.json). Ids match. Every technique traces to one or more claims in [`claims.json`](claims.json); the analysis layer reads this file, machines validate the JSON.

Worked before/after examples live in the [pattern library](patterns/index.json), one per rubric dimension; each pattern cites the technique ids it applies. Every claim cited here is `verified` (M1), and every technique is `status: active` as of the M2 FR-8 promotion (every cited claim verified — the KN-2 criterion; decision recorded in the CHANGELOG). Patterns remain `status: draft`: they carry no claim-provenance relation, so their promotion criterion is an open governance decision (specs/M2.md, open choice O7).

- **T1 Be clear and direct** — the golden rule (colleague test) and specificity. Grounds fixes for R1, R3.
- **T2 Add context and motivation** — state audience, purpose, and the reason behind constraints. Grounds fixes for R2.
- **T3 Use examples (multishot)** — 3–5 diverse examples in tags. Grounds fixes for R10.
- **T4 Structure with XML tags** — separate instruction from data. Grounds fixes for R6.
- **T5 Give the model a role** — one-sentence role. Supporting technique.
- **T6 Order long context correctly** — data first, query last, quote-ground. Grounds fixes for R6.
- **T7 Specify output positively** — say what to produce. Grounds fixes for R9, R10.
- **T8 Decompose or chain** — split unrelated goals; sequence dependent ones. Grounds fixes for R4, R5.
- **T9 Define success criteria and constraints** — checkable "done" and stated constraints. Grounds fixes for R4, R8, R9.
- **T10 Avoid over-prescription** — goals over emphatic step-lists on current models. Grounds fixes for R7.
