# Observable Event Taxonomy — prose companion (anthropic pack, 2026.07-draft)

Extended notes for the entries in [`events.json`](events.json). Ids match. This is the "Observed" layer's reference: it tells the analysis layer exactly what may and may not be concluded from each observation, and which claims back it.

**The honesty rule this file enforces:** for every observation, `can_conclude` is stated as fact tied to a claim; `cannot_conclude` is stated as an explicit boundary. When no entry matches, the outcome is `kind: unknown` (contract-mandated), and the report says: here is what you saw, it matches no documented pattern in taxonomy version X, and no causal claim can be made — followed by ordinary prompt-quality analysis.

**Surface categories.** The core Observable Event contract uses host-neutral surface categories (`web`, `cli`, `desktop`, `api`, `other`, `unspecified`). This provider pack maps Anthropic's product surfaces onto them: the web app → `web`; the Claude Code CLI/agent → `cli`; the direct API → `api`. Product-specific naming stays in this pack, not in the core contract.

## The flagship scenario (`evt-model-switch-visible`)
A user's legitimate prompt is declined by Claude Fable 5's safeguards and the reply is visibly produced by Claude Opus 4.8. Handling:

1. **Observed** — quote the switch/notice the user saw. That it appeared on their screen is a fact.
2. **Citation discipline** — cite the documented API fallback mechanism (`clm-fallback-block`) and the documented Fable 5 safeguard scope including benign false positives (`clm-fable-classifier-scope`). Do **not** assert how the specific consumer surface implements the switch until `clm-consumer-surface-fallback` is verified in M1; attribute the surface's behavior to the user's report.
3. **Estimated** (separate report layer) — confidence-labeled hypotheses about what in the prompt could read as in-scope for a classifier despite benign intent.
4. **Rewrite** (if the request is legitimate) — make the legitimate intent explicit; attach the non-guarantee notice; if the same visible behavior could still occur, say so (`gate: conditional`).

M1 verifies `clm-consumer-surface-fallback` against the refusals-and-fallback page and rewrites `api_correlate`/`cannot_conclude` accordingly.
