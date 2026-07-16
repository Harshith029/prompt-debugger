# Policy review process

| | |
|---|---|
| **Audience** | Maintainers. This is a process document, not a contract. |
| **Scope** | How the declarative policy data evolves: the `common`-pack policy files ([misuse-policy](../../core/knowledge/packs/common/misuse-policy.md), [rewrite-policy](../../core/knowledge/packs/common/rewrite-policy.md), [notices](../../core/knowledge/packs/common/notices.md)), their schemas under [`core/contracts/knowledge/`](../../core/contracts/knowledge/CONTRACT.md), and — where noted — provider-pack knowledge that feeds policy decisions. |
| **Effect** | None at runtime. This document changes no schema, no policy file, and no behavior; it only governs how maintainers change them. |
| **Design basis** | [Policy architecture](../design/policy-architecture.md); [Policy schemas](../design/policy-schemas.md); [Contract invariants](../CONTRACT-INVARIANTS.md) |

## Governing principles (recap, binding on every change)

Every policy change must preserve the properties the design established. A change that violates any of these is rejected regardless of its other merits:

1. **Purely declarative.** Policy files are inert data: closed enums and human-readable prose only. No branching fields (`next`, `on_yes`, `if`, `then`), no expressions, no thresholds, no templates-as-code, no regex-against-prompts. If a proposed change needs executable behavior, it belongs in analyzer/verifier code (M2+) and, if invariant, in [CONTRACT-INVARIANTS.md](../CONTRACT-INVARIANTS.md) — never in the data.
2. **Provider-neutral (KN-5).** `common`-pack files carry no `provider` field, cite no `clm-*` claims, and use topic-agnostic wording. Provider specifics live in provider packs and feed only the report's Estimated layer.
3. **Fail-closed.** Policy with holes fails open; that is why every field is required. A change may add safety, precision, or clarity — it may never relax a global (L0) invariant or weaken the misuse gate.
4. **One-directional gate.** No change may make a request more acceptable to a provider or help content get past a safeguard. The rewrite guarantees (RG-1..RG-8) and the prohibited-transformation checklist are floors, not defaults.

## Contribution workflow

1. **Open an issue** describing the proposed policy change, its motivation, and its expected compatibility class (see below). Trivial wording fixes may skip straight to a PR that carries the same information in its description.
2. **Branch and edit.** In one PR, change *both* members of the pair: the `.json` file (what machines validate) and its `.md` companion (what humans and adapters read). Ids must match one-to-one after the change; a PR that lets them drift is incomplete.
3. **Follow id discipline** (PL-1). New entries take the next unused registry number for their file (`MISUSE-###`, `RW-###`, `NOTICE-###`). Never reuse, renumber, or repurpose an id — a removed entry retires its number permanently.
4. **Write the rationale** for every new or reworded entry (see Rationale expectations).
5. **Bump the correct version axis** (see Versioning expectations) and add a CHANGELOG entry naming the compatibility class.
6. **Re-vendor the plugin copy** (`python tools/sync_plugin.py`) — the adapter vendors `core/`, and CI fails on drift.
7. **Run the full quality gate** locally (see Regression requirements) before requesting review.
8. **Request review** per the Approval process. Do not self-merge policy changes.

## Review expectations

A reviewer of a policy PR verifies, explicitly and in this order:

- **Declarative mandate holds.** No new field or value smuggles in logic: no branching directives, no expressions, nothing the engine would *execute* rather than *interpret*. Sequence (array order) is acceptable; dispatch is not.
- **Neutrality holds.** No provider names, product names, `clm-*` citations, or topic-specific carve-outs in `common`-pack files. The misuse model classifies by intent relative to safeguards, never by subject matter.
- **Id discipline holds.** New ids are fresh and well-formed; no existing id changed; registry keys stay separate from semantic roles (`class`, `notice`, `guarantee_ref`).
- **Companion parity holds.** The `.md` companion says the same thing as the `.json`, entry for entry, id for id.
- **The compatibility class is correctly declared.** The author's additive/compatible/breaking classification matches what the diff actually does (reviewers re-derive it; they do not take it on faith).
- **The gate is not weakened.** Any change touching the misuse classes, procedure, prohibited transformations, or guarantees is checked against the four governing principles above and against the [policy architecture](../design/policy-architecture.md) §§3–4.
- **Rationales are real.** Each rationale explains *why*, not *what* (the field already says what). A rationale that paraphrases its own entry is returned for rework.

