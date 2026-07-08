# Prompt Debugger for Claude — Architecture Proposal

| | |
|---|---|
| **Status** | Proposal — awaiting maintainer approval and independent (Codex) review before implementation |
| **Version** | 0.1.0-draft |
| **Date** | 2026-07-07 |
| **Authors** | Claude Code (lead engineer/architect) |

---

## 1. Mission and scope

**Prompt Debugger for Claude** is an open-source Claude Code skill (distributed as a plugin) that helps users:

1. **Understand observable model behavior** — visible safeguard messages, visible model switches, user-visible errors — using only information the user can actually see, grounded in Anthropic's public documentation.
2. **Analyze prompt quality** — detect ambiguity, missing context, contradictory instructions, scope creep, unrelated task bundling, poor formatting, excessive complexity, weak objectives, missing constraints, and missing output specifications.
3. **Rewrite legitimate prompts** — improve clarity, structure, explicit intent, and output specification while preserving meaning, applying Anthropic's published prompt-engineering techniques.
4. **Track prompt quality locally** — save history, compare revisions, analyze trends, and export reports. Local-first, zero telemetry.

### 1.1 Non-goals (explicit)

- **Never** claim knowledge of Anthropic's internal moderation logic, classifier thresholds, or routing rules. Every explanation is either an *observable fact* (quoted verbatim, tied to documented API surface) or an *estimate* (labeled with confidence and reasoning).
- **Never** rewrite a prompt for the purpose of bypassing or evading safety systems. If the user's underlying intent appears to be circumvention, the skill declines the rewrite and says why.
- **Never** guarantee that a rewrite changes model behavior. Every rewrite carries a standard non-guarantee notice.
- **No cloud services, no telemetry, no network calls** in v1. All data stays on the user's machine.

---

## 2. What the official documentation establishes (grounding)

Every design decision below is grounded in Anthropic's public documentation, reviewed on 2026-07-07. This section records the facts the product depends on, so reviewers can verify claims and so the skill's bundled reference files have a single provenance trail.

### 2.1 Observable safeguard and routing events are documented API surface

From the Claude API documentation and model release notes:

- A safeguard decline returns **HTTP 200 with `stop_reason: "refusal"`**, optionally accompanied by a `stop_details` object with a `category` field (documented values include `"cyber"`, `"bio"`, `"reasoning_extraction"`, `"frontier_llm"`, or `null`) and an `explanation`. Both classifier declines and ordinary model refusals surface through the same `stop_reason`.
- When fallbacks are configured (or built into a consumer surface), a **`fallback` content block** (`{type: "fallback", from: {model}, to: {model}}`) marks each visible model switch, and the response's `model` field names the model that actually served the reply. Anthropic documents that most Claude consumer surfaces ship with built-in fallbacks to Claude Opus 4.8 — which is why users of claude.ai and Claude Code sometimes see a *visible* model-switch notice after a safeguard event.
- **User-visible errors** are enumerated in the errors reference: 400 `invalid_request_error`, 401, 403, 404, 413, 429 `rate_limit_error`, 500, 529 `overloaded_error`, plus stop reasons `max_tokens` and `model_context_window_exceeded`.
- The Fable 5 prompting guide states that safety classifiers target offensive cybersecurity, biology/life-sciences content, and reasoning extraction, and explicitly notes that **benign adjacent work can trigger false positives**. This is the documented, citable basis for the product's core use case: legitimate prompts sometimes receive safeguard responses, and clearer prompts communicate legitimate intent better.

**Consequence:** the skill can build a complete, honest taxonomy of observable events from public sources alone. Nothing needs to be inferred about hidden systems.

### 2.2 The prompt-engineering technique inventory

From the prompt-engineering overview, the prompting best-practices reference, and the Fable 5 prompting guide, the techniques the rewriter must encode are:

