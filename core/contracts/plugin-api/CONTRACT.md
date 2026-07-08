# Contract: Plugin / Adapter API (v1)

**Purpose.** Defines what any host adapter (Claude Code plugin, future CLI UX, future MCP server, future editors) must consume and produce so that every host behaves identically where it matters. Claude Code is **one adapter among possible many** — nothing in `core/` or `src/` may reference a specific host. (ADR-0003.)

## An adapter MUST

1. **Declare itself** with an `adapter-manifest.json` conforming to [`adapter-manifest.schema.json`](adapter-manifest.schema.json), pinning the contract versions it consumes.
2. **Produce Report JSON** conforming to the Report contract (including composite parts) for every analysis it performs, regardless of how it renders results to its host.
3. **Source all guidance from the Knowledge Engine.** No rubric text, technique text, taxonomy fact, notice text, or policy rule may be hardcoded in adapter files; adapters read pack content (or its `.md` companions).
4. **Enforce the honesty architecture**: Observed vs Estimated separation, confidence labels on estimates, fixed notices from the knowledge pack, `unknown` event handling.
5. **Enforce the legitimacy gate** as specified by the misuse policy (M1 knowledge content) and record the outcome in `rewrite.gate`.
6. **Persist only through the storage API** (library CLI). Adapters never write store files directly, and never persist without explicit user action.
7. **Respect privacy defaults**: no network I/O, redaction before persistence, raw saves gated on per-save confirmation.

## An adapter MAY

- Render Markdown its own way (the Report is canonical; rendering is a projection).
- Offer host-native affordances (slash commands, tool pre-approval, visualizations such as the Prompt Tree).
- Ship host-specific packaging (the Claude Code adapter vendors a copy of `core/` — see ADR-0008).

## An adapter MUST NOT

- Claim knowledge of provider internals beyond taxonomy entries.
- Extend or reinterpret the transformation rules of the rewrite contract.
- Introduce runtime dependencies into `core/` or `src/`.

## Versioning

`adapter_api_version` is the version of *this* contract. Adapters pin the exact contract versions they consume in `consumes`; CI checks the shipped Claude Code adapter manifest against the contract versions present in the repo.
