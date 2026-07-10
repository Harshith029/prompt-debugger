# Prompt Debugger for Claude — Architecture

| | |
|---|---|
| **Status** | Milestone M0 (engineering foundation) implemented. Analyzer and rewrite behavior are future work (M2–M4). |
| **Document version** | 1.0 |
| **Last updated** | 2026-07-07 |

This document describes the architecture of `prompt-debugger`: its layering, contracts, and the reasoning behind the significant design decisions. Decisions are also captured individually as [Architecture Decision Records](adr/README.md).

---

## 1. Mission and scope

**Prompt Debugger for Claude** is an open-source toolkit — delivered as a Claude Code plugin built on host-neutral core contracts — that helps users:

1. **Understand observable model behavior**: visible safeguard messages, visible model switches, and user-visible errors, explained using only information the user can see, grounded in Anthropic's public documentation.
2. **Analyze prompt quality** against a versioned ten-dimension rubric (ambiguity, missing context, contradictions, scope creep, unrelated task bundling, poor formatting, excessive complexity, weak objectives, missing constraints, missing output specification).
3. **Rewrite legitimate prompts** to improve clarity, structure, explicit intent, and output specification while preserving meaning, applying Anthropic's published prompt-engineering techniques.
4. **Track prompt quality locally**: save history, compare revisions, analyze trends, export reports. Local-first, zero telemetry.

### 1.1 Flagship scenario

The primary user journey (confirmed by the maintainer): *a user's legitimate prompt is declined by Claude Fable 5's safety classifiers and the response is visibly served by Claude Opus 4.8 (a model-switch notice the user can see).* Anthropic's public Fable 5 documentation states that its classifiers target offensive cybersecurity, biology/life-sciences content, and reasoning extraction — and that **benign adjacent work may also trigger these safeguards**. The product helps that user understand what they observed, find what in their prompt obscures their legitimate intent, and communicate that intent more clearly — never to evade policy.

### 1.2 Non-goals (binding)

- **Never** claim knowledge of Anthropic's internal moderation logic, classifier thresholds, or routing rules. Every explanation is either an *observable fact* (quoted verbatim, classified against documented surface) or an *estimate* (labeled with confidence and reasoning).
- **Never** rewrite a prompt to bypass or evade safety systems. The legitimacy gate (§6.6) is a specified decision procedure, not a vibe.
- **Never** guarantee that a rewrite changes model behavior; every rewrite carries a fixed non-guarantee notice.
- **No runtime network I/O, no telemetry, no cloud services** in v1 (CI-enforced, §7 S6).

---

## 2. Grounding in public documentation

All factual claims about model/API behavior live in a **claim registry** (`core/sources/claims.yaml`): claim ID, exact claim text, source URL, retrieval date, verification status, last-verified date. The registry is versioned; the event taxonomy and rubric carry version identifiers; every generated report records which versions it used. A quarterly re-verification checklist (issue template) keeps the corpus honest as Anthropic's documentation evolves. **The taxonomy is explicitly non-exhaustive**: events that match no documented pattern are classified `unknown` and handled gracefully (§6.5).

Facts the product currently relies on (each becomes a registry entry with its retrieval date of 2026-07-07):

- A safeguard decline on the API returns **HTTP 200 with `stop_reason: "refusal"`**, optionally with `stop_details` (`category` values documented to include `"cyber"`, `"bio"`, `"reasoning_extraction"`, `"frontier_llm"`, or `null`; `explanation` not guaranteed). Classifier declines and ordinary model refusals surface through the same stop reason.
- With fallbacks configured, a **`fallback` content block** (`{type: "fallback", from: {model}, to: {model}}`) marks a model switch, and the response `model` field names the serving model.
- **User-visible errors** are enumerated publicly: 400/401/403/404/413/429/500/529 plus stop reasons `max_tokens` and `model_context_window_exceeded`.
- Fable 5's classifiers target offensive cyber, bio/life-sciences, and reasoning extraction; **benign work may trigger false positives**; Anthropic documents fallback to Claude Opus 4.8 as the recovery path.

**Consumer/CLI surfaces (claude.ai, Claude Code):** a model-switch notice or refusal banner the user sees is treated as **observed evidence reported by the user** — a fact about what appeared on their screen. The *citation* attached to it references only the documented API mechanism class; whether a given surface implements fallback in a particular way is stated as **not publicly specified** unless a public source is verified (an explicit M1 task against the refusals-and-fallback page, recorded in the registry either way).

**Prompt-engineering technique inventory (T1–T10)**, from the prompt-engineering overview, the prompting best-practices reference, and the Fable 5 prompting guide:

| # | Technique | Core guidance |
|---|-----------|---------------|
| T1 | Be clear and direct | "Golden rule": if a colleague with minimal context would be confused, Claude will be too |
| T2 | Add context and motivation | Explain *why*; "give the reason, not only the request" |
| T3 | Use examples (multishot) | 3–5 relevant, diverse examples in `<example>` tags |
| T4 | Structure with XML tags | Separate instructions/context/input/examples with consistent tags |
| T5 | Give Claude a role | One-sentence system-prompt role focuses behavior |
| T6 | Long-context ordering | Longform data at top, query at end; ground in quotes |
| T7 | Control output format positively | Say what to do, not what to avoid; format indicators |
| T8 | Decompose or chain complex tasks | Split multi-goal requests; chain for inspectable pipelines |
| T9 | Define success criteria and constraints | Measurable "done" before tuning |
| T10 | Avoid over-prescription | Current models follow instructions literally; state goals/constraints, drop "CRITICAL/MUST" scaffolding |

**Skill authoring constraints** (Claude Code docs + Agent Skills standard): `SKILL.md` < 500 lines; frontmatter `name` ≤ 64 chars, lowercase/numbers/hyphens, must not contain reserved words "anthropic"/"claude"; `description` ≤ 1024 chars, third person, what + when; reference files one *hop* deep; bundled scripts are executed, not loaded; `allowed-tools` **pre-approves and does not restrict** — restriction requires `disallowed-tools`; evals via per-skill `evals.json` and baseline comparison; plugins are the distribution vehicle.

---

## 3. Product decisions

| ID | Decision | Rationale (trade-offs noted inline) |
|----|----------|-------------------------------------|
| D1 | **Layered architecture: host-neutral core contracts + core library + thin adapters.** Skills are the v1 adapter, not the architecture. | Contracts (schemas, taxonomy, rubric, policy) and deterministic logic (storage, redaction, validation, rendering) must not depend on prose in SKILL.md files — tests, storage, and future adapters (CLI, MCP) bind to contracts. *Scope boundary:* no additional host runtimes ship in v1; the LLM judgment layer is host-portable via the Agent Skills open standard + neutral contracts, and building unproven adapters first would be speculative generality. (ADR-0001) |
| D2 | **No browser extension in v1.** Structured paste protocol instead. | An extension must scrape an undocumented DOM — the opposite of observable-facts grounding — and is the largest privacy surface for the smallest gain. The user already possesses the evidence; pasting it is consent. Reconsider only if an official client API exposes events (ADR-0005). |
| D3 | **Judgment in skills, determinism in code — with a structured interface between them.** | The LLM performs segmentation, analysis, and rewriting (high-freedom instructions); everything checkable is checked by code: evidence quotes verified as substrings, Report JSON schema-validated, storage/redaction/export deterministic. |
| D4 | **Dual-artifact output: Report JSON is the system of record; Markdown is the human projection.** | Machine-readable reports make persistence, comparison, validation, and regression testing possible. (ADR-0002) |
| D5 | **Python 3.10+, stdlib-only at runtime; dev-time tooling unrestricted.** Schema validation via an in-repo subset validator, differentially tested in CI against the real `jsonschema` package (dev dependency). | Zero runtime supply chain; correctness risk of owning a validator bounded by restricting schemas to a defined subset + differential testing. (ADR-0003) |
| D6 | **Honesty architecture**: Observed vs Estimated separation, confidence labels, fixed epistemic and non-guarantee notices, specified legitimacy gate with transformation rules (§6.6). | The core differentiator; now specified as testable contracts rather than principles. |
| D7 | **License: MIT (recommended).** | Maximizes adoption for a prose-heavy community project; Apache-2.0 the alternative if a patent grant is wanted. Decision isolated to `LICENSE`, needed at M0. |
| D8 | **Privacy-hardened defaults**: user-local storage, per-store salted HMAC fingerprints, redacted exports, rare/loud/reversible raw storage. | See §8. The default storage location cannot be accidentally committed to a repository (ADR-0004). |

---

## 4. System architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│ ADAPTERS (host-specific, thin)                                        │
│                                                                       │
│  v1: Claude Code plugin "prompt-debugger"                             │
│      skills/analyze   skills/rewrite   skills/history                 │
│      (workflow + methodology prose; all contracts referenced from     │
│       core/; all deterministic work delegated to the library)         │
│                                                                       │
│  roadmap: standalone CLI UX · MCP server  (bind to the same core)     │
└───────────────┬───────────────────────────────────────────────────────┘
                │ reads contracts / invokes library