| # | Technique | Source guidance |
|---|-----------|-----------------|
| T1 | Be clear and direct | "Golden rule": if a colleague with minimal context would be confused, Claude will be too. Be specific about desired output. |
| T2 | Add context and motivation | Explain *why* an instruction matters; "give the reason, not only the request." |
| T3 | Use examples (multishot) | 3–5 relevant, diverse examples wrapped in `<example>` tags. |
| T4 | Structure with XML tags | Separate instructions, context, input, and examples with consistent, descriptive tags. |
| T5 | Give Claude a role | A one-sentence system-prompt role focuses behavior and tone. |
| T6 | Long-context ordering | Longform data at the top, query/instructions at the end (up to ~30% quality improvement); ground responses in quotes. |
| T7 | Control output format positively | Say what to do, not what to avoid; use format indicators; match prompt style to desired output. |
| T8 | Decompose or chain complex tasks | Break multi-goal requests into steps or separate prompts; chaining for inspectable pipelines. |
| T9 | Define success criteria and constraints | The overview's precondition: measurable success criteria before tuning. |
| T10 | Avoid over-prescription on current models | Fable 5 guidance: state goals and constraints rather than enumerating steps; aggressive "CRITICAL/MUST" language overtriggers; instructions are followed literally. |

### 2.3 Skill authoring constraints (Claude Code + Agent Skills standard)

- A skill is a directory with `SKILL.md` (YAML frontmatter + markdown body). Frontmatter `name`: ≤64 chars, lowercase/numbers/hyphens, **must not contain the reserved words "anthropic" or "claude"**. `description`: ≤1024 chars, third person, states *what* and *when*.
- Keep `SKILL.md` **under 500 lines**; move detail into reference files linked **one level deep**; bundle scripts that are *executed, not loaded* (only their output costs tokens).
- Relevant frontmatter: `description`, `when_to_use`, `argument-hint`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `context: fork` + `agent`, `paths`. Dynamic context injection (`` !`cmd` ``) runs shell commands at invocation time — a security-relevant feature we deliberately minimize (§8).
- Skill locations: personal (`~/.claude/skills/`), project (`.claude/skills/`), plugin (`<plugin>/skills/`, namespaced `plugin:skill`). Plugins are the distribution vehicle for a community project.
- Evaluation: `evals/evals.json` per skill (prompts + expected behaviors), baseline comparisons with the skill disabled, and the `skill-creator` plugin automates trigger-rate and A/B measurement. Skills follow the Agent Skills open standard (agentskills.io), so the core skill is portable beyond Claude Code.

---

## 3. Key product decisions

### D1 — Skill-first, packaged as a plugin

The deliverable is a **plugin** named `prompt-debugger` containing a small set of skills. A plugin (vs. loose project skills) gives us: namespacing (`prompt-debugger:analyze`), marketplace distribution (`/plugin install`), versioning, and room to bundle future agents/hooks without breaking users. The repository doubles as the plugin: users can also copy `skills/` into `.claude/skills/` directly.

### D2 — No browser extension in v1

The mission says "browser extension (if appropriate)." It is **not appropriate**, for three reasons:

1. **No honest data source.** An extension would have to scrape claude.ai's DOM — an undocumented, unstable, unofficial surface. The project's core value is *grounding in observable, documented facts*; a scraper is the opposite.
2. **Privacy and trust.** An extension with read access to conversations is the largest possible privacy surface for the smallest gain. This contradicts the local-first, minimal-data principle.
3. **The paste protocol is strictly better.** The user already *has* the observable evidence (the visible message, the error text, the model indicator). A structured "observable event report" the user pastes or describes (§7.4) captures the same information with zero risk. Consent is inherent in the act of pasting.

A browser extension remains on the roadmap (§14) only if an official, documented client surface ever exposes these events programmatically.

### D3 — Judgment in markdown, determinism in scripts

Per the skill best-practices "degrees of freedom" model:

- **Prompt analysis, event explanation, and rewriting are judgment tasks** → high-freedom markdown instructions with a strict *output contract* (templates in §7). The model is the analysis engine; the skill is the methodology.
- **Storage, diffing, redaction, schema validation, and report export are fragile/deterministic** → low-freedom bundled Python scripts with exact invocation commands. Scripts are executed, not loaded, keeping token cost near zero.

