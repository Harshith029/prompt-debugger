# Rubric-calibration suite

**Question it answers:** does the analyzer detect the issues that are actually present, without over-flagging healthy prompts?

**Protocol (implemented M3):**
1. Prompts with planted, labeled issues (drawn from and extending the `benchmarks/` corpus, whose cases carry `likely_dimensions`).
2. Run `analyze`; compare detected dimensions to the planted labels.
3. Track **precision and recall per rubric dimension**, release over release, to catch drift in either direction (missed issues or false positives on good prompts).

**Why it matters:** the `good` benchmark category exists precisely to keep the analyzer from crying wolf; this suite quantifies that. At M0 the protocol is defined; scoring harness lands in M3.
