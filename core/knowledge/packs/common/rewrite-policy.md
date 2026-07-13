# Rewrite Policy — prose companion (policy_version 2026.07-draft)

Human/model-readable exposition of the rewrite rules defined in [`rewrite-policy.json`](rewrite-policy.json). Ids match one-to-one. The JSON is what machines validate; this file is what analysis-layer adapters read. Design basis: [policy architecture §3](../../../../docs/design/policy-architecture.md).

**Anchor (binding on every rewrite):** a rewrite may make intent *more* explicit, never less, and may use *only* facts the user actually supplied. This policy is declarative data — the rewrite engine interprets it and never executes it.

## Allowed transformations

Each cites the technique ids it applies (provenance to the Anthropic techniques file); `RW-009` is purely mechanical and cites none.

- **RW-001** state audience and purpose, using only supplied context (T2).
- **RW-002** resolve ambiguous referents and undefined terms the user already identified (T1).
- **RW-003** separate unrelated bundled tasks into distinct, ordered requests without dropping any (T8).
- **RW-004** state the definition of done / success criteria the user implied (T9).
- **RW-005** surface constraints the user supplied but left implicit (T9).
- **RW-006** specify output shape positively, placeholder examples only (T7).
- **RW-007** separate instructions from supplied data; long material before the question (T4, T6).
- **RW-008** reduce over-prescription to goals and constraints (T10).
- **RW-009** normalize structure and whitespace with no change to meaning (mechanical).

## Prohibited transformations (the intent-laundering checklist, RG-6)

- **RW-050** fabricate context (facts, credentials, authorization, roles, background) not supplied.
- **RW-051** fictional / hypothetical / roleplay reframing to change the policy reading.
- **RW-052** semantic dilution or euphemism to make the request less legible.
- **RW-053** split a request to distribute a prohibited intent across benign-looking pieces (the abusive inverse of RW-003).
- **RW-054** encode, cipher, translate, or obfuscate content to evade detection.
- **RW-055** invent domain examples that could be read as user-supplied facts (RG-8).

## Guarantees

Each binds an architecture guarantee (`guarantee_ref` → RG-*) and states its enforcement `mode`. *Hard* guarantees are mechanically checkable and fail-closed; *judged* guarantees are evaluated by the meaning-preservation eval suite with a defined bar — an honest distinction, not a hedge.

| Registry id | RG | Mode |
|---|---|---|
| RW-080 | RG-1 meaning preservation | judged |
| RW-081 | RG-2 explicitness monotonicity | judged |
| RW-082 | RG-3 structure preservation | hard |
| RW-083 | RG-4 honesty | hard |
| RW-084 | RG-5 evidence preservation | hard |
| RW-085 | RG-6 no intent laundering | hard |
| RW-086 | RG-7 no fabricated context | hard |
| RW-087 | RG-8 no invented examples | hard |

A declined rewrite trivially satisfies every guarantee (no text is produced). Guarantees constrain *produced* rewrites; the misuse gate constrains *whether* one is produced.

## Notice rules

Which fixed notice attaches in which named situation. `applies_when` is a controlled vocabulary the engine maps to behavior, not a computed condition; the notice texts live in [`notices.json`](notices.json).

- **RW-090** `non_guarantee` when a rewrite is produced (mandatory per RW-2).
- **RW-091** `gate_conditional` when the gate is conditional.
- **RW-092** `gate_declined` when the gate is declined.
- **RW-093** `epistemic` when the report explains an observable event.