### D4 — Local-first analytics, opt-in persistence, zero telemetry

History lives in `.prompt-debugger/history.jsonl` (project-scoped) or `~/.prompt-debugger/history.jsonl` (user-scoped, configurable). Nothing is written unless the user asks to save. Raw prompt text is stored only with explicit opt-in; the default record stores a redacted prompt plus a content hash for revision matching. No network I/O exists anywhere in the codebase — enforced by code review and a CI grep gate.

### D5 — Python 3.10+, standard library only, for all scripts

Skills run wherever Claude Code runs; the best-practices doc warns against assuming installed packages. Stdlib-only scripts (json, hashlib, difflib, argparse, re, datetime, pathlib) remove the entire dependency-supply-chain and install-failure surface. Dev-time tooling (pytest, ruff, mypy) is confined to `requirements-dev.txt` and CI.

### D6 — The honesty architecture (core differentiator)

Every explanation output is structurally split into:

1. **Observed** — verbatim quotes of what the user saw, classified against the documented event taxonomy (§7.4). Facts only.
2. **Estimated** — hypotheses about contributing factors *in the prompt* (ambiguous phrasing that could read as a prohibited request, missing context that obscures legitimate intent), each labeled **High / Medium / Low confidence** with one sentence of reasoning.
3. **Epistemic notice** — a fixed template stating that moderation and routing internals are not public, that estimates are educated guesses, and that the analysis is based only on visible information.

Rewrites additionally carry the fixed non-guarantee notice (verbatim, required by template):

> *"This rewrite is intended to improve clarity and communicate your legitimate intent more effectively. It does not guarantee a different response, as model behavior depends on the provider's systems and policies."*

**Legitimacy gate:** before rewriting, the skill assesses whether the request appears legitimate (education, software development, debugging, documentation, research, writing, analysis, and similar). If the stated goal is to get prohibited content past safeguards, or the prompt has no plausible legitimate reading, the skill explains the observable event but **declines the rewrite** and says so plainly. If a rewritten legitimate prompt could still trigger the same visible behavior under Anthropic's policies, the skill states that explicitly.

### D7 — License: MIT

MIT for the whole repository. Rationale: the project is predominantly prose + small scripts; MIT maximizes adoption and contribution for a community-standard candidate. Apache-2.0 is the alternative if the maintainer wants an explicit patent grant; the choice is isolated to `LICENSE` and can be made at M0 without affecting anything else.

---

## 4. System architecture

```
┌────────────────────────────────────────────────────────────────────┐
│ User input                                                         │
│  • pasted prompt  • pasted safeguard/error message                 │
│  • description of a visible model switch  • "/pd:*" invocation     │
└──────────────┬─────────────────────────────────────────────────────┘
               ▼
┌────────────────────────────────────────────────────────────────────┐
│ SKILLS (plugin: prompt-debugger)          judgment layer           │
│                                                                    │
│  analyze ──── full workflow: intake → event ID → quality           │
│               analysis → estimate → rewrite → offer save           │
│  rewrite ──── rewrite-only fast path (same guards + notice)        │
│  history ──── save / list / compare / trends / export             │
│                                                                    │
│  Progressive-disclosure references (loaded on demand):             │
│   references/observable-events.md   (documented event taxonomy)    │
│   references/quality-rubric.md      (10-dimension rubric, R1–R10)  │
│   references/rewrite-guide.md       (techniques T1–T10 + templates)│
│   references/output-templates.md    (report/rewrite/event formats) │
│   references/honesty-policy.md      (observed-vs-estimated rules,  │
│                                      legitimacy gate, notices)     │
└──────────────┬─────────────────────────────────────────────────────┘
               ▼ Bash (scoped, explicit commands only)
┌────────────────────────────────────────────────────────────────────┐
│ SCRIPTS (Python 3.10+, stdlib only)       deterministic layer      │
│  history.py   append/list/get/compare/trends on history.jsonl      │
│  redact.py    secret+PII pattern scrub before persistence          │
│  export.py    render saved records → Markdown / JSON / CSV         │
│  validate.py  JSON-schema check for records & frontmatter (CI too) │
└──────────────┬─────────────────────────────────────────────────────┘
               ▼
┌────────────────────────────────────────────────────────────────────┐
│ LOCAL STORAGE (no network, user-owned)                             │
│  .prompt-debugger/history.jsonl   (append-only records)            │
│  .prompt-debugger/config.json     (scope, redaction, raw opt-in)   │
└────────────────────────────────────────────────────────────────────┘
```

