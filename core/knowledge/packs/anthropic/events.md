# Observable Event Taxonomy — prose companion (anthropic pack, 2026.07-m2)

Extended notes for the entries in [`events.json`](events.json). Ids match. This is the "Observed" layer's reference: it tells the analysis layer exactly what may and may not be concluded from each observation, and which claims back it.

**The honesty rule this file enforces:** for every observation, `can_conclude` is stated as fact tied to a claim; `cannot_conclude` is stated as an explicit boundary. When no entry matches, the outcome is `kind: unknown` (contract-mandated), and the report says: here is what you saw, it matches no documented pattern in taxonomy version X, and no causal claim can be made — followed by ordinary prompt-quality analysis.

**Surface categories.** The core Observable Event contract uses host-neutral surface categories (`web`, `cli`, `desktop`, `api`, `other`, `unspecified`). This provider pack maps Anthropic's product surfaces onto them: the web app → `web`; the Claude Code CLI/agent → `cli`; the desktop app → `desktop`; the direct API → `api`; mobile and other product surfaces → `other`. Product-specific naming stays in this pack, not in the core contract.

## Selection rule: classify by observation channel (deterministic)

Some outcomes have two entries — one for the outcome as *rendered by a product surface*, one for the outcome as *raw API response fields*. Exactly one applies, decided by what the user directly observed:

- **The observation is the raw API response** (the user is reading response fields: `stop_reason`, `stop_details`, content blocks, `usage`): classify with the API-native entry — `evt-api-refusal-stop-reason` or `evt-api-fallback-block`. These entries list exactly one surface, `api`.
- **The observation is a rendered message or notice on a product surface** (web app, CLI transcript, desktop app, mobile, or unstated): classify with the rendered entry — `evt-refusal-visible` or `evt-model-switch-visible`. These entries never list the `api` surface.

Because the paired entries' surface sets are disjoint, one observation can never match both members of a pair; the analyzer has no tie to break. Kinds with a single entry spanning both channels (`error`: the same documented HTTP error may be read as rendered text or as raw JSON) present no ambiguity — there is nothing to select between. This rule is enforced by executable tests (`tests/test_knowledge_integrity.py`) and recorded as invariant EV-4.

## The flagship scenario (`evt-model-switch-visible`)
A user's legitimate prompt is declined by Claude Fable 5's safeguards and the reply is visibly produced by Claude Opus 4.8. Handling:

1. **Observed** — quote the switch/notice the user saw. That it appeared on their screen is a fact.
2. **Citation discipline** — cite what the tracked official documentation supports, *scoped to the surface*: the API mechanism (`clm-fallback-block`), the documented Fable 5 safeguard scope including benign false positives (`clm-fable-classifier-scope`), and — where the surface is known — the product-documented behavior: Claude Code's automatic fallback with a transcript notice (`clm-claude-code-fallback`), or the consumer apps' automatic switching, notice, and model label (`clm-webapp-switch-notice`). The platform API page documents no consumer-surface behavior (`clm-consumer-surface-fallback`); for any surface without a tracked product document, attribute the behavior to the user's report. Never borrow one surface's documentation for another surface.
3. **Estimated** (separate report layer) — confidence-labeled hypotheses about what in the prompt could read as in-scope for a classifier despite benign intent.
4. **Rewrite** (if the request is legitimate) — make the legitimate intent explicit; attach the non-guarantee notice; if the same visible behavior could still occur, say so (`gate: conditional`).

A visible switch is also not proof of a safeguard decline by itself: Claude Code documents availability-based fallback model chains (overload/unavailability) as a separate mechanism from content-based fallback (`clm-claude-code-fallback`), and on the API a sticky-routed turn is served by the fallback model with no fallback block (`clm-fallback-block`).

## Two families of "something stopped" (do not conflate)

A user reporting "it errored" or "it cut off" is describing one of two documented, mutually exclusive families, and the taxonomy keeps them apart:

- **HTTP errors** (`evt-user-visible-error`) — the request *failed to process*. The API returns a documented error status and type string in a top-level `error` object (`clm-api-errors`). The response carries no generated content.
- **Stop conditions** — generation *succeeded and ended for a documented reason*. Every HTTP 200 Messages response carries a `stop_reason` (`clm-stop-reasons`): a truncated reply is `max_tokens` or `model_context_window_exceeded`, a decline is `refusal` (`evt-api-refusal-stop-reason`), and `end_turn`/`stop_sequence`/`tool_use`/`pause_turn` are ordinary completions.

Truncation stop conditions are claim-backed but have **no dedicated taxonomy kind** in the frozen v1 event contract; a user-reported truncation is handled through the `unknown`-kind honesty path, with `clm-stop-reasons` available for the documented explanation. The decision and its revisit trigger are recorded in [ADR-0009](../../../../docs/adr/0009-truncation-observables-deferred.md).