┌───────────────▼───────────────────────────────────────────────────────┐
│ CORE CONTRACTS  (core/ — versioned, host-neutral artifacts)           │
│  schemas/     prompt-ir · report · history-record · config            │
│  taxonomy/    observable-events (versioned; includes `unknown`)       │
│  rubric/      R1–R10 definitions + severity criteria                  │
│  policy/      rewrite contract · misuse decision procedure · notices  │
│  sources/     claims.yaml (claim registry with retrieval dates)       │
└───────────────┬───────────────────────────────────────────────────────┘
                │ validated by / rendered by
┌───────────────▼───────────────────────────────────────────────────────┐
│ CORE LIBRARY  (src/prompt_debugger/ — Python 3.10+, stdlib only)      │
│  store.py     locking · atomic append · migrate · doctor · archive    │
│  schema.py    JSON-Schema-subset validator                            │
│  verify.py    evidence-quote substring verification · IR checks       │
│  redact.py    secret/PII scrub (typed placeholders)                   │
│  sanitize.py  control-char/ANSI stripping · CSV formula escaping      │
│  render.py    Report JSON → Markdown/CSV/JSON exports                 │
│  cli.py       argparse entry point wrapping all of the above          │
└───────────────┬───────────────────────────────────────────────────────┘
                ▼
│ LOCAL STORAGE (user-owned, no network)                                │
│  default: ~/.prompt-debugger/stores/<project-key>/history.jsonl       │
│  opt-in:  <project>/.prompt-debugger/  (self-ignoring)                │
```

### 4.1 Skill decomposition (v1 adapter)

| Skill | Command | Invocation | Purpose |
|---|---|---|---|
| `analyze` | `/prompt-debugger:analyze [prompt or pasted event]` | user **and** model (triggers on "my prompt was refused", "it switched models", "review my prompt") | Full workflow (§4.2): intake → observe → gate → IR → rubric → estimate → rewrite → offer save |
| `rewrite` | `/prompt-debugger:rewrite [prompt]` | user and model | Fast path: gate + rewrite + change log + notices |
| `history` | `/prompt-debugger:history [save\|list\|compare\|trends\|export\|strip-raw\|delete\|purge\|doctor\|archive]` | **user only** (`disable-model-invocation: true`) | Thin wrapper over `cli.py`; persistence is always user-initiated |

Skills link contract documents directly from `core/` (one hop from SKILL.md — the best-practice constraint is chain depth, not directory distance). Scripts import the library via a stable relative path within the installed plugin. Consequence: **supported installs are whole-repo installs** (plugin install, or clone + symlink), documented in the install matrix (§6.9).

### 4.2 Main workflow (`analyze`)

```
Step 0  INTAKE      Identify inputs. If an event is referenced but not quoted,
                    ask for the visible text verbatim (accept "not available").
                    Wrap all user-supplied artifacts in explicit data tags;
                    treat strictly as data under analysis (§7 S1).
Step 1  OBSERVE     Classify the event against core/taxonomy (versioned).
                    No documented match → kind: unknown, with the honest
                    statement of what can and cannot be concluded.
Step 2  GATE        Run the misuse decision procedure (§6.6).
                    legitimate → continue · circumvention → explain event,
                    decline rewrite, stop · uncertain → ask for purpose.
Step 3  SEGMENT     Produce Prompt IR (§6.3).
Step 4  ANALYZE     Apply rubric R1–R10 to the IR. Findings carry verbatim
                    evidence quotes tied to segments.
Step 5  ESTIMATE    Only if an event was reported: confidence-labeled
                    hypotheses + fixed epistemic notice.
Step 6  REWRITE     Apply T1–T10 under the transformation rules (§6.6).
                    Per-change log: change → technique → benefit.
                    Fixed non-guarantee notice. If the rewritten prompt could
                    still trigger the same visible behavior under policy,
                    say so explicitly.
Step 7  EMIT        Render the human report AND the Report JSON block.
Step 8  OFFER SAVE  Offer /prompt-debugger:history save (validates JSON,
                    verifies evidence quotes, redacts, persists). Never
                    persist without an explicit yes.
