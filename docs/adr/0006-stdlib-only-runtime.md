# ADR-0006: Stdlib-only runtime, no runtime network I/O

- **Status:** Accepted
- **Date:** 2026-07-07

## Context

The shipped core library runs wherever the adapter runs, including environments with no package installation. Skill best-practice guidance warns against assuming installed packages. The product is also local-first with a hard privacy promise of no telemetry.

## Decision

The runtime library (`src/prompt_debugger/`) uses the **Python standard library only** and performs **no runtime network I/O**. Development-time tools (pytest, ruff, mypy) and one CI helper (`jsonschema`, for differential schema validation) are dev-only dependencies, never imported by shipped code.

Enforcement is behavioral, not aspirational:
- `tools/check_imports.py` (AST) fails if any shipped module imports outside a stdlib allowlist or touches a network/exec denylist (`socket`, `urllib`, `http`, `subprocess`, `ctypes`, …).
- The test suite runs with `socket.socket` replaced by a raising stub (`tests/conftest.py`), so any accidental socket use fails the suite.

## Alternatives considered

- **Allow a curated runtime dependency set (e.g. pydantic, jsonschema at runtime).** Rejected: every runtime dependency is a supply-chain and install-failure surface; the review (F5) specifically flagged the stdlib/jsonschema tension. A defined schema subset + a small in-repo validator (M2) removes the need.
- **Grep-based network gate (v0.1).** Rejected per F12 as naive (misses `subprocess`, false positives). Replaced by the AST allowlist plus the runtime socket-block harness.

## Trade-offs

- We own a ~150-line JSON-Schema-subset validator instead of taking `jsonschema` at runtime. Bounded by differential testing against real `jsonschema` in CI.
- The schema subset is deliberately restricted (no `$ref`, `anyOf`, recursion), which shapes how contracts are authored (composite validation instead of `$ref`).

## Consequences

- Zero runtime supply chain; the library installs and runs anywhere Python ≥ 3.10 exists.
- The no-network promise is enforced by tooling and tests, not just documented.
- Schema authors follow the subset (CI meta-check enforces it).
