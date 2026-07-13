# Policy schemas — design

| | |
|---|---|
| **Status** | Approved (Option A), with four refinements incorporated. This document specifies the schemas; FR-3 implements exactly what is specified here. |
| **Decision** | Policy is validated, declarative data. Three additive schemas under `core/contracts/knowledge/`. |
| **Predecessor** | [Policy architecture](policy-architecture.md); [Contract invariants](../CONTRACT-INVARIANTS.md); [Knowledge contract](../../core/contracts/knowledge/CONTRACT.md) |
| **Governs** | The *shape* of the three `common`-pack policy files FR-3 authors |

This document specifies the three policy schemas field-by-field: every field, whether it is required or optional, its validation rules, and why it exists. It provides a minimal valid example document for each. It then confirms the design is purely declarative, embeds no executable logic or rule language, and remains provider-neutral and compatible with frozen M0.

Four refinements requested at approval are incorporated throughout and called out where they land:

1. **Stable, permanent identifiers** on every policy entry (`MISUSE-001`, `RW-001`, `NOTICE-001`), never reused — see [Stable identifiers](#stable-identifiers-refinement-1).
2. **`schema_version` separated from `policy_version`** — schema evolution and policy evolution are independent axes — see [Two version axes](#two-version-axes-refinement-2).
3. **Documented compatibility rules** per schema (additive / compatible / breaking) — see each schema's *Compatibility* table and the shared [Compatibility model](#compatibility-model-refinement-3).
4. **Maintainer-facing `rationale`** on every entry, documentation-only and never read at runtime — see [Rationale](#maintainer-rationale-refinement-4).

## The declarative mandate (the governing constraint)

The schemas **validate policy data. They never execute it.** The analyzer and rewrite engine (M2–M4 code) are the sole interpreters of policy; the policy files are inert, descriptive data. This has concrete design consequences, and they are the reason the misuse model below looks different from the sketch in the architecture design:

- **No branching encoded as data.** There are no `next`, `goto`, `on_yes`, `on_no`, `if`, `then`, or `else` fields anywhere. A decision-tree-as-data is a program; it is prohibited. The misuse `procedure` is an **ordered list of prose steps** — a documented checklist the analyzer follows in order, exactly as the rubric is an ordered list of dimensions. Sequence is data; conditional dispatch is not.
- **No expressions, formulas, or code.** No field holds an expression to be evaluated, a threshold to be computed, a regex to be executed against prompts, or a template language. Where the design needs "logic-like" content, it takes one of two inert forms only: **(a) a closed enum of named situations/outcomes** (a controlled vocabulary the engine maps to behavior), or **(b) human-readable prose** the analyzer reads and applies.
- **The engine owns interpretation.** "The analyzer classifies by applying these steps" means the *code* applies them. The data says *what* the steps are; the code decides *what to do*. This division is the whole point: policy can be reviewed, versioned, diffed, and validated as data, while the judgment that consumes it lives in one auditable place.

If a future requirement seems to need executable behavior in policy (a computed condition, dynamic dispatch, a cross-field rule the schema cannot state), the answer is **not** to grow a rule language into the schema. It is to implement that behavior in the analyzer/verifier as code and, if it is an invariant, record it in [CONTRACT-INVARIANTS.md](../CONTRACT-INVARIANTS.md). The "Expressiveness boundary" section below records what these schemas intentionally cannot express, so that boundary is explicit rather than discovered under pressure.

## Shared conventions

All three schemas obey the existing knowledge-schema conventions and the recursion-free subset ([contracts README](../../core/contracts/README.md)):

- **Subset only.** `type`, `const`, `enum`, `properties`, `required`, `items`, `minItems`/`maxItems`, `uniqueItems`, `pattern`, `minLength`, plus annotations. **No** `$ref`, `anyOf`, `if/then`, `patternProperties`, or recursion. Every object sets `additionalProperties: false`.
- **Status lifecycle.** `misuse-policy` and `rewrite-policy` carry `status` ∈ `draft`/`active`/`deprecated`, matching techniques/events/rubric. (The notices file is a pure text table keyed to a closed enum and carries no status.)
- **Provider-neutral (KN-5).** These are `common`-pack files. They contain **no** `provider` field and **no** `clm-*` claim citations. Provider specifics never appear here; they live in provider packs and feed only the report's Estimated layer.

### Stable identifiers (refinement 1)

Every policy **entry** — every object that is a member of a list whose membership evolves — carries an `id` that is a **stable, permanent registry key**. The rules:

- **Form.** One prefix per file, a hyphen, and a zero-padded three-digit number: `^MISUSE-[0-9]{3}$` in `misuse-policy`, `^RW-[0-9]{3}$` in `rewrite-policy`, `^NOTICE-[0-9]{3}$` in `notices`.
- **Permanent and unique.** An id is assigned once and **never reused, never renumbered, never repurposed**. Deleting an entry retires its id permanently; a later entry takes the next unused number. Ids are unique across *all* lists within a file (a single registry per file), which an integrity test enforces.
- **Opaque.** The number carries no meaning (not a priority, not an order — array position is order). It is a durable handle for tests, audit logs, reports, and cross-references.
- **Separate from semantic role.** Where an entry also has a *closed semantic role* — a misuse `class`, a `notice` kind that links to the frozen [Rewrite Report](../../core/contracts/rewrite-report/CONTRACT.md) `notices` enum, or a `guarantee_ref` that links to an architecture RG-guarantee — that role lives in its **own field**, distinct from `id`. This keeps the permanent registry key independent of any value that a frozen contract or the architecture already fixes, so neither can drift into the other.
- **Singletons are keyed by name.** The two singleton objects (a file's root, and the misuse `elicitation` rule) are addressed by their JSON key, not by a registry id. Ids exist to disambiguate *members of a collection*; a singleton needs neither a disambiguator nor a stable cross-reference handle. Singletons still carry a `rationale`.

### Two version axes (refinement 2)

Policy has **two independent evolution axes**, and each policy file names both:

| Field | Type | Governs | Bumped when |
|---|---|---|---|
| `schema_version` | integer `const` | The **shape** of the file (which fields exist, their types, their enums). Mirrors the `$id`'s `/vN`. This is the contract/format version, subject to VC-1/VC-2. | The schema changes shape (see Compatibility model). |
| `policy_version` | string, `^[0-9]{4}\.[0-9]{2}(-[a-z0-9]+)?$` | The **content** of the file (which entries exist, their wording, their outcomes). Reports pin it for reproducibility. | The policy content changes, with the shape unchanged. |

These are deliberately separate concerns: the wording of a decline template or the addition of a transformation is a *content* event (`policy_version`) that must not be conflated with a *format* event (`schema_version`). Older knowledge files (`claims.json`, `events.json`, `rubric.json`) use a single `file_version` integer for the format axis; the policy files rename that axis to `schema_version` precisely to sit it beside `policy_version` and make the independence explicit and legible. Functionally `schema_version` plays the same role `file_version` plays elsewhere (an integer `const` format version); only the name differs, and the [knowledge contract](../../core/contracts/knowledge/CONTRACT.md) records the reason.

### Maintainer rationale (refinement 4)

Every entry (and every singleton) carries a required `rationale`: prose that explains, to a future maintainer, *why the entry exists and why it is worded as it is*. Its schema annotation states the binding rule:

> Maintainer-facing documentation only. Not consumed by the analyzer, rewrite engine, or verifier; must not affect runtime behavior.

`rationale` is **required at validation time** (documentation discipline — a policy entry with no recorded reason does not validate), but it is **never read at decision time**. Requiring a field at validation is not runtime behavior; the engine's decisions are a pure function of the *other* fields. This is stated in each schema and asserted by the confirmation checklist.

### A note on VC-3 (graceful-degradation members)

VC-3 requires extensible, open-world enums (event `kind`, IR `kind`) to reserve a degradation member so new real-world realities validate instead of failing. **None of the policy enums are open-world.** `class` (3 members), `gate_outcome`, `mode`, `status`, `notice`, and `applies_when` are *internal controlled vocabularies*: closed sets whose growth is a coordinated, versioned schema change, not an unpredictable input from the world. Like `severity` (closed) and unlike event `kind` (open), they take no degradation member. This is a deliberate application of VC-3, not an oversight.

## Compatibility model (refinement 3)

Because policy has two version axes, it has two families of change. Each schema section below gives a concrete table; the shared rules are:

**Shape changes — governed by `schema_version` and VC-1/VC-2.**

| Class | Examples | Effect |
|---|---|---|
| **Additive** | Add a new *optional* field. | Within-version (VC-1). `schema_version` unchanged; readers of the old shape ignore the new field. |
| **Breaking** | Remove or rename a field; make an optional field required; narrow an enum; tighten a pattern; change a type; lower a `maxItems`. | New `schema_version` **and** a new `$id` `/vN` (VC-1). Readers must be upgraded. |

There are no "compatible" shape changes distinct from additive ones: a shape edit either only adds optional surface (additive) or it breaks (new version).

**Content changes — governed by `policy_version`.**

| Class | Examples | Effect |
|---|---|---|
| **Additive** | Add a new entry with a fresh, never-reused `id`. | Bump `policy_version`. Consumers that don't recognize the id degrade gracefully (an unknown notice/transformation is simply not emitted). No behavior regresses. |
| **Compatible** | Reword a `definition`, `description`, `text`, `statement`, `guidance`, `when`, or `rationale` without changing any `id`, enum value, or structure. | Bump `policy_version`. Decision snapshots (architecture §8) are unaffected because they pin *decisions*, not prose. |
| **Breaking** | Remove an entry; change a `class`'s `gate_outcome`; change a guarantee's `mode`; change a `notice`'s `text` in a way that alters its meaning; change a `notice_rule`'s `applies_when`; retire a class. | Bump `policy_version`, call it out in CHANGELOG, and update decision snapshots. The shape is unchanged (no `schema_version` bump), but behavior changes, so it is reviewed as a behavior change and may require coordinated verifier updates. Changing an existing `id` is **never** permitted (refinement 1). |

---

## Schema 1 — `misuse-policy`

**Purpose.** Declaratively describe how the legitimacy of *rewriting* is classified: the three classes, the neutral ordered procedure the analyzer follows, the ask-don't-guess rule for ambiguity, and the fixed decline wording. Provider-neutral; interpreted by the analyzer, never executed.

### Fields

| Field | Req? | Type / rule | Purpose |
|---|---|---|---|
| `schema_version` | ✅ | `const: 1` | Format version; lets the M2 validator dispatch. |
| `policy_version` | ✅ | string, version pattern | Content version; reports pin it for reproducibility. |
| `classes` | ✅ | array, exactly 3 items | The closed set of classification outcomes. |
| `classes[].id` | ✅ | string, `^MISUSE-[0-9]{3}$` | Stable permanent registry key. Never reused. |
| `classes[].class` | ✅ | enum `legitimate`/`ambiguous`/`prohibited` | The closed semantic class identity (distinct from the registry `id`). |
| `classes[].definition` | ✅ | string, non-empty | Prose definition of the class (what qualifies). |
| `classes[].gate_outcome` | ✅ | enum `passed_or_conditional`/`elicit`/`declined` | The declarative association from class → the Rewrite-Report gate space. The analyzer chooses *within* `passed_or_conditional` at runtime; the data only names the permitted space. |
| `classes[].analyzer_action` | ✅ | string, non-empty | Prose: what the analyzer does for this class. |
| `classes[].rationale` | ✅ | string, non-empty | Maintainer-facing; not read at runtime. |
| `procedure` | ✅ | array, ≥1 item | The neutral classification steps, **applied in array order**. A checklist, not a flowchart. |
| `procedure[].id` | ✅ | string, `^MISUSE-[0-9]{3}$` | Stable permanent registry key. |
| `procedure[].description` | ✅ | string, non-empty | Prose describing the step the analyzer performs. Contains no branching directive. |
| `procedure[].rationale` | ✅ | string, non-empty | Maintainer-facing; not read at runtime. |
| `elicitation` | ✅ | object (singleton) | The ask-don't-guess rule for `ambiguous`. Keyed by name, no `id`. |
| `elicitation.when` | ✅ | string, non-empty | Prose: the situation in which to elicit rather than guess. |
| `elicitation.guidance` | ✅ | string, non-empty | Prose: how to ask, and that the answer becomes stated context for re-classification. |
| `elicitation.rationale` | ✅ | string, non-empty | Maintainer-facing; not read at runtime. |
| `decline_templates` | ✅ | array, ≥1 item | Fixed decline wording the gate uses on `declined`. |
| `decline_templates[].id` | ✅ | string, `^MISUSE-[0-9]{3}$` | Stable permanent registry key. |
| `decline_templates[].text` | ✅ | string, non-empty | The fixed decline text (versioned, testable). |
| `decline_templates[].rationale` | ✅ | string, non-empty | Maintainer-facing; not read at runtime. |
| `status` | ✅ | enum `draft`/`active`/`deprecated` | Promotion state (starts `draft`, promoted in FR-2/M-later). |

There are **no optional fields** in v1; every field is required. This is deliberate — a policy with holes is a policy that fails open. Optionality can be added additively later without a version bump (VC-1).

### Compatibility

| Change | Class | Axis |
|---|---|---|
| Add a `procedure` step / `decline_template` with a new id | Additive | `policy_version` |
| Reword any `definition` / `description` / `text` / `rationale` | Compatible | `policy_version` |
| Change a `class`'s `gate_outcome`; remove a class; remove a step | Breaking (behavior) | `policy_version` + CHANGELOG + snapshots |
| Add an optional field to the schema | Additive | `schema_version` unchanged (VC-1) |
| Add a member to `class`/`gate_outcome`, or make a field required | Breaking (shape) | new `schema_version` + `/v2` |

### Design (intended `misuse-policy.schema.json`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://prompt-debugger.dev/schemas/knowledge-misuse-policy/v1",
  "title": "Misuse Policy file v1",
  "description": "Provider-neutral, declarative description of how the legitimacy of rewriting is classified. Descriptive prose and closed enums only; contains no executable logic, expressions, or branching. The analyzer interprets this data; it does not execute it. The 'rationale' fields are maintainer documentation and must not affect runtime behavior.",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "policy_version", "classes", "procedure", "elicitation", "decline_templates", "status"],
  "properties": {
    "schema_version": { "const": 1 },
    "policy_version": { "type": "string", "pattern": "^[0-9]{4}\\.[0-9]{2}(-[a-z0-9]+)?$" },
    "classes": {
      "type": "array",
      "minItems": 3,
      "maxItems": 3,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "class", "definition", "gate_outcome", "analyzer_action", "rationale"],
        "properties": {
          "id": { "type": "string", "pattern": "^MISUSE-[0-9]{3}$" },
          "class": { "type": "string", "enum": ["legitimate", "ambiguous", "prohibited"] },
          "definition": { "type": "string", "minLength": 1 },
          "gate_outcome": { "type": "string", "enum": ["passed_or_conditional", "elicit", "declined"] },
          "analyzer_action": { "type": "string", "minLength": 1 },
          "rationale": { "type": "string", "minLength": 1, "description": "Maintainer-facing documentation only; must not affect runtime behavior." }
        }
      }
    },
    "procedure": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "description", "rationale"],
        "properties": {
          "id": { "type": "string", "pattern": "^MISUSE-[0-9]{3}$" },
          "description": { "type": "string", "minLength": 1 },
          "rationale": { "type": "string", "minLength": 1, "description": "Maintainer-facing documentation only; must not affect runtime behavior." }
        }
      }
    },
    "elicitation": {
      "type": "object",
      "additionalProperties": false,
      "required": ["when", "guidance", "rationale"],
      "properties": {
        "when": { "type": "string", "minLength": 1 },
        "guidance": { "type": "string", "minLength": 1 },
        "rationale": { "type": "string", "minLength": 1, "description": "Maintainer-facing documentation only; must not affect runtime behavior." }
      }
    },
    "decline_templates": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "text", "rationale"],
        "properties": {
          "id": { "type": "string", "pattern": "^MISUSE-[0-9]{3}$" },
          "text": { "type": "string", "minLength": 1 },
          "rationale": { "type": "string", "minLength": 1, "description": "Maintainer-facing documentation only; must not affect runtime behavior." }
        }
      }
    },
    "status": { "type": "string", "enum": ["draft", "active", "deprecated"] }
  }
}
```

### Minimal valid example (illustrative only — FR-3 authors the real content)

```json
{
  "schema_version": 1,
  "policy_version": "2026.07-draft",
  "classes": [
    {
      "id": "MISUSE-001",
      "class": "legitimate",
      "definition": "A plausible benign reading exists and is consistent with the user's stated purpose and context; the request is not primarily aimed at defeating a safety system.",
      "gate_outcome": "passed_or_conditional",
      "analyzer_action": "Produce a rewrite that makes the stated intent more explicit.",
      "rationale": "The default for good-faith prompts; the gate exists to help clarity, not to gatekeep benign work."
    }
  ],
  "procedure": [
    { "id": "MISUSE-010", "description": "Construct the most plausible legitimate reading and the most plausible harmful reading together with any stated purpose.", "rationale": "Dual-reading forces the analyzer to consider both intents before judging, rather than pattern-matching a topic." }
  ],
  "elicitation": {
    "when": "Purpose is unstated and a harmful reading is plausible.",
    "guidance": "Ask what the user is trying to accomplish and why; incorporate the answer as stated context, then re-run the procedure.",
    "rationale": "Ask-don't-guess keeps the gate from resolving ambiguity in the permissive direction on the user's behalf."
  },
  "decline_templates": [
    { "id": "MISUSE-020", "text": "This request appears aimed at getting around a safety system, so a rewrite is not offered. The observable event is still explained below.", "rationale": "Fixed, testable decline wording keeps the refusal stable and auditable rather than model-authored." }
  ],
  "status": "draft"
}
```

---

## Schema 2 — `rewrite-policy`

**Purpose.** Declaratively catalogue what a rewrite may do (allowed transformations, each traced to techniques), what it must never do (the intent-laundering checklist), the guarantees it upholds (with each guarantee's enforcement mode), and which fixed notices attach in which named situations. Provider-neutral; interpreted, never executed.

### Fields

| Field | Req? | Type / rule | Purpose |
|---|---|---|---|
| `schema_version` | ✅ | `const: 1` | Format version. |
| `policy_version` | ✅ | string, version pattern | Content version. |
| `allowed_transformations` | ✅ | array, ≥1 | What a rewrite is permitted to do. |
| `allowed_transformations[].id` | ✅ | `^RW-[0-9]{3}$` | Stable permanent registry key. |
| `allowed_transformations[].description` | ✅ | string, non-empty | Prose describing the permitted transformation. |
| `allowed_transformations[].techniques` | ✅ | array of `^T[0-9]+$` | Technique ids this transformation applies (provenance to the techniques file). May be empty for purely mechanical edits. |
| `allowed_transformations[].rationale` | ✅ | string, non-empty | Maintainer-facing; not read at runtime. |
| `prohibited_transformations` | ✅ | array, ≥1 | The intent-laundering checklist (guarantee RG-6). |
| `prohibited_transformations[].id` | ✅ | `^RW-[0-9]{3}$` | Stable permanent registry key. |
| `prohibited_transformations[].description` | ✅ | string, non-empty | Prose describing the forbidden transformation. |
| `prohibited_transformations[].rationale` | ✅ | string, non-empty | Maintainer-facing; not read at runtime. |
| `guarantees` | ✅ | array, ≥1 | The rewrite guarantees this policy binds. |
| `guarantees[].id` | ✅ | `^RW-[0-9]{3}$` | Stable permanent registry key (file-local). |
| `guarantees[].guarantee_ref` | ✅ | `^RG-[0-9]+$` | Link to the architecture guarantee (RG-1..RG-8). Distinct from the registry `id`. |
| `guarantees[].statement` | ✅ | string, non-empty | Prose statement of the guarantee. |
| `guarantees[].mode` | ✅ | enum `hard`/`judged` | Whether the guarantee is mechanically checkable (hard) or evaluated by a semantic suite (judged). Honest, testable distinction. |
| `guarantees[].rationale` | ✅ | string, non-empty | Maintainer-facing; not read at runtime. |
| `notice_rules` | ✅ | array, ≥1 | Which notice attaches in which situation. |
| `notice_rules[].id` | ✅ | `^RW-[0-9]{3}$` | Stable permanent registry key. |
| `notice_rules[].notice` | ✅ | enum `non_guarantee`/`epistemic`/`gate_declined`/`gate_conditional` | The notice (matches the Rewrite-Report `notices` enum). |
| `notice_rules[].applies_when` | ✅ | enum `rewrite_produced`/`event_explained`/`gate_declined`/`gate_conditional` | The named situation that triggers the notice. A controlled vocabulary the engine maps to behavior — not a computed condition. |
| `notice_rules[].rationale` | ✅ | string, non-empty | Maintainer-facing; not read at runtime. |
| `status` | ✅ | enum `draft`/`active`/`deprecated` | Promotion state. |

`allowed_transformations[].techniques` is the one field permitted to be an empty array (a mechanical edit cites no technique); every other field is required and non-empty. No optional fields in v1.

### Compatibility

| Change | Class | Axis |
|---|---|---|
| Add an allowed/prohibited transformation, guarantee binding, or notice rule with a new id | Additive | `policy_version` |
| Reword any `description` / `statement` / `rationale` | Compatible | `policy_version` |
| Change a guarantee's `mode`; remove a prohibited transformation; change a `notice_rule`'s `applies_when` | Breaking (behavior) | `policy_version` + CHANGELOG + snapshots |
| Add an optional field to the schema | Additive | `schema_version` unchanged (VC-1) |
| Narrow the `mode`/`notice`/`applies_when` enum, or make a field required | Breaking (shape) | new `schema_version` + `/v2` |

### Design (intended `rewrite-policy.schema.json`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://prompt-debugger.dev/schemas/knowledge-rewrite-policy/v1",
  "title": "Rewrite Policy file v1",
  "description": "Provider-neutral, declarative catalogue of allowed and prohibited rewrite transformations, the guarantees a rewrite upholds, and which notices attach in which named situations. Descriptive prose and closed enums only; no executable logic, expressions, or branching. Interpreted by the rewrite engine; never executed. The 'rationale' fields are maintainer documentation and must not affect runtime behavior.",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "policy_version", "allowed_transformations", "prohibited_transformations", "guarantees", "notice_rules", "status"],
  "properties": {
    "schema_version": { "const": 1 },
    "policy_version": { "type": "string", "pattern": "^[0-9]{4}\\.[0-9]{2}(-[a-z0-9]+)?$" },
    "allowed_transformations": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "description", "techniques", "rationale"],
        "properties": {
          "id": { "type": "string", "pattern": "^RW-[0-9]{3}$" },
          "description": { "type": "string", "minLength": 1 },
          "techniques": {
            "type": "array",
            "items": { "type": "string", "pattern": "^T[0-9]+$" }
          },
          "rationale": { "type": "string", "minLength": 1, "description": "Maintainer-facing documentation only; must not affect runtime behavior." }
        }
      }
    },
    "prohibited_transformations": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "description", "rationale"],
        "properties": {
          "id": { "type": "string", "pattern": "^RW-[0-9]{3}$" },
          "description": { "type": "string", "minLength": 1 },
          "rationale": { "type": "string", "minLength": 1, "description": "Maintainer-facing documentation only; must not affect runtime behavior." }
        }
      }
    },
    "guarantees": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "guarantee_ref", "statement", "mode", "rationale"],
        "properties": {
          "id": { "type": "string", "pattern": "^RW-[0-9]{3}$" },
          "guarantee_ref": { "type": "string", "pattern": "^RG-[0-9]+$" },
          "statement": { "type": "string", "minLength": 1 },
          "mode": { "type": "string", "enum": ["hard", "judged"] },
          "rationale": { "type": "string", "minLength": 1, "description": "Maintainer-facing documentation only; must not affect runtime behavior." }
        }
      }
    },
    "notice_rules": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "notice", "applies_when", "rationale"],
        "properties": {
          "id": { "type": "string", "pattern": "^RW-[0-9]{3}$" },
          "notice": { "type": "string", "enum": ["non_guarantee", "epistemic", "gate_declined", "gate_conditional"] },
          "applies_when": { "type": "string", "enum": ["rewrite_produced", "event_explained", "gate_declined", "gate_conditional"] },
          "rationale": { "type": "string", "minLength": 1, "description": "Maintainer-facing documentation only; must not affect runtime behavior." }
        }
      }
    },
    "status": { "type": "string", "enum": ["draft", "active", "deprecated"] }
  }
}
```