### 4.1 Skill decomposition

| Skill | Command | Invocation | Purpose |
|---|---|---|---|
| `analyze` | `/prompt-debugger:analyze [prompt or event]` | user **and** model (description triggers on "my prompt was refused", "why did the model switch", "review my prompt") | The main workflow. Routes on input type: event + prompt → full debug; prompt only → quality report. |
| `rewrite` | `/prompt-debugger:rewrite [prompt]` | user and model | Fast path: rewrite with change-log, legitimacy gate, and notice. Shares the rubric/guide references. |
| `history` | `/prompt-debugger:history [save\|list\|compare\|trends\|export]` | user only (`disable-model-invocation: true` — persistence is a side effect the user controls) | Wraps the deterministic scripts. |

Three skills rather than one keeps each `SKILL.md` small, gives each a precise trigger description (critical for correct auto-invocation), and lets `history` be safely excluded from model-initiated invocation. Shared methodology lives once, in `references/`, linked one level deep from each `SKILL.md`.

### 4.2 Main workflow (`analyze`)

```
Step 0  INTAKE      Identify what the user provided. If a safeguard event is
                    referenced but not quoted, ask for the visible text
                    verbatim (or accept "not available").
Step 1  OBSERVE     Classify the event against references/observable-events.md.
                    Output the "Observed" block: quotes + documented meaning.
                    Never go beyond what the taxonomy documents.
Step 2  LEGITIMACY  Assess apparent intent. Legitimate → continue.
        GATE        Circumvention intent → explain event, decline rewrite, stop.
Step 3  ANALYZE     Score the prompt against quality-rubric.md (R1–R10).
                    Each finding: dimension, severity, evidence quote, fix.
Step 4  ESTIMATE    If an event occurred: list estimated contributing factors
                    with High/Medium/Low confidence + reasoning. Emit the
                    epistemic notice. Skip entirely if no event was reported.
Step 5  REWRITE     Apply T1–T10. Preserve meaning. Emit rewrite + per-change
                    explanation (what changed → which technique → why it
                    helps communication) + the non-guarantee notice.
Step 6  OFFER SAVE  Offer /prompt-debugger:history save. Never persist
                    without an explicit yes.
```

---

## 5. Repository structure

