# Architecture Decision Records

Each ADR captures one significant decision: its context, the decision, alternatives, trade-offs, and consequences. ADRs are immutable once accepted; a superseding decision gets a new ADR that references the old one.

| ADR | Title | Status |
|---|---|---|
| [0001](0001-prompt-ir-not-ast.md) | Prompt IR instead of a full Prompt AST | Accepted |
| [0002](0002-report-json-canonical.md) | Report JSON is canonical; Markdown is a rendered view | Accepted |
| [0003](0003-host-neutral-core.md) | Host-neutral core with thin adapters | Accepted |
| [0004](0004-storage-default-user-local.md) | Default storage is user-local | Accepted |
| [0005](0005-no-browser-extension.md) | No browser extension in v1 | Accepted |
| [0006](0006-stdlib-only-runtime.md) | Stdlib-only runtime, no runtime network I/O | Accepted |
| [0007](0007-knowledge-engine.md) | Knowledge Engine of versioned data packs | Accepted |
| [0008](0008-vendored-core-in-plugin.md) | Vendor core/ into the Claude Code plugin | Accepted |

Template: [`_template.md`](_template.md).
