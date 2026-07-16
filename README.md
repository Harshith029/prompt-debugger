# prompt-debugger

[![CI](https://github.com/Harshith029/prompt-debugger/actions/workflows/ci.yml/badge.svg)](https://github.com/Harshith029/prompt-debugger/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Status](https://img.shields.io/badge/status-pre--release%20(M1%20complete)-orange.svg)](#project-status)

**Understand what you can see. Improve what you can control.**

`prompt-debugger` is an open-source toolkit that helps you understand **observable** AI model behavior — visible safeguard messages, visible model switches, and user-visible errors — and improve your prompts using published prompt-engineering guidance. The first shipped surface is a [Claude Code](https://code.claude.com) plugin; the analysis engine is host-neutral by design.

> **Status: pre-release (Milestones M0 and M1 complete; M2 not started).** The engineering foundation — contracts, schemas, the knowledge engine, benchmarks, tooling, and CI — is in place and green; the claim registry is verified against live sources, the policy layer is authored and frozen, the taxonomy prose and pattern library are complete, and the knowledge snapshot is versioned (`2026.07-m1`). **Analyzer and rewrite functionality are not implemented yet** (Milestones M2–M4). This repository is being built in the open, milestone by milestone, with an independent review at every step. See [Project status](#project-status).

---

## Table of contents

- [Why this project exists](#why-this-project-exists)
- [Goals](#goals)
- [What it does](#what-it-does)
- [What it will never do](#what-it-will-never-do)
- [Architecture overview](#architecture-overview)
- [Repository structure](#repository-structure)
- [Installation](#installation)
- [Development workflow](#development-workflow)
- [Contributing](#contributing)
- [Privacy philosophy](#privacy-philosophy)
- [Project status](#project-status)
- [Roadmap and future milestones](#roadmap-and-future-milestones)
- [FAQ](#faq)
- [License](#license)

---

## Why this project exists

Sometimes a perfectly legitimate prompt gets an unexpected response: a safeguard message, or a visible switch to a different model. Anthropic's own documentation notes that safety classifiers can trigger on **benign adjacent work** — a security engineer, a life-sciences researcher, a teacher, or a developer can all run into this while doing entirely ordinary work.

When that happens, people are left guessing. They don't know what they actually observed, they can't tell which part of their prompt obscured their intent, and the internet fills the gap with folklore about "what the AI is really doing."

`prompt-debugger` exists to replace that guesswork with something honest:

- It explains what you **observed**, grounded only in public documentation, and never claims to know a provider's internal moderation or routing logic.
- It analyzes your prompt for the things that genuinely make intent hard to read — ambiguity, missing context, contradictions, and so on.
- It rewrites **legitimate** prompts to communicate that intent more clearly.

It is explicitly **not** a tool for getting around safety systems, and it is designed so it cannot quietly become one (see [What it will never do](#what-it-will-never-do)).

## Goals

- **Accuracy and honesty first.** Every explanation is either an observable fact (quoted, tied to documented behavior) or a clearly labeled estimate with a confidence level. No hidden-system claims, ever.
- **Genuinely useful prompt analysis.** A versioned, ten-dimension quality rubric mapped to Anthropic's published prompt-engineering techniques.
- **Local-first and private.** No accounts, no telemetry, no network calls. Your prompts stay on your machine.
- **Host-neutral and extensible.** A small, dependency-free core with thin adapters, so the same engine can back a Claude Code plugin today and other surfaces later.
- **Community-standard quality.** Strong typing, tests, CI, documentation, and an independent review at every milestone.

## What it does

1. **Explains observable events.** Paste the visible safeguard message, error, or model-switch notice you saw. It classifies the event against a documented taxonomy and separates **observed facts** from **estimated contributing factors**.
2. **Analyzes prompt quality** against a ten-dimension rubric: ambiguity, missing context, contradictions, scope creep, unrelated task bundling, poor formatting, excessive complexity, weak objectives, missing constraints, and missing output specification.
3. **Rewrites legitimate prompts** for clarity, structure, and explicit intent — preserving meaning, applying published techniques, and always stating that a rewrite does not guarantee a different response.
4. **Tracks history locally.** Save analyses, compare revisions, and export reports — redacted by default, with no data leaving your machine.

## What it will never do

- **Claim knowledge of a provider's internal systems.** It reports only what is observable and documented.
- **Rewrite a prompt to bypass or evade safety systems.** A specified legitimacy gate refuses circumvention requests, and the rewrite rules forbid intent-laundering (fabricated context, fictional reframing, semantic dilution, request-splitting, or encoding). A rewrite may make intent *more* explicit, never less.
- **Guarantee a different outcome.** Every rewrite carries a fixed notice that model behavior depends on the provider's systems and policies.
- **Send your data anywhere.** There is no network I/O in shipped code — enforced by CI, not just promised.

See [docs/ETHICS.md](docs/ETHICS.md) for the full use policy and why these boundaries are enforceable rather than aspirational.

## Architecture overview

The project is layered so that nothing important depends on a single host. Claude Code is **one adapter**, not the architecture.

```
Adapters (thin, host-specific)      Claude Code plugin  ·  [future: CLI, MCP, editors]
        │  read contracts / call the library
Core contracts (versioned)          schemas · event taxonomy · rubric · policy · claim registry
        │  validated / rendered by
Core library (stdlib-only)          storage · validation · verification · redaction · rendering
        │
Local storage (user-owned)          ~/.prompt-debugger/  (no network, ever)
```

Three ideas do most of the work:

- **The honesty architecture.** Every report structurally separates *Observed* (facts, quoted) from *Estimated* (hypotheses, confidence-labeled), with fixed epistemic and non-guarantee notices.
- **Knowledge as data, not code.** All prompt-engineering guidance lives in a versioned [Knowledge Engine](core/knowledge/README.md) where every factual claim is dated and linked to a public source. Analyzers query it; they never hardcode guidance.
- **Structured, verifiable output.** Analyses produce a canonical [Report JSON](core/contracts/report/CONTRACT.md); the Markdown you read is a rendered projection. Evidence quotes are verified as verbatim substrings of your prompt, so the tool cannot fabricate evidence undetectably.

The full design and the reasoning behind each significant decision live in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and the [Architecture Decision Records](docs/adr/README.md).

## Repository structure

| Path | Purpose |
|---|---|
| [`core/contracts/`](core/contracts/README.md) | Versioned, host-neutral contracts (schemas + prose) for Prompt IR, Report JSON, Rewrite Report, Observable Events, Storage, Knowledge Engine, Plugin API, Prompt Tree |
| [`core/knowledge/`](core/knowledge/README.md) | The Knowledge Engine: versioned data packs (rubric, techniques, event taxonomy, dated claim registry, pattern library) |
| [`src/prompt_debugger/`](src/prompt_debugger/__init__.py) | Host-neutral core library (Python ≥ 3.10, standard library only). Implemented in M2 |
| [`adapters/claude-code/`](adapters/claude-code/README.md) | The Claude Code plugin adapter — one adapter among possible many |
| [`benchmarks/`](benchmarks/README.md) | Nine-category prompt corpus + runner; corpus integrity is CI-enforced |
| [`evals/`](evals/README.md) | Semantic evaluation protocols (meaning preservation, red-team rewrite, rubric calibration) |
| [`tools/`](tools/README.md) | Repository tooling: schema validation, import policy, link check, plugin sync |
| [`tests/`](tests) | pytest suite: contract, policy, knowledge-integrity, and corpus tests |
| [`docs/`](docs/OVERVIEW.md) | Architecture, ADRs, data flow, glossary, threat model, privacy model, roadmap, compatibility policy |

## Installation

> The plugin does not perform analysis yet (that arrives in M2–M4). These instructions get you a working development checkout and, once behavior ships, an installable plugin.

### Requirements

- Python **3.10+** (runtime is standard-library only; no runtime dependencies)
- For plugin use: [Claude Code](https://code.claude.com)

### Development checkout

```bash
git clone https://github.com/Harshith029/prompt-debugger.git
cd prompt-debugger

python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

### Claude Code plugin (once behavior ships)

The adapter lives in [`adapters/claude-code/`](adapters/claude-code/README.md) and is self-contained (it vendors the core contracts and knowledge). Installation via the plugin marketplace will be documented in `docs/INSTALL.md` at Milestone M5.

## Development workflow

Run the full local gate before every change; CI runs the same on Windows, macOS, and Linux across supported Python versions.

```bash
ruff check . && ruff format --check .        # lint + format
mypy                                         # strict type-checking
python tools/check_versions.py               # version metadata agrees
python tools/validate_schemas.py --require-jsonschema
python tools/check_imports.py                # runtime is stdlib-only, no network
python tools/check_links.py                  # docs links resolve
python tools/check_plugin_sync.py            # vendored adapter core is in sync
python benchmarks/run.py validate            # corpus integrity
pytest                                        # contract + policy + corpus tests
```

If you edit anything under `core/`, run `python tools/sync_plugin.py` afterward to refresh the vendored adapter copy (CI enforces that it matches).

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) first — it covers setup, the local gate, and the non-negotiable principles (honesty over completeness, no bypassing, local-first, knowledge-in-the-engine, host-neutral core). All participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). Every milestone is validated against a fixed engineering review checklist before it's considered complete; substantial pull requests are held to the same standard.

Good first areas (as the project matures): expanding the benchmark corpus, improving documentation, and — from M1 onward — verifying and extending the Knowledge Engine's claim registry.

## Privacy philosophy

Your prompts are yours, and nothing leaves your machine. There are no accounts, no identifiers, no network calls, and no telemetry anywhere in the codebase — and this is *enforced*, not just stated: shipped code passes an AST import check that forbids network modules, and the test suite runs with sockets blocked.

Nothing is persisted unless you explicitly save it. Saved records are redacted by default; storing raw prompt text is rare, requires per-save confirmation, and is reversible. Storage is user-local by default so history can't be accidentally committed to a repository. The complete data-lifecycle account, including the honest limits of pattern-based redaction, is in [docs/PRIVACY.md](docs/PRIVACY.md).

## Project status

**Pre-release. Milestone M0 (engineering foundation) and Milestone M1 (knowledge verification and policy authoring) are complete; Milestone M2 has not started.** What exists today:

- Eight versioned, host-neutral contracts with JSON schemas and prose specifications, plus three additive knowledge schemas for the policy files.
- The Knowledge Engine with a **verified claim registry** (every claim checked against its live source, with dates), a complete observable-event taxonomy, the authored provider-neutral policy layer (misuse policy, rewrite policy, fixed notices) — frozen after independent review — and a complete pattern library (one before/after pattern per rubric dimension), all versioned as the `2026.07-m1` snapshot.
- A nine-category benchmark corpus, the full tooling and CI suite, and a passing test suite.
- Complete architecture documentation, including nine Architecture Decision Records.

What does **not** exist yet: the analyzer, the rewriter, and the storage implementation. Those are Milestones M2–M4. This is deliberate — the foundation is built and reviewed before any feature logic.

## Roadmap and future milestones

| Milestone | Focus | State |
|---|---|---|
| **M0** | Engineering foundation: repo, contracts, knowledge engine, benchmarks, tooling, CI, docs | **complete** |
| M1 | Knowledge verification: verify every claim against its source, author the misuse policy + rewrite rules + notices, expand the taxonomy, populate the pattern library | **complete** — released as `v0.2.0-alpha`; record: [docs/releases/M1.md](docs/releases/M1.md) |
| M2 | Core library: storage, schema validation, evidence verification, redaction, rendering, CLI | planned |
| M3 | `analyze` + `rewrite` skills; trigger, adversarial, meaning-preservation, and rubric-calibration evals | planned |
| M4 | `history` skill; privacy verifications | planned |
| M5 | Docs, examples, packaging, release-trust pipeline; cross-OS install tests | planned |
| M6 | Final security/privacy review; **v1.0.0** | planned |

Post-v1 ideas (MCP/CLI adapters, a Prompt Tree visualizer, template libraries) are in [docs/ROADMAP.md](docs/ROADMAP.md).

## FAQ

**Does this help me get around safety filters?**
No. It refuses that by design. Its purpose is the opposite: to help legitimate prompts communicate legitimate intent clearly. See [docs/ETHICS.md](docs/ETHICS.md).

**Does it know why my prompt was flagged?**
No — and it will never pretend to. It explains what you *observed* using documented behavior, and separately offers clearly-labeled *estimates* about what in your prompt might have made your intent hard to read. Provider internals are not public, and the tool says so.

**Does it send my prompts anywhere?**
No. There is no network I/O in shipped code, enforced by CI and tests. Everything runs locally.

**Can I use it today?**
You can explore the architecture, contracts, and knowledge engine, and run the full development gate. The analysis and rewrite features are not implemented yet — see [Project status](#project-status).

**Is it only for Claude?**
The first adapter targets Claude Code, and the initial knowledge pack covers Anthropic's documented behavior. The core is host- and provider-neutral by design: new providers are new knowledge packs, and new surfaces are new adapters, with no changes to the core.

**Why is there so much structure for a pre-release project?**
Because the goal is a community standard, not a proof of concept. The foundation — versioned contracts, a knowledge engine, enforced privacy, and independent review — is the hard part, and it's built first on purpose.

**Can I contribute even though features aren't built yet?**
Yes. Documentation, benchmark cases, and (from M1) knowledge-registry verification are all valuable now. See [Contributing](#contributing).

## License

[MIT](LICENSE) © The prompt-debugger contributors
