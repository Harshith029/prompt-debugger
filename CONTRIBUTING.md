# Contributing

Thanks for helping build `prompt-debugger`. This project aims to be a community standard, which means a high bar for accuracy, honesty, and maintainability. Please read this before opening a PR.

## Principles (non-negotiable)

- **Honesty over completeness.** The tool explains only observable facts and clearly labels estimates. Never add code or content that claims knowledge of a provider's internal moderation or routing logic.
- **No bypassing.** Nothing may weaken the legitimacy gate or the rewrite transformation rules. See [docs/ETHICS.md](docs/ETHICS.md).
- **Local-first, no telemetry.** Shipped code performs no network I/O. Ever.
- **Knowledge belongs in the Knowledge Engine**, not in code or skill prose.
- **Contracts are versioned and additive.** Breaking a contract requires a version bump and a changelog entry.

## Setup

```bash
python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## The local gate (run before every PR)

```bash
ruff check . && ruff format --check .
mypy
python tools/validate_schemas.py --require-jsonschema
python tools/check_imports.py
python tools/check_links.py
python tools/check_plugin_sync.py
python benchmarks/run.py validate
pytest
```

CI runs the same gate on Windows, macOS, and Linux across supported Python versions. All must be green.

## Working with the pieces

- **Editing `core/` (contracts or knowledge):** run `python tools/sync_plugin.py` afterward to refresh the vendored adapter copy, or CI's plugin-sync check will fail. Any provider statement needs a `clm-*` claim id.
- **Editing schemas:** stay within the documented subset (`core/contracts/README.md`); the subset meta-check and differential validation enforce it.
- **Editing skills:** the frontmatter permission profile is contract-tested (`tests/test_frontmatter.py`); changes there must be intentional and match the documented profile.
- **Adding benchmark cases:** one JSON file per case under `benchmarks/corpus/<category>/`, conforming to the case schema; `benchmarks/run.py validate` checks it.
- **Runtime code (`src/`):** standard library only. If you think you need a dependency, you almost certainly don't — open an issue first.

## The review workflow

Every milestone is validated against a fixed engineering review checklist before it is considered complete, and no milestone closes with open accepted findings. Substantial pull requests are held to the same standard: correctness, security, privacy, edge cases, maintainability, documentation, and tests.

## Commits and PRs

- Keep commits focused; write clear messages.
- Update `CHANGELOG.md` under `[Unreleased]` for anything user- or contract-facing.
- Update or add tests for any behavior change.
- Update docs when you change behavior, contracts, or knowledge.

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
