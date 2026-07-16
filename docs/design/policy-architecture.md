# Policy architecture — design

| | |
|---|---|
| **Status** | Approved and implemented as data (M1 FR-3). The schemas and policy files exist; the engine that evaluates them is M2–M4. |
| **Predecessor** | [M0 architecture](../ARCHITECTURE.md) (frozen); [Contract invariants](../CONTRACT-INVARIANTS.md) |
| **Successor** | [Policy schemas](policy-schemas.md) — the authoritative field-by-field specification the implementation follows |
| **Governs** | All future analyzer and rewrite behavior (M2–M4) |
| **Milestone** | Policy Design (preceded [M1](../../specs/M1.md) FR-3 authoring) |

This document specifies the **policy system** that decides, for any prompt, (a) whether a rewrite is permitted, (b) what a rewrite may and may not do, (c) what the analyzer may and may not conclude, and (d) how every such decision is explained and made traceable. It defines layers, precedence, guarantees, a classification model, a reporting philosophy, an extensibility model, and a testing strategy. FR-3 authored the concrete policy files against this design (as refined by [policy-schemas.md](policy-schemas.md)); M2–M4 implement the engine that evaluates them.

The design is deliberately continuous with what already exists. It formalizes and extends the honesty architecture, the [Rewrite Report contract](../../core/contracts/rewrite-report/CONTRACT.md) (`gate` ∈ `passed`/`conditional`/`declined`; invariants RW-1..RW-3), the misuse gate and transformation rules sketched in [ARCHITECTURE §6.6](../ARCHITECTURE.md), the provenance rules (KN-1..KN-2), and the data-driven Knowledge Engine ([ADR-0007](../adr/0007-knowledge-engine.md)). It introduces no new architectural shape; it names and orders what the frozen contracts already imply.

## Design principles

Five properties are required of the policy system; every decision below serves them.

- **Provider-neutral.** The decision *procedure* contains no provider-, product-, or topic-specific wording. Provider specifics are data in provider packs, consumed by the neutral procedure — never branches in it.
- **Deterministic.** A decision is a pure function of (the prompt + its IR) and (the versioned policy corpus). No wall-clock, no randomness, no dependence on unordered iteration. The same inputs always yield the same gate outcome, classification, applied transformations, and findings.
- **Explainable.** Every outcome carries a reason that resolves to a policy rule id and, where it asserts provider behavior, to a dated claim. Nothing is decided by an unnamed heuristic.
- **Testable.** Every guarantee and every layer boundary is expressible as an executable check with compliant and violating fixtures, in the style already used by `tests/test_contract_invariants.py`.
- **Extensible.** A new provider adds a pack; it never edits the neutral procedure or relaxes a global invariant.

A sixth property is load-bearing and stated once here: **fail-closed.** When policy is missing, malformed, mutually contradictory, or a decision is under-determined, the outcome is the safe one — abstain from a conclusion, or decline a rewrite — never the permissive one.

---

## 1. Policy hierarchy

Policy is organized into four layers. Each layer has a single responsibility and a fixed authority relative to the others. Higher layers **constrain** lower layers; lower layers may **specialize** but never **relax**.

| Layer | Name | Lives in | Responsibility | May it be overridden? |
|---|---|---|---|---|
| **L0** | Global invariants (constitutional) | the contracts + this document; enforced in code | The non-negotiable, provider-neutral hard constraints every decision must satisfy: honesty separation, no-bypass, mandatory non-guarantee notice, verbatim evidence, privacy PR-1, no fabricated context. | **Never.** Not by any pack, provider, or configuration. |
| **L1** | Provider-neutral policy | `common` pack | The methodology: the misuse decision procedure, the rewrite transformation rules and guarantees, the fixed notice texts, the quality rubric. Topic-agnostic. | Only by L0. Providers may not edit it. |
| **L2** | Provider policy | provider packs (e.g. `anthropic`) | Provider-specific *knowledge* the neutral procedure consumes: dated claims, techniques, the observable-event taxonomy, patterns, and any provider-specific sensitivities that inform the *Estimated* layer. | Only by adding constraints/specializations; never by weakening L0 or contradicting L1's neutral rules. |
| **L3** | Reporting policy | `common` pack (+ provider taxonomy prose) | How a decided outcome is *presented*: Observed/Estimated separation, confidence labelling, notice attachment, uncertainty phrasing. Presentation only. | It has no authority over decisions; it describes them. |

### Responsibilities in one sentence each

- **L0** decides what is *always* true of a valid decision.
- **L1** decides *how* legitimacy and rewriting are judged, neutrally.
- **L2** supplies *what is known* about a specific provider, as evidence.
- **L3** decides *how the result is said*, never *what the result is*.

