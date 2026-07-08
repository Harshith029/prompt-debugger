# Documentation overview

Start here to navigate the project's documentation.

## For users

- [README](../README.md) — what the tool does, how to install and run, honest scope.
- [Privacy model](PRIVACY.md) — what is stored, where, and how to control it.
- [Ethics and use policy](ETHICS.md) — what the tool will and will not do, and why that is enforceable.

## For contributors

- [Contributor guide](../CONTRIBUTING.md) — setup, the local gate, the review workflow.
- [Architecture](ARCHITECTURE.md) — the full design (v0.2, post-review).
- [Architecture Decision Records](adr/README.md) — why the key decisions were made.
- [Data flow](DATAFLOW.md) — how a request moves through the system, with trust boundaries.
- [Glossary](GLOSSARY.md) — the project's vocabulary (used consistently by contract).

## The contracts (the real interfaces)

- [Contracts index](../core/contracts/README.md) — Prompt IR, Report JSON, Rewrite Report, Observable Event, Storage, Knowledge Engine, Plugin/Adapter API, Prompt Tree.
- [Knowledge Engine](../core/knowledge/README.md) — versioned data packs; the source of all guidance.

## Reviews and process

- [Compatibility policy](COMPATIBILITY.md) — versioning and support commitments.
- [Threat model](THREAT-MODEL.md) and the security process in [SECURITY.md](../SECURITY.md).
- [Roadmap](ROADMAP.md) — milestones and what's next.
- [Review dispositions](reviews/) — how independent-review findings were handled.
- [Prompt Tree design](design/prompt-tree.md) — the visualization data model for future adapters.
