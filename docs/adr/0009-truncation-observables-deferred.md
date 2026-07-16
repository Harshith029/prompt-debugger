# ADR-0009: Truncation observables are claim-backed but have no taxonomy kind in M1

- **Status:** Accepted
- **Date:** 2026-07-14

## Context

M1 FR-4 (taxonomy prose) verified the stop-reasons documentation (`clm-stop-reasons`): a truncated response is a real, documented, user-visible observable — a successful HTTP 200 response whose `stop_reason` is `max_tokens` or `model_context_window_exceeded`, explicitly distinct from HTTP errors. Users plausibly bring "my response cut off" to the tool.

The frozen v1 Observable Event contract's `kind` enum (`refusal_message`, `model_switch`, `api_refusal_stop_reason`, `api_fallback_block`, `error`, `unknown`, `none`) has no member for a stop condition. M1's constraints forbid contract changes, and no consumer of a truncation classification exists yet (the analyzer is M2).

## Decision

Record the truncation knowledge as a verified claim (`clm-stop-reasons`) and express the boundary as prose in the taxonomy — `evt-user-visible-error.cannot_conclude` states that truncation is a stop condition, not an HTTP error — **without adding a taxonomy entry or a `kind` member in M1**. Until a kind exists, a user-reported truncation flows through the contract-mandated `unknown`-kind honesty path (report what was seen, state that it matches no taxonomy entry), with the claim available for documented explanation prose.

Adding a stop-condition kind (and its taxonomy entry) is deferred to the first milestone where the analyzer needs to *classify* truncation — expected at M2 contract review. Growing the `kind` enum is additive for readers (VC-1/VC-3: unknown members degrade to `unknown`), so the deferral creates no migration debt.

## Alternatives considered

- **Add a `stop_condition` kind now.** Rejected: M1 freezes contracts, no consumer exists, and choosing the member name/granularity (one kind vs. per-stop-reason kinds) is better decided when the analyzer's real classification needs are known — deciding it now is speculative generalization.
- **Shoehorn truncation under `error`.** Rejected as factually wrong: the source documents truncation as a property of a *successful* response, and the taxonomy would then misstate its own source — breaking the accuracy invariant the taxonomy exists to uphold.
- **Leave the knowledge out entirely until M2.** Rejected: the claim is verifiable *now*, and without it the error entry cannot honestly state its own boundary (users conflate truncation with errors; the `cannot_conclude` text must be able to separate them with a citation).

## Trade-offs

Until the kind exists, truncation reports get the honest-but-generic `unknown` path rather than a first-class classification. Accepted: the honesty architecture is designed exactly for this case, and the alternative (a frozen-period contract change for an unconsumed feature) costs more than it buys.

## Consequences

- `clm-stop-reasons` is verified and already cited by `evt-refusal-visible`, `evt-api-refusal-stop-reason`, and `evt-user-visible-error`; only the enum member and taxonomy entry remain when the deferral ends.
- M2's contract review must explicitly revisit this ADR and either add the kind or re-defer with reasons.
- The events prose companion documents the two families ("HTTP errors" vs "stop conditions") so analysis-layer adapters do not conflate them in the interim.