### Precedence

Precedence runs strictly downward: **L0 > L1 > L2 > L3.** "Greater" means *more authoritative on conflict* and *more general in scope*. Two consequences are structural, not situational:

1. A lower layer that would relax a higher layer is not a runtime dilemma — it is a **malformed corpus**, rejected at load time (§2).
2. L3 can never change an outcome produced by L0–L2. If a reporting expectation does not match an outcome, the outcome stands and the report states it faithfully.

---

## 2. Conflict resolution

Conflicts are resolved by two mechanisms working together: **static rejection** (most conflicts never reach runtime) and **deterministic runtime evaluation** (for rules that legitimately compose).

### 2.1 Static rejection (load/validation time)

Before any prompt is analyzed, the policy corpus is validated as a whole. The following are **load-time errors**, not runtime resolutions:

- A L2 provider rule that weakens or negates a L0 global invariant or an L1 neutral rule.
- A rule set that is internally contradictory (e.g., a transformation listed as both *required* and *prohibited*).
- A provider statement without a claim citation (KN-1), or an `active` rule citing a non-`verified` claim (KN-2).
- A reference to a policy element that does not exist (a notice id, a technique id, a rubric dimension).

A corpus that fails validation does not load; the engine fails closed (no analysis, no rewrite) rather than operating on an inconsistent policy. This makes the loaded corpus **provably consistent** before any decision is made — the strongest possible form of conflict resolution, because the conflict is designed out.

### 2.2 Deterministic runtime evaluation

Decisions proceed in fixed **phases**, mirroring the analyzer pipeline in [ARCHITECTURE §4.2](../ARCHITECTURE.md):

```
OBSERVE → GATE → SEGMENT → ANALYZE → ESTIMATE → TRANSFORM → REPORT
                 (misuse)            (rubric)   (rewrite)   (present)
```

Phase order is itself the primary conflict-resolution tool: a phase can only see the committed outputs of earlier phases, and cannot re-open them. Within a phase, when multiple rules apply, evaluation is totally ordered by:

1. **layer** (L0 before L1 before L2), then
2. **explicit rule priority** (an integer the rule declares), then
3. **stable rule id** (lexicographic) as the final tiebreak.

For *permissions*, the composition is **intersection — most restrictive wins**: a transformation is applied only if every applicable layer permits it. For *hard constraints*, the first L0 violation **short-circuits** the phase with the fail-closed outcome. No decision depends on the iteration order of an unordered collection; every tiebreak resolves to a stable id, so the decision is reproducible.

### 2.3 The named conflict cases, resolved

| Conflict | Resolution | Why it is deterministic |
|---|---|---|
| **Provider rule vs global invariant** | Global invariant wins; the provider rule is a load-time error (§2.1). If a case is only detectable at runtime, the invariant short-circuits and the offending rule is treated as void and logged. | Designed out at load; never a runtime coin-flip. |
| **Rewrite rule vs safety rule** | Safety wins by *phase order*: GATE precedes TRANSFORM. A `declined` gate short-circuits — no transformation rule runs. A rewrite rule can never re-open a declined gate. | Upstream/downstream, not peer conflict. |
| **Transformation rule vs reporting rule** | Category error: TRANSFORM decides content; REPORT is a pure projection of the committed outcome. The outcome wins; the report describes it. | Different phases; L3 has no authority over content. |

---

## 3. Rewrite guarantees

These are the long-term invariants of every rewrite. Each has an id, a precise statement, an enforcement mode, and a mapping to the existing contract invariants so this is an *extension*, not a parallel system. **Enforcement mode** is stated honestly: *hard* guarantees are mechanically checkable and fail-closed; *judged* guarantees are evaluated by a semantic eval suite with a defined bar (they cannot be proven by a substring check, and the design does not pretend otherwise).

The anchor, from the Rewrite Report contract, is binding on all of them: **a rewrite may make intent more explicit, never less, and may use only facts the user actually supplied.**