### Minimal valid example (illustrative only)

```json
{
  "schema_version": 1,
  "policy_version": "2026.07-draft",
  "allowed_transformations": [
    { "id": "RW-001", "description": "Make the stated audience and purpose explicit using only context the user supplied.", "techniques": ["T2"], "rationale": "Explicit purpose is the single highest-value clarity edit and stays within user-supplied facts (RG-7)." }
  ],
  "prohibited_transformations": [
    { "id": "RW-050", "description": "Introduce facts, credentials, authorization, or background the user did not supply.", "rationale": "Fabricated context is intent laundering; RG-7 forbids it outright." }
  ],
  "guarantees": [
    { "id": "RW-080", "guarantee_ref": "RG-5", "statement": "Every evidence quote and IR segment text is a verbatim substring of its reference prompt.", "mode": "hard", "rationale": "Mechanically checkable by substring; the verifier decides it deterministically." }
  ],
  "notice_rules": [
    { "id": "RW-090", "notice": "non_guarantee", "applies_when": "rewrite_produced", "rationale": "RW-2 makes the non-guarantee notice mandatory whenever a rewrite text exists." }
  ],
  "status": "draft"
}
```

---

## Schema 3 — `notices`

**Purpose.** The fixed, versioned text of each notice, keyed to the Rewrite-Report `notices` enum. Keeping the wording here (not in model output) is what makes the non-guarantee notice stable and testable, per the Rewrite-Report contract.