```
prompt-debugger/
├── README.md                      # value prop, quickstart, honest-scope statement
├── LICENSE                        # MIT
├── CONTRIBUTING.md                # dev setup, eval workflow, review gates
├── CODE_OF_CONDUCT.md
├── SECURITY.md                    # reporting, threat model summary
├── CHANGELOG.md                   # Keep a Changelog + SemVer
├── .claude-plugin/
│   ├── plugin.json                # plugin manifest
│   └── marketplace.json           # self-hosted marketplace entry
├── skills/
│   ├── analyze/
│   │   ├── SKILL.md               # < 500 lines, workflow of §4.2
│   │   ├── references/
│   │   │   ├── observable-events.md
│   │   │   ├── quality-rubric.md
│   │   │   ├── rewrite-guide.md
│   │   │   ├── output-templates.md
│   │   │   └── honesty-policy.md
│   │   └── evals/evals.json
│   ├── rewrite/
│   │   ├── SKILL.md               # links to ../analyze/references/ content
│   │   └── evals/evals.json       # (copies synced by CI if cross-skill links
│   │                              #  prove unreliable — verified in M1)
│   └── history/
│       ├── SKILL.md
│       ├── scripts/
│       │   ├── history.py
│       │   ├── redact.py
│       │   ├── export.py
│       │   └── validate.py
│       └── evals/evals.json
├── schemas/
│   ├── history-record.schema.json
│   └── config.schema.json
├── docs/
│   ├── ARCHITECTURE.md            # this document
│   ├── INSTALL.md                 # plugin, project-skill, and personal installs
│   ├── USAGE.md                   # walkthroughs per feature
│   ├── PRIVACY.md                 # data inventory, defaults, deletion
│   ├── SECURITY-REVIEW.md
│   ├── ETHICS.md                  # honesty policy, no-bypass policy (public)
│   └── SOURCES.md                 # every doc claim → public URL
├── examples/
│   ├── 01-ambiguous-prompt/       # before.md, session-transcript.md, after.md
│   ├── 02-safeguard-event/
│   ├── 03-multi-task-prompt/
│   └── 04-history-workflow/
├── tests/
│   ├── test_history.py
│   ├── test_redact.py
│   ├── test_export.py
│   ├── test_validate.py
│   └── test_frontmatter.py        # name/description constraint enforcement
├── .github/
│   ├── workflows/ci.yml
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── requirements-dev.txt           # pytest, ruff, mypy (dev only)
└── pyproject.toml                 # tool config; no runtime deps
```

Note on naming: skill `name` fields cannot contain the reserved words "claude" or "anthropic", so skills are `analyze` / `rewrite` / `history` under the `prompt-debugger` plugin namespace. The *repository* and README may freely say "for Claude".

---

## 6. Technical specification — skills

### 6.1 `analyze/SKILL.md` frontmatter

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
---
```

- No `context: fork`: the workflow needs conversation context (the prompt or event is often already in the transcript).
- `allowed-tools: Read` only; the analyze skill needs no shell access. All tools remain *available* under normal permission prompts — this field only pre-approves.

### 6.2 `history/SKILL.md` frontmatter

```yaml
---
name: history
description: Saves prompt analyses locally, compares revisions, shows trends,
  and exports reports. Local-first; writes only when explicitly asked.
argument-hint: "[save | list | compare <id> <id> | trends | export <format>]"
disable-model-invocation: true
allowed-tools: >
  Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/history.py *)
  Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/redact.py *)
  Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/export.py *)
---
```

- `disable-model-invocation: true`: persistence is user-controlled; Claude never decides on its own to write history.
- `allowed-tools` pre-approves only the bundled scripts by absolute skill path.

### 6.3 Quality rubric (R1–R10), encoded in `references/quality-rubric.md`

| ID | Dimension | Detects | Maps to fix |
|----|-----------|---------|-------------|
| R1 | Ambiguity | vague referents, undefined terms, multiple readings; fails the "colleague test" | T1 |
| R2 | Missing context | unstated audience/purpose/domain; intent the reader must guess | T2 |
| R3 | Contradictory instructions | mutually exclusive requirements; inconsistent terminology | T1, consistency pass |
| R4 | Scope creep | requirements smuggled into asides; "also/while you're at it" chains | T8, T9 |
| R5 | Multiple unrelated tasks | independent goals in one prompt | T8 (split or chain) |
| R6 | Poor formatting | wall-of-text; data/instructions interleaved; long context ordered badly | T4, T6 |
| R7 | Excessive complexity / over-prescription | micromanaged steps, redundant emphasis (ALL CAPS, "CRITICAL"), nested conditionals | T10 |
| R8 | Weak objective | no definition of done; no success criteria | T9 |
| R9 | Missing constraints | unstated length/tone/tech/format boundaries the user actually has | T9, T7 |
| R10 | Missing output specification | no format, structure, or example of the expected answer | T7, T3 |

Each finding is reported as: **dimension · severity (High/Medium/Low) · evidence (verbatim quote) · why it impedes communication · concrete fix**. Severity reflects impact on a model's ability to understand intent — the rubric never claims a finding "caused" a safeguard event (that belongs to the Estimated layer, with confidence labels).

### 6.4 Output contract (excerpt of `output-templates.md`)

```markdown
## Prompt Debug Report

