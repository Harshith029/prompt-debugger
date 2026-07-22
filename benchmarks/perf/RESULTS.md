# Storage performance measurements (M2 FR-11)

Recorded measurements from the timing harness ([`harness.py`](harness.py)) and the
size-warning threshold derived from them (open choice O6; ARCHITECTURE §9).
Timings are machine-dependent; this file records **actual measured runs** on the
reference machine (CPython 3.11, Windows). CI runs the same procedure on the
Linux / macOS / Windows × Python 3.10 / 3.12 matrix (`harness.py validate` for
correctness, `harness.py measure --sizes 10000,100000` for the timing procedure).

## What was measured

- **Generator:** `generate_store(home, project, n)` writes `n` synthetic,
  composite-schema-valid, PR-1-valid history records to a temporary store.
- **Operations timed:** `list`, `get`, `trends` — the routine read paths. All
  three share the storage layer's `_read_records` scan, which reads the JSONL
  file and **composite-schema-validates every record** on every read (records
  are untrusted input — threat S10, enforced in FR-5). This validate-and-parse
  scan is the dominant O(n) cost.

## Methodology

- **Small sizes (1k–10k): median of 5 repeats.** These are stable and
  repeatable, and are the basis for the threshold derivation below.
- **Large sizes (50k, 100k): a single repeat, run twice.** At these sizes a
  single scan costs tens of seconds to minutes, so many repeats are impractical;
  two independent single-repeat runs are recorded instead. The large-size numbers
  are **noise-dominated observations, not point estimates** — the two runs differ
  by up to ~2–3× (e.g. 100k `trends`: 178 s vs 476 s), reflecting memory/GC
  pressure and shared-machine load at these sizes. They are reported **exactly as
  observed, without averaging.**

## Small-size measurements (median of 5 repeats, milliseconds)

| records | list (ms) | get (ms) | trends (ms) |
|--------:|----------:|---------:|------------:|
|   1,000 |     621.5 |    632.2 |       621.8 |
|   2,000 |   1,280.2 |  1,246.2 |     1,235.1 |
|   5,000 |   3,133.0 |  3,139.2 |     3,124.9 |
|  10,000 |   6,378.7 |  6,288.8 |     6,498.6 |

Clean linear fit in this region: **≈ 0.63 ms/record**.

## Large-size measurements (single repeat, two runs, seconds)

| records | run | list (s) | get (s) | trends (s) |
|--------:|:---:|---------:|--------:|-----------:|
|  50,000 |  1  |    132.4 |    92.3 |       96.7 |
|  50,000 |  2  |     66.4 |    84.7 |      118.0 |
| 100,000 |  1  |    180.6 |   183.4 |      178.2 |
| 100,000 |  2  |    188.4 |   229.5 |      476.0 |

**Measured, not extrapolated.** A naive linear projection of the 0.63 ms/record
small-size fit would predict 50k ≈ 32 s and 100k ≈ 63 s. The **actual** figures
are far worse — 50k reads take ~1–2 minutes and 100k reads take ~3 minutes (up to
~8 minutes for one 100k `trends` sample) — because the scan degrades
super-linearly at scale. The earlier extrapolation understated the cost by ~3–8×;
these actual measurements replace it, per the observed data rather than the fit.

## Observed scaling and its cause

In the small-size region the read scan is linear at ≈ 0.63 ms/record, dominated
by per-record composite schema validation: `schema.validate_history_record`
re-reads and re-parses the contract schema files from disk on every call (see
`schema.py`), so an `n`-record read performs `O(n)` schema (re)loads. At large
sizes, building tens of thousands of parsed records adds memory/GC pressure (on
top of the O(n log n) id sort), and the scan degrades super-linearly with high
run-to-run variance. This is the shipped behavior of the frozen FR-1 validator
and the FR-5 fail-closed read path; it is **not changed here** (FR-11 measures;
it does not optimize frozen modules). The inefficiency is flagged for a future,
separately-approved optimization pass — it does not affect the correctness of any
operation.

## Derived size-warning threshold (`size_warn_records`)

**Criterion.** The threshold marks where a routine full-history read crosses the
**1-second interactive-responsiveness boundary** (the canonical HCI limit beyond
which a command no longer feels prompt) — the point at which archiving the store
becomes worthwhile. The record count comes from the measurement, not from
opinion (O6); the 1-second bound is a standard, named figure, not a guess. It is
derived from the stable small-size linear region (the large-size numbers are too
noisy to derive from, and are well past the bound regardless).

**Value.** At the measured ≈ 0.63 ms/record, a `list` scan reaches 1 second at
≈ 1,600 records. The largest round number (1–2–5 series) whose scan stays at or
under that bound is **1,000** (1,000 → ≈ 0.62 s; 2,000 → ≈ 1.28 s already
exceeds it). This coincides with — and is independently vindicated by — the
config schema's own `minimum` of 1,000.

**What it replaces.** The previous default was a guessed **50,000**. The
measurements show a routine read scan at 50,000 records already takes **on the
order of a minute or more** (list: 66–132 s across the two runs) — orders of
magnitude past any interactive-responsiveness bound. The default is therefore set
to the measured **1,000** in both the config schema
(`core/contracts/storage/config.schema.json`) and the library's runtime defaults
(`src/prompt_debugger/store.py`).

## Reproducing

```
python benchmarks/perf/harness.py validate                       # CI smoke (correctness)
python benchmarks/perf/harness.py measure --sizes 1000,2000,5000,10000 --repeats 5
python benchmarks/perf/harness.py measure --sizes 50000,100000 --repeats 1
```
