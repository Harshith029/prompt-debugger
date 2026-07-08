# Contracts

Versioned, host-neutral contracts. Every adapter, tool, test, and stored artifact binds to these — never to prose in a skill file or to implementation details.

## Index

| Contract | Version | Schema(s) | Prose |
|---|---|---|---|
| Prompt IR | 1 | [`prompt-ir/prompt-ir.schema.json`](prompt-ir/prompt-ir.schema.json) | [`prompt-ir/CONTRACT.md`](prompt-ir/CONTRACT.md) |
| Report JSON | 1 | [`report/report.schema.json`](report/report.schema.json) | [`report/CONTRACT.md`](report/CONTRACT.md) |
| Rewrite Report | 1 | [`rewrite-report/rewrite-report.schema.json`](rewrite-report/rewrite-report.schema.json) | [`rewrite-report/CONTRACT.md`](rewrite-report/CONTRACT.md) |
| Observable Event | 1 | [`events/observable-event.schema.json`](events/observable-event.schema.json) | [`events/CONTRACT.md`](events/CONTRACT.md) |
| Storage | 1 | [`storage/history-record.schema.json`](storage/history-record.schema.json), [`storage/config.schema.json`](storage/config.schema.json) | [`storage/CONTRACT.md`](storage/CONTRACT.md) |
| Knowledge Engine | 1 | [`knowledge/`](knowledge/) (7 file-format schemas) | [`knowledge/CONTRACT.md`](knowledge/CONTRACT.md) |
| Plugin / Adapter API | 1 | [`plugin-api/adapter-manifest.schema.json`](plugin-api/adapter-manifest.schema.json) | [`plugin-api/CONTRACT.md`](plugin-api/CONTRACT.md) |
| Prompt Tree | 1 | [`prompt-tree/prompt-tree.schema.json`](prompt-tree/prompt-tree.schema.json) | [`prompt-tree/CONTRACT.md`](prompt-tree/CONTRACT.md) |

## Versioning and compatibility rules

1. **Every contract carries an integer version** embedded in its instances (`ir_version`, `report_version`, …). Instances state the version they conform to; validators dispatch on it.
2. **Additive-only within a version.** New *optional* fields may be added to a schema without a version bump. Removing a field, changing a type, tightening an enum, or making an optional field required is a **breaking change** and requires a new version.
3. **Old versions remain readable.** When version N+1 ships, readers must still accept version N instances (the Storage contract's `migrate` operation upgrades persisted records; see `storage/CONTRACT.md`).
4. **Enums are open by policy where marked.** Enums documented as *closed* (e.g., severity) reject unknown values. Enums documented as *extensible* (e.g., event `kind`) reserve `unknown`/`other` members so new realities degrade gracefully instead of failing validation.
5. **Version bumps are logged** in `CHANGELOG.md` with a migration note.

## Schema subset (normative)

All schemas are JSON Schema **draft 2020-12 restricted to this subset**, so the M2 stdlib validator can implement them exactly. CI rejects schemas that stray outside it.

Allowed keywords: `$schema`, `$id`, `$comment`, `title`, `description`, `type` (including type arrays for nullability), `enum`, `const`, `properties`, `required`, `additionalProperties` (must be `false` on every object), `items`, `minItems`, `maxItems`, `uniqueItems`, `pattern`, `minLength`, `maxLength`, `minimum`, `maximum`, `default` (annotation), `examples` (annotation), `format` (annotation only — never enforced).

Prohibited: `$ref`, `$defs`, `anyOf`, `allOf`, `oneOf`, `not`, `if`/`then`/`else`, `patternProperties`, `dependentSchemas`, recursion of any kind.

## Composite validation (normative)

Because `$ref` is prohibited, schemas do not embed one another. Fields governed by another contract are declared as plain objects with a `$comment` naming the governing schema, and **validation code composes validators**:

- `report.ir` → validated against `prompt-ir.schema.json`
- `report.event` → validated against `observable-event.schema.json`
- `report.rewrite` → validated against `rewrite-report.schema.json`
- `history-record.report` → validated against `report.schema.json` (then recursively as above)

A document is valid only if the envelope **and** every composed sub-document validate.

## Integrity rules beyond schemas

Schemas check shape; these semantic rules are enforced by `verify.py` (M2) and asserted by tests:

- Every `PromptIR.segments[].text` and every finding `evidence[].quote` must be a **verbatim substring of the source prompt**.
- Finding `evidence[].segment` values must reference existing IR segment ids.
- `report.rewrite.gate == "declined"` implies `report.rewrite.text == null`.
- Prompt Tree `segment_ids` must reference existing IR segment ids; `parent_id` must reference an existing node or be null (no cycles).