### Fields

| Field | Req? | Type / rule | Purpose |
|---|---|---|---|
| `schema_version` | ✅ | `const: 1` | Format version. |
| `policy_version` | ✅ | string, version pattern | Content version. |
| `notices` | ✅ | array, ≥1 | The notice texts. |
| `notices[].id` | ✅ | `^NOTICE-[0-9]{3}$` | Stable permanent registry key. |
| `notices[].notice` | ✅ | enum `non_guarantee`/`epistemic`/`gate_declined`/`gate_conditional` | Notice identity; matches the Rewrite-Report `notices` enum exactly. |
| `notices[].text` | ✅ | string, non-empty | The fixed notice wording. |
| `notices[].rationale` | ✅ | string, non-empty | Maintainer-facing; not read at runtime. |

No optional fields.

### Compatibility

| Change | Class | Axis |
|---|---|---|
| Add a notice entry with a new id (e.g. a future notice enum member) | Additive | `policy_version` |
| Reword a notice `text` without changing meaning; edit a `rationale` | Compatible | `policy_version` |
| Change a notice `text` meaning; remove a notice | Breaking (behavior) | `policy_version` + CHANGELOG + snapshots |
| Narrow the `notice` enum, or make a field required | Breaking (shape) | new `schema_version` + `/v2` |

