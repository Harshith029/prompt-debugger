# ADR-0010: Truncation kind re-deferred at the M2 contract review

- **Status:** Accepted
- **Date:** 2026-07-20

## Context

[ADR-0009](0009-truncation-observables-deferred.md) recorded the truncation
knowledge as a verified claim (`clm-stop-reasons`) without adding a taxonomy
entry or a `kind` member, and obligated M2's contract review to "explicitly
revisit this ADR and either add the kind or re-defer with reasons"
(specs/M2.md FR-9 — the only path by which M2 may touch a frozen contract or
the taxonomy, bounded to exactly that change and executable only after
explicit approval as a contract evolution).

This ADR is that revisit. The facts at review time:

1. **ADR-0009's own end-condition is not met.** It deferred the kind "to the
   first milestone where the analyzer needs to *classify* truncation". M2's
   approved scope contains no analyzer — analyzer and rewrite behavior are M3
   (specs/M2.md Non-goals; §Transition to M3). No consumer of a truncation
   classification exists at M2's end, exactly as at M1's.
2. **The granularity question is still undecidable.** ADR-0009 rejected
   choosing the member name and granularity ahead of real classification needs
   as speculative generalization. `clm-stop-reasons` documents seven stop
   values; whether the analyzer needs one `stop_condition` kind, a
   truncation-only kind, or per-stop-reason kinds is knowable only once the
   analyzer's OBSERVE step is authored (M3).
3. **A correction to ADR-0009's cost framing.** ADR-0009 stated that growing
   the `kind` enum is "additive for readers … no migration debt". The frozen
   Observable Event contract's own compatibility rule says otherwise: "Adding
   a `kind` member is a version bump (consumers switch on it); the `unknown`
   member exists precisely so bumps are rare." Exercising the FR-9 exception
   in M2 would therefore be a v1→v2 contract evolution — `event_version`,
   composite validation, verifier rules, fixtures, `CONTRACT_VERSIONS`, and
   the adapter manifest all move — for a kind no component consumes.
   (specs/M2.md's "one additive `kind` enum member" describes the shape of the
   edit; the contract's compatibility rule governs its versioning cost.)
4. **The honesty path already serves truncation reports.** The contract
   mandates `kind: "unknown"` with `documented_match: null` when no taxonomy
   entry matches, as a first-class outcome; `evt-user-visible-error.
   cannot_conclude` states the truncation-vs-error boundary with its citation,
   and `clm-stop-reasons` is verified and available for documented explanation
   prose. Nothing is silently mis-classified in the interim.

## Decision

**Re-defer.** M2 adds no `kind` member and no taxonomy entry; no contract,
schema, or taxonomy change occurs in M2. The deferral is renewed under
concrete terms:

- The kind (and its taxonomy entry) is added by the milestone that authors the
  analyzer's classification behavior (M3 on the current roadmap), **if and
  only if** that milestone demonstrates the analyzer needs to classify
  truncation distinctly from `unknown` — i.e., a real consumer exists.
- That milestone's review must revisit this ADR explicitly and record its
  outcome either way; **silence is not an outcome** (the FR-9 discipline is
  inherited).
- If taken, the change is executed as an approved contract evolution: a
  version bump per the Observable Event contract's compatibility rule, with
  the member granularity chosen from the analyzer's demonstrated needs, plus
  the taxonomy entry, tests, and knowledge snapshot bump.

## Alternatives considered

- **Add the kind now, under the FR-9 carve-out.** Rejected: the criterion
  ADR-0009 set (an analyzer that needs the classification) is unmet — M2 built
  the deterministic library, not the analyzer — so the addition would fix the
  member granularity without the information ADR-0009 said the choice needs,
  and would spend a rare contract version bump on an unconsumed kind.
- **Shoehorn truncation under `error`.** Still rejected for ADR-0009's reason:
  the source documents truncation as a property of a *successful* response;
  the taxonomy would misstate its own source.
- **Defer silently / drop the question.** Rejected: FR-9 requires the decision
  recorded either way, and this ADR carries that obligation forward to M3.

## Trade-offs

Truncation reports continue through the honest-but-generic `unknown` path
until an analyzer exists to consume a first-class classification. Accepted:
that path is contract-mandated and designed for exactly this case, and the
alternative buys no user-visible capability in M2 while consuming a contract
version bump the compatibility rule says should be rare.

## Consequences

- The M2 scope stays fully closed: FR-9's carved-out exception goes unused,
  and no frozen artifact changes in M2.
- `clm-stop-reasons` remains verified and cited (`evt-refusal-visible`,
  `evt-api-refusal-stop-reason`, `evt-user-visible-error`); the events prose
  companion keeps documenting the two families (HTTP errors vs. stop
  conditions) so adapters do not conflate them in the interim.
- The M3 specification must contain the explicit revisit obligation this ADR
  carries forward, with the consumer-exists criterion above.
- ADR-0009's status becomes "Superseded by ADR-0010": its M1 decision stands
  historically, but its expectation ("expected at M2 contract review") and its
  compatibility framing ("no migration debt") are corrected here.