### 1. Observed
> [verbatim quote of visible message / event]
[Documented classification: e.g., "a visible refusal message; on the API this
surfaces as stop_reason: refusal" — with reference to SOURCES.md entry]

### 2. Prompt quality findings
| # | Dimension | Severity | Evidence | Suggested fix |
...

### 3. Estimated contributing factors  ⚠ estimates, not facts
- [factor] — Confidence: Medium — [one-sentence reasoning]
[Epistemic notice — fixed text]

### 4. Rewritten prompt
[rewrite]

### 5. What changed and why
- [change] → applies [T#] → [communication benefit]

[Non-guarantee notice — fixed text]
```

### 6.5 History record schema (`schemas/history-record.schema.json`)

```jsonc
{
  "id": "pd-20260707-a1b2c3",        // date + short hash
  "created_at": "2026-07-07T12:00:00Z",
  "schema_version": 1,
  "prompt_hash": "sha256:…",          // always stored (revision matching)
  "prompt_redacted": "…",             // default persistence form
  "prompt_raw": null,                 // only with per-save explicit opt-in
  "event": {                          // nullable
    "kind": "refusal_message | model_switch | error | none",
    "verbatim": "…",                  // redacted like prompts
    "category_documented": "…"        // only if user pasted one (e.g. API field)
  },
  "findings": [ { "dimension": "R1", "severity": "high", "note": "…" } ],
  "scores": { "R1": 2, "...": 0 },    // 0 none / 1 minor / 2 major
  "rewrite_hash": "sha256:…",
  "parent_id": null                   // links revisions for compare/trends
}
```

`history.py` subcommands: `append` (stdin JSON, validated against schema), `list`, `get <id>`, `compare <id> <id>` (rubric-score delta + unified diff of redacted prompts), `trends` (per-dimension counts over time), all with `--json` and human output. `export.py` renders Markdown/CSV/JSON. Append-only with `delete <id>` and `purge` provided for data-ownership reasons (§9).

### 6.6 Redaction (`redact.py`)

Pattern-based scrub applied before any persistence: common credential shapes (`sk-…`, `ghp_…`, `AKIA…`, `xox…`, JWTs, PEM blocks, `password=`/`token=` assignments), emails, and long high-entropy strings → replaced with typed placeholders (`[REDACTED:api-key]`). Documented as best-effort, not a guarantee — PRIVACY.md tells users the truth about its limits. Unit-tested against a fixture corpus of true/false positives.

---

## 7. Security review (threat model)

| # | Threat | Mitigation |
|---|--------|------------|
| S1 | **Prompt injection via analyzed content.** A pasted prompt may contain instructions ("ignore previous instructions and…"). | The skill's workflow wraps user-supplied prompt/event text in explicit data tags and instructs Claude to treat it strictly as an artifact under analysis, never as instructions. Eval cases in `evals.json` test injection payloads. This is best-effort mitigation (injection is not fully solvable at the prompt layer) and is documented as such. |
| S2 | **Skill grants itself excessive tool access.** | `analyze`/`rewrite`: `Read` only. `history`: only the three bundled scripts by `${CLAUDE_SKILL_DIR}` path. No `Write`, no broad `Bash`. Reviewed at every release gate. |
| S3 | **Dynamic context injection abuse** (`` !`cmd` `` runs at render time). | The skills use **no** dynamic context injection in v1. CI greps skill bodies for the `` !` `` pattern and fails on it. Compatible with orgs that set `disableSkillShellExecution`. |
| S4 | **Path traversal / unsafe file handling in scripts.** | Scripts resolve paths with `pathlib`, confine writes to the configured `.prompt-debugger/` directory, reject paths that escape it, and never execute or eval stored content. |
| S5 | **Secrets persisted into history.** | Redaction-by-default (§6.6); raw storage requires per-save opt-in; PRIVACY.md documents limits; `.gitignore` guidance for `.prompt-debugger/`. |
| S6 | **Supply chain.** | Zero runtime dependencies (D5). Dev deps pinned. No install scripts. |
| S7 | **Misuse: the tool as a bypass assistant.** | Legitimacy gate (D6) in the workflow + fixed policy text in `honesty-policy.md` + adversarial eval cases (requests to "rephrase so the filter doesn't catch it" must be declined). ETHICS.md makes the policy public and auditable. |

---

## 8. Privacy review

**Data inventory:** the only data the system can touch is (a) text the user pastes into their own Claude Code session and (b) records the user explicitly saves to their own disk. There are no accounts, no identifiers, no network calls, no telemetry, and no analytics beacons.

- **Default:** nothing persisted. Analysis is ephemeral conversation.
- **On save:** redacted prompt + hash. Raw text only with explicit per-save consent (`--raw` acknowledged interactively).
- **Deletion:** `history.py delete <id>` / `purge`; PRIVACY.md documents the exact file locations so users can audit or remove them by hand.
- **Sharing surface:** exports are files the user creates deliberately; the export header notes that the content may contain their prompt text.
- **CI enforcement:** a test asserts no `http`, `socket`, `urllib`, or `requests` usage in `skills/**/scripts/`.

Note: content the user pastes into a Claude Code session is processed by Anthropic per the user's existing Claude agreement — the skill adds no *additional* data flow, and PRIVACY.md says exactly that rather than implying the skill makes the conversation itself more private.

---

## 9. Performance review

- **Token budget:** each `SKILL.md` ≤ 300 lines (hard cap 500 per docs); descriptions front-load trigger keywords within the 1,536-char listing cap; methodology detail sits in reference files loaded only when the workflow reaches the relevant step; scripts are executed, never loaded. Idle cost of the installed plugin ≈ three descriptions (~150 tokens).
- **Runtime:** scripts are O(history size) JSONL scans — negligible for realistic volumes (thousands of records); no indexing needed in v1 (revisit if `trends` exceeds ~50k records).
- **Latency:** the dominant cost is model reasoning, which is the product. No retries, no network waits.

---

## 10. Testing strategy

| Layer | What | How | CI |
|---|---|---|---|
| Unit | `history.py`, `redact.py`, `export.py`, `validate.py` | pytest, fixture corpus (incl. redaction true/false positives, malformed JSONL, schema violations) | ✅ every PR |
| Contract | frontmatter rules (name charset/length/reserved words, description length), SKILL.md line caps, one-level-deep reference links, no `` !` `` injection, no network imports | `test_frontmatter.py` + lint script | ✅ every PR |
| Schema | history records validate against `schemas/*.json` | pytest + `validate.py` self-test | ✅ every PR |
| Skill evals | per-skill `evals/evals.json`: should-trigger prompts, should-NOT-trigger prompts (description tuning), golden scenarios (ambiguous prompt → R1 finding; safeguard event → Observed/Estimated separation present; bypass request → declined; injection payload → treated as data) | skill-creator plugin loop + documented manual protocol (fresh session, with/without skill baseline) | ◻ release gate (model-in-the-loop; run pre-release + on skill changes, results committed) |
| Examples-as-tests | `examples/**` transcripts regenerated at each release; drift reviewed | manual, checklist in CONTRIBUTING | ◻ release gate |

Eval-driven development order (per best-practices doc): write `evals.json` for a feature **before** writing the skill content, baseline without the skill, then write the minimum instructions that pass.

---

## 11. CI/CD

**CI (GitHub Actions, on every PR + main):**
1. `ruff check` + `ruff format --check` (scripts, tests)
2. `mypy --strict` on `skills/**/scripts/`
3. `pytest` (unit + contract + schema)
4. Markdown link check (docs + skill references)
5. Policy gates: no network imports, no dynamic-context injection, frontmatter contract, SKILL.md size caps

**Release:**
1. SemVer tag → GitHub Release with CHANGELOG excerpt
2. `plugin.json` version bump verified against tag
3. Skill evals executed and results attached to the release PR
4. Marketplace manifest (`marketplace.json`) points at the tagged ref, so `/plugin install prompt-debugger@<marketplace>` gets pinned, reviewed versions

---

## 12. Milestones and independent-review workflow

Every milestone ends with a Codex red-team review against a fixed checklist (correctness, architecture, security, privacy, edge cases, maintainability, docs, test coverage). **No milestone is complete until every verified finding is addressed.** Review requests and dispositions are recorded in `docs/reviews/M<N>-review.md`.

| M | Deliverable | Exit criteria |
|---|-------------|---------------|
| M0 | Repo scaffold: structure, LICENSE, README, CONTRIBUTING, CI skeleton, this document merged | CI green on empty scaffold; license decision recorded |
| M1 | Reference corpus: `observable-events.md`, `quality-rubric.md`, `rewrite-guide.md`, `honesty-policy.md`, `output-templates.md`, `SOURCES.md` | Every factual claim has a public-doc source; Codex verifies citations; cross-skill reference linking verified to work from a plugin install |
| M2 | `analyze` skill + evals | Golden scenarios pass; should-not-trigger rate acceptable; injection + bypass evals pass |
| M3 | `rewrite` skill + evals | Meaning-preservation spot checks; notice always present; gate holds under adversarial evals |
| M4 | `history` skill + scripts + schemas + unit tests | Full unit/contract coverage; redaction corpus passes; privacy defaults verified |
| M5 | Docs + examples + plugin packaging + marketplace | Fresh-machine install test (Windows + macOS/Linux paths); examples reproduce |
| M6 | Security & privacy review docs finalized; v1.0.0 release | Codex full-repo review; all findings closed |

---

## 13. Roadmap (post-v1)

- **v1.1** — Config polish (user- vs project-scope switching UX), `trends` visual HTML report (bundled script, local file output).
- **v1.2** — Prompt-template library: reusable rewrite scaffolds per task family (coding, research, writing) as additional reference files.
- **v1.3** — Optional MCP server exposing analyze/rewrite/history as tools for non-Claude-Code hosts that support MCP but not Agent Skills. Same local-first constraints.
- **Deferred indefinitely** — Browser extension: reconsider only if an official client API exposes observable events; would require its own security/privacy review cycle.
- **Continuous** — Doc-sync process: a quarterly checklist item (and issue template) to re-verify `SOURCES.md` claims against current Anthropic docs, since observable-event surfaces evolve with model releases.

---

## 14. Open questions for the maintainer

1. **License:** MIT (recommended) or Apache-2.0? (§3 D7 — needed at M0.)
2. **Plugin namespace UX:** `/prompt-debugger:analyze` is explicit but long. Acceptable, or should the plugin also ship a short alias skill (e.g. `pd`) that routes?
3. **History default scope:** project-local `.prompt-debugger/` (recommended: keeps data next to the work, easy to gitignore) vs. user-global `~/.prompt-debugger/`?
4. **Repository name:** `prompt-debugger` vs `prompt-debugger-for-claude` (README can clarify either way).

---

## 15. Sources

All facts in §2 and the skill reference corpus derive from these public documents (retrieved 2026-07-07):

- Claude Code — Skills: `https://code.claude.com/docs/en/skills`
- Agent Skills — Authoring best practices: `https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices`
- Prompt engineering — Overview: `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview`
- Prompting best practices (living reference): `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices`
- Prompting Claude Fable 5: `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5`
- Refusals and fallback (stop_reason/stop_details/fallback blocks): `https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback`
- API errors reference: `https://platform.claude.com/docs/en/api/errors`
- Agent Skills open standard: `https://agentskills.io`

The full claim→URL map ships as `docs/SOURCES.md` in M1.
