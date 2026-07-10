# Tooling

Repository maintenance and CI enforcement scripts. All are stdlib-only except where a
script explicitly opts into the **dev-only** `jsonschema` package for instance validation.

| Tool | Purpose | Uses jsonschema? |
|---|---|---|
| [`validate_schemas.py`](validate_schemas.py) | Every `*.schema.json` parses and conforms to the contract subset; seed instances (knowledge, benchmarks, adapter manifest) validate against their schemas | optional; required in CI via `--require-jsonschema` |
| [`check_imports.py`](check_imports.py) | AST import allowlist for `src/prompt_debugger/` — enforces the stdlib-only, no-runtime-network policy (ADR-0006) | no |
| [`check_links.py`](check_links.py) | Relative markdown links in docs/contracts resolve to real files | no |
| [`check_versions.py`](check_versions.py) | All version-bearing files agree (manifests, pyproject, `__init__`, CHANGELOG heading); runs every PR | no |
| [`check_release_version.py`](check_release_version.py) | At release, plugin/marketplace/adapter versions match the git tag | no |
| [`sync_plugin.py`](sync_plugin.py) | Vendor repo-root `core/` into the Claude Code adapter (ADR-0008) | no |
| [`check_plugin_sync.py`](check_plugin_sync.py) | Fail if the vendored adapter `core/` has drifted from repo-root `core/` | no |

Run the full local gate:

```bash
python tools/check_versions.py
python tools/validate_schemas.py --require-jsonschema
python tools/check_imports.py
python tools/check_links.py
python tools/check_plugin_sync.py
python benchmarks/run.py validate
```
