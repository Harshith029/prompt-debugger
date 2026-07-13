# Notices — prose companion (policy_version 2026.07-draft)

Human/model-readable exposition of the fixed notice texts defined in [`notices.json`](notices.json). Ids match one-to-one. The JSON is what machines validate; this file is what analysis-layer adapters read.

The `notice` value of each entry matches the [Rewrite Report](../../../../core/contracts/rewrite-report/CONTRACT.md) `notices` enum exactly (`non_guarantee`, `epistemic`, `gate_declined`, `gate_conditional`). Keeping the wording here — versioned data, not model output — is what makes the non-guarantee notice stable and testable. Which notice attaches when is declared by the [rewrite policy](rewrite-policy.md) `notice_rules`; this file holds only the text.

## Notice texts

- **NOTICE-001 `non_guarantee`** — the mandatory notice attached whenever a rewrite text exists (RW-2). States that a rewrite improves clarity but does not guarantee a different response, because model behavior depends on provider systems the tool does not control or predict.
- **NOTICE-002 `epistemic`** — marks estimated contributing factors as hypotheses, not facts, and states the analysis uses only observable information, not knowledge of provider internals.
- **NOTICE-003 `gate_conditional`** — states that a conditional rewrite may still receive the same visible response under provider policy; it clarifies intent, it does not make the request more acceptable.
- **NOTICE-004 `gate_declined`** — states that no rewrite was produced, while the observable event is still explained honestly.
