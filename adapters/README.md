# Adapters

Host adapters bind the host-neutral core (`core/` contracts + `src/prompt_debugger/` library) to a specific environment. **Claude Code is one adapter, not the architecture** (ADR-0003). Every adapter obeys the [Plugin/Adapter API contract](../core/contracts/plugin-api/CONTRACT.md).

| Adapter | Host | Status |
|---|---|---|
| [`claude-code/`](claude-code/) | Claude Code plugin | v1 (skills scaffolded in M0; analyzer/rewrite behavior authored M2–M4) |
| _cli_ | Standalone terminal UX | roadmap |
| _mcp_ | MCP server | roadmap (v1.3) |

## Rules

- An adapter contains **only** host-specific glue: packaging, invocation surface (slash commands), rendering, and a vendored copy of `core/` where the host requires self-containment (ADR-0008).
- No adapter hardcodes rubric/technique/taxonomy/notice/policy content — all of it comes from the Knowledge Engine.
- No adapter reaches into storage files directly; it calls the library CLI.
- Adding an adapter never edits `core/` or `src/`.
