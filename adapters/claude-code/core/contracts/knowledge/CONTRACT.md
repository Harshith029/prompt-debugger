# Contract: Knowledge Engine (v1)

**Purpose.** The Knowledge Engine separates *prompt-engineering knowledge* from *implementation*. Analyzers, rewriters, and adapters never hardcode guidance; they query versioned **data packs**. This is what makes the product auditable (every rule traces to a dated public source), updatable (provider docs change → pack version bumps, no code change), and extensible (future providers are new packs, not new code). See ADR-0007.

## Structure

```
core/knowledge/
├── manifest.json                 # manifest.schema.json — knowledge_version + pack index
└── packs/
    ├── common/                   # provider-neutral methodology
    │   ├── pack.json             # pack.schema.json
    │   ├── rubric.json           # rubric.schema.json — R-dimensions
    │   ├── rubric.md             # prose companion (human/model reading)
    │   ├── misuse-policy.json    # misuse-policy.schema.json — legitimacy classification
    │   ├── misuse-policy.md      # prose companion
    │   ├── rewrite-policy.json   # rewrite-policy.schema.json — transformation rules + guarantees
    │   ├── rewrite-policy.md     # prose companion
    │   ├── notices.json          # notices.schema.json — fixed notice texts
    │   └── notices.md            # prose companion
    └── anthropic/                # provider pack
        ├── pack.json
        ├── claims.json           # claims.schema.json — dated claim registry
        ├── techniques.json       # techniques.schema.json — T-techniques
        ├── techniques.md
        ├── events.json           # events.schema.json — observable-event taxonomy
        ├── events.md
        └── patterns/
            └── index.json        # patterns-index.schema.json — pattern library index
```

Machine-readable files are **JSON, not YAML** (the runtime is stdlib-only; YAML parsing is not). Every `.json` knowledge file has a schema in this directory and is validated in CI. Prose `.md` companions carry the same ids so humans and models read the same knowledge the machines validate.

## The provenance chain

```
observation (user evidence)
  → taxonomy entry (events.json, id evt-*)
    → claims (claims.json, id clm-*, with URL + retrieval date + verification status)
      → public documentation
```

Techniques and rubric dimensions link into the same claim registry via `source_claims`. **Nothing in a pack may assert provider behavior without a claim id.**

## Versioning

- `manifest.json` carries `knowledge_version` (e.g. `2026.07-m1`) covering the whole corpus snapshot.
- Each pack carries `pack_version`; each file carries a format version as an integer. Most files spell it `file_version`; the `common`-pack **policy** files (`misuse-policy`, `rewrite-policy`, `notices`) spell it `schema_version` and additionally carry `policy_version` (content version) — schema evolution and policy evolution are independent axes for these files. See [policy-schemas.md](../../../docs/design/policy-schemas.md).
- Reports pin `knowledge.knowledge_version`, `provider`, `rubric_version`, and (when a policy corpus was loaded) `policy_version`, so any report is reproducible against the knowledge and policy that produced it.
- Claims have lifecycle `recorded → verified → stale → retired`; a quarterly re-verification checklist (issue template) drives transitions. `verified` is the citable state: an `active` taxonomy entry or technique must not cite a non-`verified` claim (KN-2), and taxonomy entries cite only `verified` claims regardless of their own status (KN-7).

## Query model (implemented M2, contract now)

The library exposes read-only accessors: `load_manifest()`, `load_pack(provider)`, `technique(id)`, `rubric_dimension(id)`, `event_entry(id)`, `claims(status=...)`. Adapters consume file paths (skills read the `.md` companions) or accessor output; nobody parses knowledge ad hoc.

## Future providers

A new provider = a new pack directory conforming to these schemas (own claims, techniques, events). The `common` pack stays provider-neutral; anything provider-specific found in `common` is a bug.
