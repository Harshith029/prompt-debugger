# ADR-0005: No browser extension in v1

- **Status:** Accepted
- **Date:** 2026-07-07

## Context

The original brief asked whether a browser extension is appropriate. An extension could, in principle, read conversations on a provider's web UI and surface observable events automatically.

## Decision

**No browser extension in v1.** Observable evidence enters the tool through a structured paste protocol: the user provides the visible message, error, or model-switch notice they already see.

## Alternatives considered

- **Ship an extension that scrapes the web UI DOM.** Rejected on three grounds:
  1. **No honest data source.** A scraper reads an undocumented, unstable DOM — the opposite of the project's grounding in observable, documented facts.
  2. **Largest privacy surface, smallest gain.** Read access to conversations is the biggest possible privacy exposure; the user already possesses the evidence the tool needs.
  3. **The paste protocol is strictly better.** It captures the same evidence with zero background access, and consent is inherent in the act of pasting.

## Trade-offs

- Slightly more user effort (paste vs automatic capture). Accepted as the correct trade for honesty and privacy.

## Consequences

- The entire product is local-first with no browser permissions.
- Reconsideration is gated: an extension returns to the roadmap only if an official, documented client API exposes observable events programmatically, and it would require its own security and privacy review.
