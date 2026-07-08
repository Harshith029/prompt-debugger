# Glossary

Terms used consistently across this project. Consistent terminology is a contract-level requirement, not a style preference.

| Term | Definition |
|---|---|
| **Adapter** | Host-specific glue binding the core to one environment (e.g. the Claude Code plugin). One of possibly many; never the architecture itself. |
| **Claim** | A single dated, sourced statement about provider behavior, stored in the claim registry with a URL, retrieval date, and verification status. |
| **Claim registry** | The versioned list of claims (`claims.json`) that grounds every factual statement the tool makes. |
| **Contract** | A versioned, host-neutral interface (schema + prose) that adapters, tools, and tests bind to. |
| **Core** | The host-neutral layers: contracts (`core/`) and the library (`src/prompt_debugger/`). |
| **Estimated (layer)** | The part of a report holding hypotheses about contributing factors, each with a confidence label. Never stated as fact. |
| **Event taxonomy** | The versioned catalog of observable events, each with what the user sees and what can/cannot be concluded. |
| **Fingerprint** | A per-store salted HMAC of a prompt, used for local revision matching. Never exported by default; not a plaintext hash. |
| **Gate (legitimacy gate)** | The decision procedure that determines whether a rewrite is offered, refused, or conditional. |
| **Honesty architecture** | The design that structurally separates Observed facts from Estimated hypotheses and attaches fixed notices. |
| **Knowledge Engine** | The system of versioned data packs holding all prompt-engineering knowledge, separate from implementation. |
| **Observable event** | Something the user can actually see: a visible safeguard message, a visible model switch, a user-visible error. |
| **Observed (layer)** | The part of a report holding facts: the user's verbatim evidence classified against the taxonomy. |
| **Pack** | A versioned unit of knowledge: `common` (provider-neutral) or a provider pack (e.g. `anthropic`). |
| **Prompt IR** | A pragmatic intermediate representation: ordered, typed, verbatim segments of a prompt. Not an AST. |
| **Prompt Tree** | A visualization-oriented projection of the Prompt IR into seven fixed sections. Derived, never authoritative. |
| **Provenance chain** | observation → taxonomy entry → claim → public URL: how every explanation is made auditable. |
| **Report JSON** | The canonical machine-readable result of an analysis; the system of record. Markdown is a projection of it. |
| **Rewrite contract** | The rules defining what a rewrite may and may not do (allowed vs prohibited transformations). |
| **Rubric** | The versioned ten-dimension prompt-quality rubric (R1–R10). |
| **Store** | One project's local history directory, holding `history.jsonl`, a salt, rejects, and archives. |
| **Technique** | A prompt-engineering technique (T1–T10) grounded in one or more claims; the fixes findings map to. |
| **Transformation rules** | The allowed/prohibited operation lists inside the rewrite contract; the anti-laundering boundary. |
| **Unknown (event kind)** | The mandated graceful-degradation classification for observations matching no documented pattern. |
| **Vendored core** | The generated copy of `core/` inside the Claude Code adapter, kept byte-identical to the source by CI. |