| ID | Guarantee | Statement | Mode | Maps to |
|---|---|---|---|---|
| **RG-1** | Meaning preservation | The rewrite's set of task-intents is a superset of the original's and introduces no new task-intent. Clarification is addition of *explicitness*, not addition of *goals*. | Judged (meaning-preservation suite) + bounded by RG-6/RG-7 | new; bounds the "more explicit, never less" rule |
| **RG-2** | Explicitness monotonicity | Explicitness of stated intent may only increase relative to the original. A rewrite never makes intent *less* legible. | Judged | Rewrite Report anchor |
| **RG-3** | Structure preservation | Embedded material the user supplied (data blocks, quoted text, examples) is preserved or reorganized; it is never deleted in a way that changes meaning, nor fabricated. | Hard (data/example segments must trace to source spans) | IR segment kinds |
| **RG-4** | Honesty | Every statement in the report is an Observed fact or a labelled Estimate; the non-guarantee notice is attached whenever a rewrite text exists. | Hard | RW-2, §5 |
| **RG-5** | Evidence preservation | Every evidence quote and IR segment text is a verbatim substring of its reference prompt. | Hard | RPT-1, IR-1, PR-1 |
| **RG-6** | No intent laundering | No prohibited transformation is applied: no fictional/hypothetical reframing to change the policy reading, no semantic dilution, no splitting a request across parts to distribute intent, no encoding/obfuscation. | Hard (prohibited-transformation checklist) + red-team suite | ETHICS policy; §4 |
| **RG-7** | No fabricated context | The rewrite introduces no facts, credentials, authorization, roles, or background the user did not supply. | Hard (every asserted fact must trace to a source span) | Rewrite Report anchor |
| **RG-8** | No invented examples | The rewrite does not fabricate domain examples that could be read as user-supplied facts. A purely structural output-format placeholder is permitted only if it is unmistakably a placeholder and asserts no domain content. | Hard (added example blocks must be placeholder-typed or trace to source) | RG-7 corollary |

Two design notes:

- **Hard vs judged is a first-class distinction, not a hedge.** RG-3/4/5/6/7/8 reduce to span-tracing and checklist checks that a verifier can decide deterministically. RG-1/2 are semantic and are gated by the meaning-preservation eval suite with a stated threshold; the design commits to measuring them, not to a false claim of proof.
- **A declined rewrite trivially satisfies all guarantees** (no text is produced). Guarantees constrain *produced* rewrites; the gate (§4) constrains *whether* one is produced.

---

## 4. Misuse policy (classification model)