### Design (intended `notices.schema.json`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://prompt-debugger.dev/schemas/knowledge-notices/v1",
  "title": "Notices file v1",
  "description": "Fixed, versioned notice texts keyed to the Rewrite Report notices enum. Text data only; no logic. The engine attaches these texts per the rewrite-policy notice_rules. The 'rationale' fields are maintainer documentation and must not affect runtime behavior.",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "policy_version", "notices"],
  "properties": {
    "schema_version": { "const": 1 },
    "policy_version": { "type": "string", "pattern": "^[0-9]{4}\\.[0-9]{2}(-[a-z0-9]+)?$" },
    "notices": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "notice", "text", "rationale"],
        "properties": {
          "id": { "type": "string", "pattern": "^NOTICE-[0-9]{3}$" },
          "notice": { "type": "string", "enum": ["non_guarantee", "epistemic", "gate_declined", "gate_conditional"] },
          "text": { "type": "string", "minLength": 1 },
          "rationale": { "type": "string", "minLength": 1, "description": "Maintainer-facing documentation only; must not affect runtime behavior." }
        }
      }
    }
  }
}
```

### Minimal valid example (illustrative — FR-3 finalizes exact wording)

```json
{
  "schema_version": 1,
  "policy_version": "2026.07-draft",
  "notices": [
    { "id": "NOTICE-001", "notice": "non_guarantee", "text": "This rewrite is intended to improve clarity and communicate your legitimate intent more effectively. It does not guarantee a different response, as model behavior depends on the provider's systems and policies.", "rationale": "The mandatory RW-2 notice; wording avoids implying any promise about provider behavior." }
  ]
}
```

---

## Confirmation checklist

### Expressive enough for current requirements

Walking the analyzer/rewrite needs against the schemas: the misuse gate needs classes + an ordered neutral procedure + an elicitation rule + decline wording → all present in `misuse-policy`. The rewrite engine needs the allowed set (with technique provenance), the prohibited set (RG-6 checklist), the guarantees it must uphold (with hard/judged mode and an RG link), and the notice attachments → all present in `rewrite-policy`. The presentation layer needs fixed notice texts keyed to the report enum → present in `notices`. Every element the policy-architecture design (§§3–5) names has a home. **Expressive enough: yes.**

### No executable logic; no rule language

Every field is one of: a version/const, a **closed enum** (controlled vocabulary), a **string of human-readable prose**, an **id or id-reference**, or an **array** of those. There is no field that holds an expression, formula, code, template language, regex-against-prompts, computed threshold, or branching directive (`next`/`goto`/`if`/`then`). Array order expresses a documented sequence (a checklist), which is inert data — the analyzer walks it; the data does not dispatch. **Declarative: confirmed.**

### Rationale is documentation-only

`rationale` appears on every entry and singleton, is required at validation time, and is annotated in every schema as maintainer documentation that must not affect runtime behavior. The engine's decisions are a pure function of the other fields; no decision reads `rationale`. **Runtime-inert documentation: confirmed.**

### Provider-neutral

All three are `common`-pack files with no `provider` field and no `clm-*` citation; wording is topic-agnostic (the misuse model classifies by intent-relative-to-safeguards, never by subject matter). KN-5 is preserved. **Provider-neutral: confirmed.**

### Compatible with frozen M0

The schemas use only the recursion-free subset, set `additionalProperties: false` on every object, carry `schema_version`/`policy_version`, and follow existing id/status conventions. They are **additive**: three new schema files under `core/contracts/knowledge/`, no change to any existing contract, schema, or the repository layout. This is the Option-A contract addition, taken under the frozen-baseline exception with approval.

## Expressiveness boundary (documented limits, by design)

These schemas deliberately **cannot** express, and never will: conditional cross-field rules ("if class X then require notice Y"), computed numeric thresholds, dynamic dispatch between steps, per-input branching, or any executable predicate. When such behavior is genuinely required, it is implemented in the **analyzer/verifier code** and, if it is an invariant, recorded in [CONTRACT-INVARIANTS.md](../CONTRACT-INVARIANTS.md) — for example, RW-2 ("`non_guarantee` mandatory when `text != null`") is enforced by the verifier, and `notice_rules` here merely *declares the association* the verifier checks. The schema states relationships as data; the code enforces them. This boundary is the guarantee that policy stays reviewable data and never drifts into a program.

## Implementation footprint (FR-3)

FR-3 implements exactly this design: it adds the three `*.schema.json` files above under `core/contracts/knowledge/`; authors the three `common`-pack policy files (`misuse-policy.json`, `rewrite-policy.json`, `notices.json`) plus Markdown companions with the authoritative content; wires each file→schema pair into `tools/validate_schemas.py`; extends `tests/test_knowledge_integrity.py` with the policy integrity checks (stable-id uniqueness; `notice` values ⊆ Rewrite-Report enum; `notice_rules` references ⊆ notices file; `guarantee_ref` ⊆ RG set; provider-neutrality of the new files); records the policy invariants in [CONTRACT-INVARIANTS.md](../CONTRACT-INVARIANTS.md); and notes the change in the changelog. No analyzer or rewrite behavior is implemented — that is M2–M4.