## Evidence requirements

- **Common-pack policy** is methodology, not provider fact. It requires *reasoned* justification (in rationales and the PR description) but must not cite provider claims — that is what keeps it neutral.
- **Provider-pack knowledge** that informs policy outcomes (claims, techniques, event taxonomy) follows the provenance chain: every provider-behavior statement cites at least one `clm-*` claim (KN-1); `active` entries cite only `verified` claims (KN-2); every claim carries a URL, retrieval date, and verification status against a live public source.
- **Negative results are evidence.** If a source does not document a behavior, record that as a verified-negative claim rather than leaving the boundary implicit — the honest "cannot conclude" boundary must itself be sourced.
- **No fabricated evidence, ever.** If a source cannot be fetched or verified, the change waits or is narrowed to what the reachable sources support; the deferral is documented.

## Compatibility expectations

Every policy PR declares one compatibility class per changed file, using the model defined in [policy-schemas.md](../design/policy-schemas.md#compatibility-model-refinement-3):

| Class | Content examples | Obligations |
|---|---|---|
| **Additive** | New entry with a fresh id | Bump `policy_version`; CHANGELOG line. |
| **Compatible** | Rewording that preserves meaning; rationale edits | Bump `policy_version`; CHANGELOG line. |
| **Breaking (behavior)** | Removing an entry; changing a `gate_outcome`, `mode`, `applies_when`, or a notice's meaning | Bump `policy_version`; explicit CHANGELOG callout; update decision snapshots (once they exist, M2+); reviewer must treat it as a behavior change even though no code changed. |

Shape changes (schema edits) are a different family — see Schema evolution rules. Changing an existing `id` is not a compatibility class; it is prohibited outright.

## Versioning expectations

Policy has two independent version axes (see [policy-schemas.md](../design/policy-schemas.md#two-version-axes-refinement-2)):

- **`policy_version`** (string, `YYYY.MM[-tag]`) moves when *content* changes. Every content PR bumps it — or, during a pre-release draft window where all knowledge shares one snapshot label (e.g. `2026.07-draft`), records the change in the CHANGELOG and lets git carry the fine-grained history, keeping labels aligned. Never bump one file's label out of sync with the pack snapshot it belongs to; label desynchronization is worse than label coarseness.
- **`schema_version`** (integer const) moves only when the *shape* changes incompatibly, together with a new `/vN` `$id`. Content PRs never touch it.
- **Pack and corpus labels** (`pack_version`, `knowledge_version`) describe snapshots. When a snapshot label changes, it changes consistently across the manifest, the pack, and the files that share it — one coordinated PR, not piecemeal drift.
- Reports pin `policy_version` (with `knowledge_version` and `rubric_version`) for reproducibility; that is why version bookkeeping is a correctness concern, not housekeeping.

## Schema evolution rules

The three policy schemas are contracts and follow contract discipline (VC-1/VC-2):

- **Subset only, forever.** Schemas stay within the recursion-free subset ([contracts README](../../core/contracts/README.md)); `tools/validate_schemas.py` enforces it. No `$ref`, `anyOf`, `if/then`, `patternProperties`, or recursion; `additionalProperties: false` on every object.
- **Additive within a version.** Adding a new *optional* field is the only in-version shape change. Everything else — removing/renaming a field, requiring an optional field, narrowing an enum, tightening a pattern, changing a type — is breaking and requires a new `schema_version`, a new `$id` `/vN`, and coordinated reader/migration updates.
- **Enum growth is a schema event.** The policy enums (`class`, `gate_outcome`, `mode`, `notice`, `applies_when`, `status`) are closed internal vocabularies (the deliberate VC-3 posture — no degradation member). Adding a member is a reviewed schema change, not a data change, and must be assessed against the frozen contracts it links to (e.g. a new `notice` member requires the Rewrite Report enum to grow first, which is that contract's own additive change).
- **The declarative boundary is non-negotiable.** No schema evolution may introduce a field whose value the engine would execute. The [expressiveness boundary](../design/policy-schemas.md#expressiveness-boundary-documented-limits-by-design) is permanent; pressure against it is redirected to verifier code and CONTRACT-INVARIANTS.md.
- **Schema changes require explicit approval.** M0 froze the contract surface; adding or reshaping a schema is a frozen-baseline exception that a maintainer other than the author must approve *as a contract change*, before implementation.

## Rationale expectations

Every policy entry (and singleton) carries a required `rationale` (PL-6):

- **Audience:** the future maintainer deciding whether to change or remove the entry.
- **Content:** why the entry exists, why it is worded/classified as it is, and what breaks if it is removed. Link the relevant guarantee (RG-*), invariant (RW-*/PL-*), or design section when one grounds the entry.
- **Not runtime input.** Rationales are documentation only. No engine, analyzer, or verifier decision may read them — reviewers reject any code or policy change that gives rationales runtime effect.
- **Kept current.** A PR that changes an entry's meaning must update its rationale in the same PR; a stale rationale is treated as a defect.

## Regression requirements

Before review is requested — and again in CI — the full quality gate must pass:

```
ruff check .                                  # lint
ruff format --check .                         # formatting
mypy                                          # strict typing (project config)
python tools/check_imports.py                 # stdlib-only allowlist
python tools/check_versions.py                # version agreement
python tools/validate_schemas.py --require-jsonschema   # subset + instance validation
python tools/check_links.py                  # docs link integrity
python tools/check_plugin_sync.py            # vendored core/ matches
python benchmarks/run.py validate            # benchmark corpus
pytest                                        # full suite, incl. policy integrity tests
```

Additionally:

- **Integrity tests grow with the data.** A PR that adds a new *kind* of policy entry or cross-reference also extends `tests/test_knowledge_integrity.py` so the new reference class cannot dangle. A PR that adds only entries of an existing kind relies on the existing tests, which must pass unmodified.
- **Decision snapshots (M2+).** Once the engine and its golden decision snapshots exist, any behavior-breaking policy change must update the snapshots in the same PR, so silent behavior drift is impossible.
- **Red-team fixtures for gate changes.** Any change to the misuse classes, procedure, or prohibited transformations must keep every laundering fixture in `evals/red-team-rewrite` yielding `gate: declined` (release-gate condition, per [policy architecture §8](../design/policy-architecture.md)).
- **Never delete a failing check to pass the gate.** If a policy change makes an integrity test fail, either the change is wrong or the test encodes an invariant being deliberately revised — and revising an invariant is its own reviewed change with its own approval.

## Approval process

- **Content changes (additive / compatible):** one maintainer approval other than the author. The reviewer walks the Review expectations checklist above.
- **Behavior-breaking content changes:** one maintainer approval other than the author, *plus* the explicit CHANGELOG callout and (M2+) snapshot updates. The PR description must state what behavior changes and why that is intended.
- **Schema shape changes:** treated as contract changes — explicit prior approval of the design (as was done for the three policy schemas), then implementation reviewed against the approved design. Never design-and-merge in a single unreviewed step.
- **Status promotion** (`draft` → `active`): requires the file's references to satisfy the provenance rules for active entries (KN-2 posture) and a maintainer's explicit promotion decision recorded in the CHANGELOG. Demotion (`active` → `deprecated`) is a behavior-breaking change and follows that path.
- **Disagreement** between author and reviewer escalates to an issue; the fail-closed default applies while it is unresolved (the change waits — policy on `main` is always the last version both parties accepted).

This process document itself evolves by ordinary documentation PR with one maintainer approval; changes to it never alter the meaning of already-merged policy.