The misuse model decides **whether rewriting is legitimate** — nothing more. It never adjudicates whether content is permitted by any provider (that is the provider's system, which the tool does not simulate or predict), and it never makes a request *more permissible*. Its wording is provider-neutral and topic-agnostic: it classifies by **intent relative to safeguards**, not by subject matter.

### 4.1 The three classes

| Class | Definition | Analyzer action |
|---|---|---|
| **Legitimate** | A plausible benign reading exists and is consistent with the user's stated purpose and the conversation context; the request is not primarily aimed at defeating a safety system. | Rewrite permitted (`gate: passed`, or `conditional` when the same visible behavior may still occur). |
| **Ambiguous** | Purpose is unstated and a harmful reading is plausible alongside a benign one. | **Do not guess.** Elicit the purpose; treat the answer as stated context and re-classify. Absent clarification, fail closed — no rewrite that resolves the ambiguity in the permissive direction. |
| **Prohibited** | The evident purpose is to bypass, evade, or defeat a safety system, or there is no plausible legitimate reading. | Decline the rewrite (`gate: declined`); still explain the observable event honestly. |

### 4.2 The distinguishing procedure (provider-neutral)

The analyzer distinguishes the classes by a fixed procedure, not by pattern-matching topics:

1. **Dual-reading construction.** Construct the most-plausible-legitimate reading and the most-plausible-harmful reading of the request together with any stated purpose and context.
2. **Safeguard-targeting test.** Does the request's evident aim include defeating, evading, or getting content past a safety system (as opposed to accomplishing a benign task)? If yes → **Prohibited**.
3. **Legitimate-reading test.** Is there a plausible benign reading consistent with stated purpose/context? If none → **Prohibited**.
4. **Sufficiency test.** Is purpose stated (or clearly implied) enough to select the legitimate reading over the harmful one? If not, and a harmful reading is plausible → **Ambiguous** (elicit).
5. **Otherwise → Legitimate.**

The outcome and the triggering step are recorded in the Rewrite Report (`gate`, `gate_reason`), so the classification is auditable and testable.

**How this is represented as data.** The conditional dispatch above ("if yes → Prohibited") describes what the *analyzer code* does — it is this document's narrative of the decision procedure, not the shape of the policy file. Under the purely-declarative mandate, the implemented `misuse-policy.json` encodes the procedure as an **ordered checklist of prose steps** (registry ids `MISUSE-010`–`MISUSE-014`) with no branching fields; the analyzer walks the steps in order and owns all dispatch. See [policy-schemas.md](policy-schemas.md) for why a decision-tree-as-data was rejected.

### 4.3 Separation of concerns (critical)

- **Neutral vs provider.** Steps 1–5 are neutral and live in the `common` pack. *What topics a specific provider's classifiers are sensitive to* is provider knowledge (dated claims in a provider pack) and feeds only the **Estimated** layer of the report — "factors that may have contributed to what you observed" — never the gate decision. The gate does not encode "cyber" or "bio"; it encodes "is this an attempt to defeat a safeguard."
- **The gate is one-directional.** It can `decline` or `permit`; it can never make a request more acceptable to a provider. Legitimacy of *rewriting for clarity* is orthogonal to whether a provider will accept the content — which the tool states plainly (the non-guarantee notice).
- **Bridge to the guarantees.** A legitimate rewrite makes stated intent *more* explicit (RG-1/RG-2) using only user-supplied facts (RG-7); it never disguises intent (RG-6). This is why "make intent more explicit, never less" is the seam between the misuse model and the rewrite guarantees.

---

## 5. Reporting philosophy

Reporting (L3) turns committed decisions into what the user reads. It is a projection; it adds no conclusions of its own.

### 5.1 What the analyzer *may* conclude

- **Observed facts:** what the user saw, quoted verbatim, classified against a taxonomy entry whose provenance chain (entry → claim → dated public source) is intact.
- **Prompt-quality findings:** rubric findings, each tied to a verbatim evidence quote (RG-5).
- **Rewrite outcome:** that a rewrite was produced or declined, and the reason, per the gate.

### 5.2 What the analyzer *must not* conclude

- Anything about a provider's internal systems — moderation logic, classifier thresholds, routing.
- **Causation** of a safeguard event stated as fact ("your prompt was flagged *because* X"). Causal hypotheses live only in the Estimated layer, labelled.
- Any **guarantee** about future model behavior. The non-guarantee notice is mandatory (RG-4 / RW-2).

### 5.3 Confidence model

Two report layers, one confidence rule:

- **Observed** is fact. It carries no confidence label because it is quoted evidence tied to a source.
- **Estimated** is hypothesis. Every estimate carries an explicit label — **High / Medium / Low** — with one sentence of reasoning. There is no unlabelled speculation.

| Label | Meaning |
|---|---|
| High | Directly supported by the prompt's content and documented behavior; a competent reviewer would likely agree. |
| Medium | Plausible and supported, but a reasonable reviewer might weigh it differently. |
| Low | A candidate factor offered for completeness; weakly supported. |

### 5.4 Evidence requirements and uncertainty

- **Evidence:** every finding cites a verbatim substring; every observed-event classification cites a taxonomy entry with an intact claim chain; every estimate cites its reasoning (it does not cite a source it does not have).
- **Unknown events:** classified `kind: unknown` and stated as such — "this matches no documented pattern in taxonomy version *v*" — with no causal claim.
- **Missing evidence:** the finding is withheld. Absence of evidence is never upgraded to a confident claim.
- **Explicit "cannot conclude":** where the honest boundary is reached (e.g., a consumer surface's undocumented behavior), the report says so, citing the claim that establishes the boundary.

---

## 6. Policy schema (implemented — see policy-schemas.md)

Policy is **validated data with prose companions**, exactly like the rubric (`rubric.json` + `rubric.md`): the parts of policy that must be machine-checked are structured JSON so they can be validated, diffed, and tested; the human exposition is a Markdown companion, inside the existing pack conventions and the recursion-free schema subset.

This was resolved as **Option A** (schemas as validated data) under an approved frozen-baseline exception, refined by four review requirements — stable permanent registry ids, independent `schema_version`/`policy_version` axes, documented per-schema compatibility rules, and maintainer-facing `rationale` on every entry — and implemented in FR-3. The authoritative field-by-field specification is **[policy-schemas.md](policy-schemas.md)**; the earlier per-field sketches this section once carried (including a `procedure` shape with branching `on_yes`/`on_no` fields) are superseded — the branching representation was **rejected** by the purely-declarative mandate and replaced with an ordered prose checklist (§4.2).

What exists in the repository:

| Artifact | Location |
|---|---|
| Schemas | [`core/contracts/knowledge/`](../../core/contracts/knowledge/CONTRACT.md): [`misuse-policy.schema.json`](../../core/contracts/knowledge/misuse-policy.schema.json), [`rewrite-policy.schema.json`](../../core/contracts/knowledge/rewrite-policy.schema.json), [`notices.schema.json`](../../core/contracts/knowledge/notices.schema.json) |
| Policy data | `core/knowledge/packs/common/`: [`misuse-policy.json`](../../core/knowledge/packs/common/misuse-policy.json), [`rewrite-policy.json`](../../core/knowledge/packs/common/rewrite-policy.json), [`notices.json`](../../core/knowledge/packs/common/notices.json) — canonical for all fixed wording (notice texts, decline templates) |
| Prose companions | [`misuse-policy.md`](../../core/knowledge/packs/common/misuse-policy.md), [`rewrite-policy.md`](../../core/knowledge/packs/common/rewrite-policy.md), [`notices.md`](../../core/knowledge/packs/common/notices.md) — derived exposition; fixed wording is quoted verbatim and drift-checked |
| Invariants | PL-1..PL-8 in [CONTRACT-INVARIANTS.md](../CONTRACT-INVARIANTS.md), guarded by `tests/test_knowledge_integrity.py` |
| Governance | [docs/process/policy-review.md](../process/policy-review.md) — how the policy data evolves |

---

## 7. Extensibility

The model adds providers without touching the neutral procedure or any global invariant:

- **A new provider = a new pack.** It supplies its own claims, techniques, event taxonomy, and patterns, and *may* supply provider-specific sensitivities that inform the Estimated layer. It is registered in the knowledge manifest; the loader composes `common` (L1) + the provider pack (L2).
- **Providers never edit L0 or L1.** The misuse procedure, the rewrite guarantees, and the notices are shared neutral content. A provider cannot relax them — an attempt is a load-time error (§2.1).
- **Composition is additive and validated.** Provider policy can only *narrow* permissions or *add* evidence. The static contradiction check proves a new pack has not weakened the constitution before it can be used.
- **Reporting adapts automatically.** Because L3 projects committed outcomes, a new provider's taxonomy prose flows into reports without any change to reporting rules.

The result: onboarding a second provider is a data exercise (author a pack, cite sources, pass the integrity tests), not a code or policy-procedure change — the same property ADR-0007 established for knowledge generally.

---

## 8. Testing strategy

Policy correctness is verified the way contract invariants already are: reference checkers with **compliant and violating** fixtures now, promoted to runtime enforcement in the verifier (M2). Six test classes:

1. **Invariant tests.** Each global invariant (L0) and each rewrite guarantee (RG-*) gets an executable check with a passing fixture and at least one violating fixture, so an incorrect implementation fails. Fail-closed defaults are asserted (missing/malformed policy ⇒ safe outcome).
2. **Regression tests (decision snapshots).** Golden fixtures map scenarios (prompt + optional event) to expected *decisions* — gate outcome, misuse class, applied/withheld transformations, finding dimensions. Snapshots capture the decision, not the prose, so wording can evolve while behavior is pinned. A policy edit that silently changes a decision fails the snapshot.
3. **Contradiction detection.** A static check over the loaded corpus asserting: no L2 rule relaxes an L0/L1 invariant; no rule set is internally inconsistent; every citation resolves; provenance holds (KN-1/KN-2). This is the executable form of §2.1.
4. **Conflict tests.** Targeted fixtures for the three named conflict cases (§2.3) asserting the deterministic resolution (invariant beats provider rule; gate precedes transform; report cannot alter outcome).
5. **Adversarial / red-team tests.** The misuse gate is exercised against laundering attempts (fabricated context, fictional reframing, semantic dilution, request-splitting, encoding) drawn from `evals/red-team-rewrite`; every such fixture must yield `gate: declined`. This is a release gate.
6. **Determinism tests.** The same input evaluated repeatedly yields the same decision; tiebreaks resolve to stable ids; no output depends on unordered iteration. Reproducibility is itself asserted.

All six extend the existing test architecture and pass under the current gate; none requires runtime analyzer code to be meaningful (the reference-checker pattern already used for RW-*/EV-*/PR-* applies).

---

## Relationship to FR-3 (completed) and what remains

FR-3 implemented this design as data: the `common`-pack `misuse-policy`, `rewrite-policy`, and `notices` files exist, their procedure, transformation lists, guarantees, and notice texts match §§3–5, and the integrity checks that are meaningful without an engine (id discipline, reference resolution, provenance, neutrality, JSON/Markdown consistency) run in `tests/test_knowledge_integrity.py`. Nothing in the authored policy introduces a rule this design forbids, and nothing weakens a global invariant.

What remains for M2–M4: the engine that evaluates this data (load-time corpus validation §2.1, phase-ordered runtime evaluation §2.2, the verifier for the hard guarantees §3), the decision-snapshot and red-team suites of §8 that need a running gate, and report/persistence integration. Policy content changes from here follow [docs/process/policy-review.md](../process/policy-review.md).