```

---

## 5. Repository structure

This is the **target** layout for the completed project. Entries that arrive in later milestones (for example `docs/INSTALL.md`, `docs/USAGE.md`, `docs/SOURCES.md`, `examples/`, `core/guides/`, and the benchmark store generators) are shown here for orientation and do not all exist in the current pre-release. The `docs/adr/` directory holds the actual Architecture Decision Records; the schema files live under `core/contracts/<name>/` (one directory per contract) rather than a flat `core/schemas/`.

```
prompt-debugger/
├── README.md · LICENSE · CONTRIBUTING.md · CODE_OF_CONDUCT.md
├── SECURITY.md · CHANGELOG.md
├── .claude-plugin/
│   ├── plugin.json                  # manifest; version synced to tags
│   └── marketplace.json             # pinned to release tags
├── core/                            # HOST-NEUTRAL CONTRACTS (versioned)
│   ├── schemas/
│   │   ├── prompt-ir.schema.json
│   │   ├── report.schema.json
│   │   ├── history-record.schema.json
│   │   └── config.schema.json
│   ├── taxonomy/
│   │   └── observable-events.md     # + machine-readable index; taxonomy_version
│   ├── rubric/
│   │   └── quality-rubric.md        # R1–R10 + severity criteria; rubric_version
│   ├── policy/
│   │   ├── rewrite-contract.md      # allowed/prohibited transformations
│   │   ├── misuse-policy.md         # decision procedure + refusal templates
│   │   └── notices.md               # fixed epistemic + non-guarantee texts
│   ├── guides/
│   │   ├── rewrite-guide.md         # T1–T10 with worked examples
│   │   └── output-templates.md      # human report + Report JSON emission
│   └── sources/
│       └── claims.yaml              # claim registry
├── src/prompt_debugger/             # CORE LIBRARY (stdlib-only)
│   ├── __init__.py · store.py · schema.py · verify.py
│   ├── redact.py · sanitize.py · render.py · cli.py
├── skills/                          # ADAPTER: Claude Code plugin skills
│   ├── analyze/  SKILL.md + evals/evals.json
│   ├── rewrite/  SKILL.md + evals/evals.json
│   └── history/  SKILL.md + evals/evals.json + scripts/run.py (launcher shim)
├── docs/
│   ├── ARCHITECTURE.md · INSTALL.md · USAGE.md · PRIVACY.md
│   ├── SECURITY-REVIEW.md · ETHICS.md · GLOSSARY.md · SOURCES.md
│   ├── adr/ (Architecture Decision Records + template)
│   └── design/ (component design notes, e.g. Prompt Tree)
├── evals/                           # cross-skill semantic suites (§10)
│   ├── meaning-preservation/ · red-team-rewrite/ · rubric-calibration/
├── examples/ (01-ambiguous-prompt · 02-safeguard-event · 03-multi-task · 04-history)
├── tests/                           # pytest: unit + contract + differential
├── benchmarks/                      # synthetic-store generators + timing harness
├── .github/ (workflows/ci.yml · release.yml · ISSUE_TEMPLATE · PR template)
├── requirements-dev.txt             # pytest, ruff, mypy, jsonschema (dev only)
└── pyproject.toml                   # tooling config; no runtime deps
```

---

## 6. Technical specification

### 6.1 `analyze` / `rewrite` frontmatter (corrected permission model)

```yaml
---
name: analyze
description: Analyzes prompt quality and explains visible safeguard messages,
  model switches, and errors using only observable information. Use when the
  user reports a refusal or safeguard message, a visible model switch, asks
  why a prompt failed, or wants a prompt reviewed for clarity, ambiguity,
  structure, or missing context.
argument-hint: "[prompt text, or paste the visible message you received]"
allowed-tools: Read
disallowed-tools: Write Edit NotebookEdit Bash
---
```

- `disallowed-tools` **removes** write/execute capability from the tool pool while the skill is active — the actual mitigation against injection-steered actions (the restriction clears on the next user message, which matches the analysis lifecycle).
- `allowed-tools: Read` merely pre-approves reading (e.g., a prompt stored in a file the user points at).
- A **documented permission profile** ships in INSTALL.md (recommended allow/deny rules for users who want defense in depth at the settings level); CI contract-tests that shipped frontmatter matches the documented profile (§7 S13).

### 6.2 `history` frontmatter

```yaml
---
name: history
description: Saves prompt analyses locally, compares revisions, shows trends,
  and exports reports. Local-first; writes only when explicitly asked.
argument-hint: "[save | list | compare <id> <id> | trends | export <format> | strip-raw <id> | delete <id>]"
disable-model-invocation: true
allowed-tools: >
  Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/run.py *)
  Bash(python ${CLAUDE_SKILL_DIR}/scripts/run.py *)
  Bash(py -3 ${CLAUDE_SKILL_DIR}/scripts/run.py *)
