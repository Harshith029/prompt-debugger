# Claude Code adapter

The v1 adapter: a Claude Code plugin exposing `analyze`, `rewrite`, and `history`.

## Layout

```
claude-code/
├── .claude-plugin/
│   ├── plugin.json            # plugin manifest
│   └── marketplace.json       # self-hosted marketplace entry
├── adapter-manifest.json      # Plugin/Adapter API conformance (pins contract versions)
├── skills/
│   ├── analyze/SKILL.md       # + evals/  (M0: frontmatter + workflow skeleton only)
│   ├── rewrite/SKILL.md       # + evals/
│   └── history/SKILL.md       # + evals/ + scripts/run.py launcher shim
└── core/                      # VENDORED copy of repo-root core/ (synced by tools/sync_plugin.py)
```

## Why `core/` is vendored (ADR-0008)

A Claude Code plugin is installed as a self-contained directory; it cannot reach up to a repository root. So the plugin vendors the versioned `core/` tree (contracts + knowledge). `tools/sync_plugin.py` copies repo-root `core/` here and `tools/check_plugin_sync.py` fails CI if the copy drifts — the repo root stays the single source of truth. The vendored copy is generated, and excluded from linting.

## Status at M0

Skill files contain frontmatter (with the corrected permission model — `disallowed-tools` for analyze/rewrite) and workflow skeletons that reference the vendored knowledge and contracts. **No analyzer or rewrite logic is authored yet** — that is M2–M4. The `history` launcher shim is present but the library it dispatches to is implemented in M2.
