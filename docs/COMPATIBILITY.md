# Compatibility policy

## Supported runtimes

| Axis | Support |
|---|---|
| Python | ≥ 3.10 (runtime is standard-library only) |
| OS | Windows, macOS, Linux — all first-class, all in CI |
| Claude Code | Minimum version stated in each release's notes once the adapter ships behavior (M3+) |

## Launchers

Scripts are invoked with the first available of `python3`, `python`, `py -3` (all pre-approved in skill frontmatter). Documented commands avoid shell-specific syntax so they work in Git Bash, PowerShell, and POSIX shells alike.

## Contract compatibility

Contracts are versioned integers embedded in every instance (see [contracts README](../core/contracts/README.md)):

- **Additive-only within a version.** New optional fields do not bump the version.
- **Breaking changes bump the version.** Removing a field, changing a type, tightening an enum, or making an optional field required requires a new version.
- **Old versions stay readable.** When a new version ships, readers still accept prior versions; persisted records are upgraded by the storage `migrate` operation.
- **Extensible enums** (marked in the schema) reserve `unknown`/`other` members so new realities degrade gracefully instead of failing validation.

## Knowledge compatibility

Knowledge packs are versioned independently of code and of contracts. Reports pin the knowledge, provider, rubric, and (when a policy corpus was loaded) policy versions that produced them, so any report is reproducible against the exact knowledge and policy state. Claim/taxonomy/rubric/policy version bumps are logged in [CHANGELOG.md](../CHANGELOG.md).

## SemVer for the project

The project follows Semantic Versioning. Contract and knowledge version bumps are called out in the changelog. Pre-1.0 (`0.x`), interfaces may still change between minor versions; the changelog documents every such change.

## Deprecation

A superseded contract version is supported for at least one minor release after its replacement ships, with a migration note. Deprecations are announced in the changelog before removal.