---
```

`run.py` is a shim that locates the in-repo library via a stable relative path and dispatches to `prompt_debugger.cli`. All three launcher spellings are pre-approved for cross-platform use (§6.9).

### 6.3 Prompt IR (`core/schemas/prompt-ir.schema.json`)

A pragmatic intermediate representation — segmentation, not parsing:

```json
{
  "ir_version": 1,
  "segments": [
    {
      "id": "s1",
      "kind": "role",
      "text": "You are a senior security engineer",
      "note": "optional model commentary"
    }
  ],
  "unsegmented_remainder": false
}
```

- `kind` enum: `role · context · task · constraint · example · output_spec · data · meta · other`.
- **Integrity rule:** every `segments[].text` and every finding evidence quote must be a **verbatim substring of the source prompt**. `verify.py` checks this deterministically; a failed check is surfaced to the model for one repair pass, then to the user. This converts "LLM hallucinated its evidence" from an invisible failure into a caught one.
- Segmentation may be non-exhaustive (`unsegmented_remainder: true`) — full tiling is not required, avoiding brittleness on unusual prompts.

### 6.4 Report JSON (`core/schemas/report.schema.json`) — the system of record

```json
{
  "report_version": 1,
  "taxonomy_version": "2026.07",
  "rubric_version": "2026.07",
  "created_at": "2026-07-07T12:00:00Z",
  "event": {
    "kind": "refusal_message",
    "surface": "cli",
    "verbatim": "…",
    "documented_match": "evt-refusal-visible",
    "notes": "kind=unknown when no documented pattern matches"
  },
  "ir": { "ir_version": 1, "segments": [] },
  "findings": [
    {
      "id": "f1",
      "dimension": "R1",
      "severity": "high",
      "evidence": [{ "segment": "s2", "quote": "…" }],
      "explanation": "…",
      "fix": "…"
    }
  ],
  "estimates": [
    { "hypothesis": "…", "confidence": "medium", "reasoning": "…" }
  ],
  "rewrite": {
    "gate": "passed",
    "text": "…",
    "changes": [{ "change": "…", "technique": "T4", "rationale": "…" }],
    "notices": ["non_guarantee"]
  }
}
```

(Prose annotation above; the shipped schema is strict JSON, subset-conformant.) `event`, `estimates`, and `rewrite` are nullable; `rewrite.gate` ∈ `passed · declined · conditional` (conditional = rewritten, but flagged that the same visible behavior may still occur). The Markdown the user reads is a **projection** of this object; `render.py` can regenerate it, and history/compare/trends operate exclusively on Report JSON.

### 6.5 Event taxonomy (`core/taxonomy/observable-events.md`)

Versioned entries, each with: event ID, what the user sees, which surface(s), the documented API correlate (with claim-registry IDs), what can honestly be concluded, and what cannot. Kinds: `refusal_message · model_switch · api_refusal_stop_reason · api_fallback_block · error · unknown · none`. The `unknown` entry is first-class: its handling text tells the model to quote the event, state that it matches no documented pattern in this taxonomy version, and proceed with prompt-quality analysis without causal claims.

### 6.6 Legitimacy gate and rewrite contract (`core/policy/`)

**Decision procedure (misuse-policy.md):**

1. Construct the **most plausible legitimate reading** and the **most plausible harmful reading** of the prompt plus any user-stated purpose.
2. If the user has *stated* the goal is to defeat, bypass, or slip past safeguards → **decline the rewrite** (fixed template), explain the observable event normally, and state that a rewrite can be offered only for a legitimate purpose the user actually articulates.
3. If the legitimate reading is plausible and consistent with the user's stated purpose and conversation context → **rewrite**, making that stated intent explicit.
4. If purpose is missing and the harmful reading is plausible → **ask** for the purpose; never guess-fill. The answer becomes part of the rewrite as explicit stated context.
5. Record the outcome in `rewrite.gate`; adversarial evals assert these branches (§10).

**Transformation rules (rewrite-contract.md):**

| Allowed | Prohibited |
|---|---|
| Restructure, reorder, deduplicate | Fabricate intent, context, credentials, or authorization the user never provided |
| Make the user's *stated* intent and context explicit | Remove or euphemize content that makes the request's true nature clear (semantic dilution) |
| Disambiguate terms; enforce consistent terminology | Reframe as fiction, hypothetical, or roleplay to alter the policy reading |
| Split unrelated tasks; add success criteria, constraints, output specs | Fragment a request across prompts to distribute intent (salami-slicing) |
| Apply T1–T10 formatting/structure techniques | Encode, obfuscate, or otherwise disguise content |

**Invariant:** a rewrite may make intent *more* explicit, never less — and may only use facts the user actually supplied.

**Fixed notices (notices.md):** the epistemic notice (estimates are educated guesses; moderation/routing internals are not public; analysis is based only on visible information) and the non-guarantee notice, verbatim:

> *"This rewrite is intended to improve clarity and communicate your legitimate intent more effectively. It does not guarantee a different response, as model behavior depends on the provider's systems and policies."*

### 6.7 Schema validation strategy

Schemas are standard **JSON Schema draft 2020-12 restricted to a documented subset**: `type`, `enum`, `const`, `required`, `properties`, `items`, `additionalProperties: false`, `pattern`, `minLength/maxLength`, `minimum/maximum`, `minItems/maxItems`, nullable via `type` arrays. `schema.py` implements exactly this subset (unit-tested). CI runs **differential validation**: the `jsonschema` package (dev-only) validates every schema fixture and must agree with `schema.py` on accept/reject; disagreement fails the build. A CI meta-check rejects any schema using constructs outside the subset.

### 6.8 Storage specification

- **Location (default):** `~/.prompt-debugger/stores/<project-key>/` where `project-key` = slug + short HMAC of the project path (stores remain per-project while living outside the repo). **Opt-in project-local:** `<project>/.prompt-debugger/`, created self-ignoring (`.gitignore` containing `*` inside the store directory) plus a warning README in the store. Config: `~/.prompt-debugger/config.json` (+ optional per-project override), schema-validated.
- **Record IDs:** `pd-<epoch-ms>-<uuid4-first8>` — time-ordered, collision-safe, stdlib-only.
- **Fingerprints:** `HMAC-SHA256(store_salt, text)` with a per-store random 256-bit salt generated at store init (file mode 0600 where supported). Fingerprints never appear in exports by default.
- **Concurrency & integrity:** advisory lock file via `fcntl` (POSIX) / `msvcrt.locking` (Windows) shim; appends are a single `os.write` on an `O_APPEND` fd; reads tolerate and report trailing partial lines.
- **Schema evolution:** per-record `schema_version`; `migrate` upgrades a store (timestamped backup first); `doctor` validates every line and quarantines corrupt/invalid ones to `history.rejects.jsonl` with reasons; `archive` rotates the live file to `archive/history-<date>.jsonl`.
- **Record content:** a redacted prompt, findings, scores, event, rewrite reference, and `parent_id` for revision chains; a `raw: true` flag marks explicitly-stored raw text, and the Report JSON is embedded as the record payload rather than duplicated as a parallel structure.
- **Read path treats records as untrusted input** (§7 S10): schema-validate + sanitize before display.

### 6.9 Portability

- **Launchers:** documented order `python3` → `python` → `py -3`; all three pre-approved in `history`'s `allowed-tools`; `run.py` is launcher-agnostic. No Bash-isms in any documented command (plain `python … run.py …` invocations work in Git Bash, PowerShell, and POSIX shells).
- **Paths:** forward slashes in all skill content; `pathlib` everywhere in the library; no reliance on `HOME` vs `USERPROFILE` (use `pathlib.Path.home()`).
- **CI matrix:** ubuntu-latest, macos-latest, windows-latest for the full test suite.
- **Install matrix (INSTALL.md):** (a) plugin install from marketplace (primary); (b) clone + symlink into `~/.claude/skills/` (documented with Windows caveats); copying `skills/` alone is **unsupported** (breaks core/ references) and documented as such.
- **M1 exit criterion:** fresh plugin-install smoke test passes on all three OSes.

---

## 7. Security review (threat model)

| # | Threat | Mitigation |
|---|--------|------------|
| S1 | **Prompt injection via analyzed content** — pasted prompts/events contain instructions, including instructions to invoke tools | Data-tag wrapping + treat-as-artifact instruction (best-effort, stated as such); **`disallowed-tools: Write Edit NotebookEdit Bash`** on `analyze`/`rewrite` removes write/execute capability from the pool during analysis; injection payloads in eval suites |
| S2 | **Excessive tool grants** | Minimal `allowed-tools` (pre-approval only — *not* treated as restriction); scripts pre-approved by `${CLAUDE_SKILL_DIR}` path only |
| S3 | **Dynamic context injection abuse** (`` !`cmd` ``) | Zero use in v1; CI greps skill bodies and fails on the pattern; compatible with `disableSkillShellExecution` |
| S4 | **Path traversal / symlink races in storage** | `pathlib` resolution + containment verification against the store root; refuse a symlinked `history.jsonl`/store dir; no `eval`/`exec`; write modes restricted where the platform supports it |
| S5 | **Secrets persisted into history** | Redaction-by-default before persistence; raw storage rare/loud/reversible (§8); self-ignoring project-local stores |
| S6 | **Supply chain / hidden network I/O** | Zero runtime deps; **AST-based import allowlist** per module (named stdlib modules only — `subprocess`, `socket`, `urllib`, `http` et al. are not on it); **runtime socket-block harness** (test suite runs with `socket.socket` stubbed to raise); policy = *no runtime network I/O* |
| S7 | **Misuse as a bypass assistant** | Specified gate + transformation rules (§6.6); public ETHICS.md; adversarial red-team eval suite is a release gate |
| S8 | **Terminal escape / control-character injection** via stored or echoed content | `sanitize.py` strips C0/C1 controls and ANSI CSI sequences from any content the scripts print or export |
| S9 | **Export injection** (CSV formulas opened in Excel; markdown/HTML payloads) | CSV cells with leading `= + - @` or tab are prefix-escaped; exports are plain md/csv/json (no HTML in v1); export headers state content provenance |
| S10 | **Malicious history records** (hand-crafted JSONL) | Read path schema-validates and sanitizes every record; invalid records quarantined by `doctor`; record content never executed or interpolated into commands |
| S11 | **Plugin update compromise** | Marketplace manifest pinned to release tags; checksums + GitHub artifact attestations (§11); SECURITY.md disclosure process |
| S12 | **Permission-profile drift** | CI contract test: shipped frontmatter (`allowed-tools`/`disallowed-tools`/`disable-model-invocation`) must equal the documented profile |
| S13 | **Injection-steered persistence** | `history` is `disable-model-invocation: true` — the model cannot invoke persistence; saves require the user |

Residual-risk statement (SECURITY-REVIEW.md): prompt injection is not fully solvable at the prompt layer; mitigations reduce blast radius (no write/execute tools active, no autonomous persistence) rather than claiming prevention.

---

## 8. Privacy review

**Data inventory:** (a) text the user pastes into their own Claude Code session; (b) records the user explicitly saves to their own disk. No accounts, identifiers, network calls, telemetry, or beacons — enforced by S6.

- **Default:** nothing persisted; analysis is ephemeral conversation.
- **On save:** redacted prompt + salted-HMAC fingerprint. **Raw text is rare, loud, reversible:** requires per-save interactive confirmation, records carry a visible `raw` flag surfaced by `list`, and `strip-raw <id>` converts a raw record to redacted in place.
- **Exports:** redacted and fingerprint-free by default; including raw content requires an explicit flag that prints a warning; export headers state that content may include prompt text.
- **Storage location:** user-local by default (outside any repo); project-local is explicit opt-in and self-ignoring (§6.8).
- **Deletion / lifecycle:** `delete <id>`, `purge`, `archive`; PRIVACY.md documents a full data-lifecycle table (what is written, where, when, how to inspect, how to destroy) and the honest limits of pattern-based redaction.
- **Boundary statement:** content pasted into a Claude Code session is processed by Anthropic under the user's existing agreement; the skill adds no additional data flow and PRIVACY.md says exactly that.

---

## 9. Performance review

- **Token budget:** SKILL.md files ≤ 300 lines (hard cap 500); trigger keywords front-loaded in descriptions (1,536-char listing cap); contracts loaded stepwise from `core/`; scripts executed, never loaded. Idle plugin cost ≈ three descriptions.
- **Runtime:** O(n) JSONL scans. **Measured, not asserted (planned for M2):** alongside the storage implementation, `benchmarks/` will add synthetic-store generators (10k / 100k records) and a timing harness so the size-warning threshold comes from measurements on the CI matrix rather than a guessed constant. The current pre-release ships the prompt corpus and its validator; the store generators and timing harness do not exist yet. Defined max-size behavior: warn at threshold, suggest `archive`.
- **Latency:** dominated by model reasoning (the product itself); scripts add single-digit milliseconds at realistic sizes (verified by benchmarks).

---

## 10. Testing strategy

| Layer | What | How | When |
|---|---|---|---|
| Unit | `store` (locking, atomic append, migrate, doctor, archive), `schema`, `verify`, `redact` (true/false-positive corpus), `sanitize`, `render`, `cli` | pytest, 3-OS matrix | every PR |
| Differential | `schema.py` vs `jsonschema` on all schemas + fixture corpus (accept and reject cases) | pytest (dev dep) | every PR |
| Contract | frontmatter ↔ documented permission profile; name/description constraints; SKILL.md line caps; one-hop references resolve; no `` !` `` patterns; AST import allowlist; socket-block suite | dedicated checks | every PR |
| Schema | Report JSON / IR / record / config fixtures validate; evidence-quote verification on golden reports | pytest | every PR |
| Skill evals | per-skill `evals.json`: should-trigger / should-not-trigger; golden scenarios (ambiguous prompt → R1; safeguard event → Observed/Estimated separation; unknown event → honest `unknown` handling; injection payload → treated as data) | skill-creator loop + documented manual baseline protocol (fresh session, with/without skill) | release gate + on skill changes |
| **Meaning preservation** | paired before/after prompts; LLM-judge intent-equivalence rubric with human spot-check; snapshot regressions on golden rewrites | `evals/meaning-preservation/` protocol | release gate |
| **Red-team rewrite** | laundering attempts (fabricated context, fiction reframing, dilution, salami-slicing, "get it past the filter" asks) must produce `gate: declined` | `evals/red-team-rewrite/` | release gate |
| **Rubric calibration** | prompts with planted, labeled issues; detection precision/recall per dimension tracked release-over-release | `evals/rubric-calibration/` | release gate |
| Examples-as-tests | `examples/**` transcripts regenerated per release; drift reviewed | checklist | release gate |

