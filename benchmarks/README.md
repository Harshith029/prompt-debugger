# Benchmark Suite

A versioned corpus of prompts across nine categories, plus a runner. It exists from M0 so that analyzer/rewrite work (M2+) is measured against a fixed, reviewable baseline rather than ad-hoc examples. **Corpus integrity is CI-enforced** (`python benchmarks/run.py validate` runs on every PR).

## Categories

| Category | Directory | What it probes |
|---|---|---|
| Good prompts | `corpus/good/` | Well-formed prompts; the analyzer should find few or no issues (guards against false positives) |
| Poor prompts | `corpus/poor/` | Multiple clear defects; the analyzer should find them |
| Ambiguous prompts | `corpus/ambiguous/` | R1-heavy; vague referents and undefined terms |
| Coding prompts | `corpus/coding/` | Software tasks; domain-specific clarity and constraints |
| Research prompts | `corpus/research/` | Investigation tasks; success criteria and source expectations |
| Creative prompts | `corpus/creative/` | Open-ended generation; where under-specification is sometimes fine |
| Educational prompts | `corpus/educational/` | Teaching/explanation tasks; audience and level |
| Long-context prompts | `corpus/long-context/` | Ordering of data vs question; quote grounding |
| Multi-step prompts | `corpus/multi-step/` | Decomposition, sequencing, R4/R5 scope issues |

## Case format

Each case is one JSON file conforming to [`benchmark-case.schema.json`](benchmark-case.schema.json):

- `id`, `category`, `prompt` — the input.
- `event` — optional observable event the case simulates (for event-explanation cases).
- `expectations` — reviewable, coarse-grained expectations (dimensions likely present, whether a rewrite is expected, whether the gate should decline). **Expectations are guidance for human review and regression tracking, not hard assertions in M0** — the analyzer does not exist yet. M3+ wires cases into the semantic eval suites (`evals/`).
- `notes` — rationale for the case.

## Runner

```bash
python benchmarks/run.py validate     # schema + integrity checks (CI)
python benchmarks/run.py list         # list cases by category
python benchmarks/run.py stats        # counts per category
```

The `run` subcommand (execute cases through an adapter and score against expectations) is added in M3 when there is an analyzer to run. At M0 the runner validates and inventories the corpus only.

## Relationship to `evals/`

Benchmarks are the **corpus**; `evals/` holds the **semantic test protocols** (meaning-preservation, red-team rewrite, rubric calibration) that consume corpus cases at release gates. Keeping them separate lets the corpus grow without entangling it with model-in-the-loop scoring.
