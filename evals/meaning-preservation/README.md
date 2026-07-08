# Meaning-preservation suite

**Question it answers:** does a rewrite preserve the user's intent, or does it drift?

**Protocol (implemented M3):**
1. Take paired (original, rewritten) prompts — from `analyze`/`rewrite` runs over benchmark corpus cases whose `rewrite_expected` is true.
2. An LLM judge scores intent-equivalence against a fixed rubric; a human spot-checks a sample each release.
3. Golden rewrites are stored as snapshots; a regression is any snapshot whose judged equivalence drops below threshold.

**Invariant under test:** a rewrite may make intent *more* explicit, never less, and never introduces facts the user didn't supply (the rewrite contract).

At M0 this directory defines the protocol only; no fixtures yet.