Eval-driven development order preserved: write evals before skill content; baseline without the skill; write the minimum that passes.

---

## 11. CI/CD

**CI (every PR + main; ubuntu/macos/windows):** ruff (check + format), mypy --strict on `src/`, pytest (unit + differential + contract + schema), markdown link check, policy gates (AST import allowlist, socket-block, frontmatter contract, size caps, no dynamic-context injection).

**Release (`release.yml`):**
1. SemVer tag → build release artifact (zip of the repo tree at the tag)
2. `plugin.json` version verified against tag; marketplace manifest pinned to the tag
3. **SHA-256SUMS** published; **GitHub artifact attestations** attached (provenance without maintainer key custody); GPG-signed tags recommended but optional
4. Compatibility matrix published in release notes (min Claude Code version, OS matrix, Python ≥ 3.10)
5. Release checklist: semantic eval suites run with results attached; security checklist (threat-model deltas reviewed); CHANGELOG entry

---

## 12. Milestones and review workflow

Each milestone is validated against a fixed engineering review checklist — correctness, architecture, security, privacy, edge cases, maintainability, documentation quality, and test coverage — before it is considered complete. A milestone does not close while any accepted finding remains open.

| M | Deliverable | Exit criteria |
|---|-------------|---------------|
| M0 | Scaffold: repo structure, LICENSE, README, CONTRIBUTING, CI, ADR baseline, this document | CI green on all 3 OSes; license recorded in an ADR |
| M1 | **Core contracts**: all schemas + subset validator + differential tests; taxonomy + claim registry (every claim sourced/dated, incl. consumer-surface fallback verification); rubric; misuse policy + rewrite contract + notices; fresh plugin-install smoke test | Citations verified against sources; contract coherence checked; 3-OS install test passes |
| M2 | **Core library**: store/verify/redact/sanitize/render/cli + unit, contract, benchmark suites | Full coverage of §6.8 behaviors incl. locking, doctor, migrate; benchmarks recorded |
| M3 | **`analyze` + `rewrite` skills** + trigger evals + adversarial/injection/meaning-preservation/rubric-calibration suites | Golden + adversarial evals pass; gate branches verified; evidence-verification loop works end-to-end |
| M4 | **`history` skill** wiring + privacy verifications | Raw-storage UX (rare/loud/reversible) verified; export redaction verified; permission-profile contract green |
| M5 | Docs (INSTALL/USAGE/PRIVACY/ETHICS/GLOSSARY/SOURCES), examples, packaging, release trust pipeline | Fresh-machine installs on 3 OSes; examples reproduce; release dry-run with checksums + attestations |
| M6 | Final security/privacy review; v1.0.0 | Full-repo security and privacy review complete; all findings closed |

