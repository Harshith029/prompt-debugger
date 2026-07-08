# Semantic evaluation suites

These are the **model-in-the-loop** quality gates that run at releases (not per-PR), distinct from the deterministic tests in `tests/` and the corpus in `benchmarks/`. They exist as structure at M0; their harnesses are implemented alongside the skills they test (M3+).

| Suite | Directory | Verifies | Gate |
|---|---|---|---|
| Meaning preservation | [`meaning-preservation/`](meaning-preservation/README.md) | Rewrites preserve intent; snapshot regressions on golden rewrites | release |
| Red-team rewrite | [`red-team-rewrite/`](red-team-rewrite/README.md) | Laundering / bypass attempts produce `gate: declined` | release |
| Rubric calibration | [`rubric-calibration/`](rubric-calibration/README.md) | Planted-issue prompts are detected; precision/recall tracked per release | release |

## Why separate from `tests/` and `benchmarks/`

- `tests/` are deterministic and run on every PR (fast, no model).
- `benchmarks/` is the reusable prompt **corpus** (data).
- `evals/` holds **protocols** that feed corpus cases through an adapter and score the model's output. They are slower, cost model calls, and run at release gates. Keeping them separate lets the corpus grow freely and keeps PR CI fast and deterministic.
