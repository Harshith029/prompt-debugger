# Notices — prose companion (policy_version 2026.07-m2)

Human/model-readable companion to [`notices.json`](notices.json). Ids match one-to-one.

**Source of truth: [`notices.json`](notices.json).** The JSON file holds the authoritative notice wording; every consumer that emits a notice takes its text from the JSON. This companion is **derived** — the block-quoted texts below are verbatim copies for human reading, and the integrity suite (`tests/test_knowledge_integrity.py`) fails if they drift from the JSON by a single character. To change a notice's wording, edit `notices.json` and update the quote here in the same change.

The `notice` value of each entry matches the [Rewrite Report](../../../../core/contracts/rewrite-report/CONTRACT.md) `notices` enum exactly (`non_guarantee`, `epistemic`, `gate_declined`, `gate_conditional`). Keeping the wording in versioned data — not model output — is what makes the non-guarantee notice stable and testable. Which notice attaches when is declared by the [rewrite policy](rewrite-policy.md) `notice_rules`; this file and its JSON hold only the texts.

## NOTICE-001 `non_guarantee`

The mandatory notice attached whenever a rewrite text exists (invariant RW-2).

> This rewrite is intended to improve clarity and communicate your legitimate intent more effectively. It does not guarantee a different response: model behavior depends on the provider's systems and policies, which this tool does not control or predict.

## NOTICE-002 `epistemic`

Marks the Estimated layer as labelled hypothesis.

> Estimated contributing factors are hypotheses, not facts. This analysis uses only information you can observe; it does not reflect any knowledge of a provider's internal systems, moderation logic, or thresholds.

## NOTICE-003 `gate_conditional`

States the honest boundary of a conditional gate.

> This rewrite may still receive the same visible response under the provider's policies. It clarifies your intent; it does not make the request more acceptable to any provider.

## NOTICE-004 `gate_declined`

Accompanies a declined gate.

> A rewrite was not produced for this request. The observable event, if any, is still explained honestly.