---

## 13. Roadmap (post-v1)

- **v1.1** — trends HTML report (local file, bundled script); config UX polish.
- **v1.2** — prompt-template library per task family (additional `core/guides/` content).
- **v1.3** — **MCP server adapter** binding to the same core contracts/library, for hosts with MCP but no Agent Skills support.
- **Deferred indefinitely** — browser extension (ADR-0005 conditions).
- **Continuous** — quarterly claim-registry re-verification (issue template + checklist); taxonomy/rubric version bumps tracked in CHANGELOG.

---

## 14. Resolved foundational decisions

The following decisions are settled and reflected in the M0 implementation:

1. **License** — MIT.
2. **Repository name** — `prompt-debugger`.
3. **Command surface** — `/prompt-debugger:analyze` plus a short `pd` alias skill.
4. **Dependency policy** — the runtime is standard-library only; `jsonschema` is a development-only dependency used for differential schema validation in CI (ADR-0006).
5. **Storage default** — user-local, with project-local storage available as an explicit, self-ignoring opt-in (ADR-0004).
6. **Raw-storage handling** — rare, loud, and reversible: per-save confirmation, records flagged in listings, and a `strip-raw` operation to revert to redacted form.

---

## 15. Sources

Public documents grounding §2 (each becomes a dated entry in `core/sources/claims.yaml` at M1):

- Claude Code — Skills: `https://code.claude.com/docs/en/skills`
- Agent Skills — Authoring best practices: `https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices`
- Prompt engineering — Overview: `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview`
- Prompting best practices (living reference): `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices`
- Prompting Claude Fable 5: `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5`
- Refusals and fallback: `https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback`
- API errors reference: `https://platform.claude.com/docs/en/api/errors`
- Agent Skills open standard: `https://agentskills.io`
