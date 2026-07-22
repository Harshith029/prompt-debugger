# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).
Contract and knowledge-pack versions are tracked independently; bumps are noted here.

## [Unreleased]

## [0.3.0-alpha] — 2026-07-22

Third pre-release: **Milestone M2 — Core Library**, the deterministic runtime layer built on the frozen M0 contracts and M1 knowledge. Adds the schema-subset validator, the invariant verifier, redaction, sanitization, the storage layer, rendering, the read-only knowledge accessors, and the CLI, plus the claim-grounded status-promotion pass, the ADR-0009 re-deferral, and the performance harness with a measured size-warning threshold. Per-FR detail follows.

### Milestone M2 — FR-11 (performance measurement)

Per the approved [specs/M2.md](specs/M2.md) FR-11 and open choice O6.

#### Added
- **`benchmarks/perf/harness.py`** (stdlib-only): the storage performance harness —
  a synthetic-store generator (writes `n` composite-schema-valid, PR-1-valid
  records to a temporary store; supports the spec's 10k / 100k sizes) and a
  timing harness for the read-scan operations (`list`/`get`/`trends`, which
  share the `_read_records` validate-and-parse scan). Subcommands: `validate`
  (a correctness smoke for the CI matrix — no machine-dependent timing bars) and
  `measure` (prints a timings table). Touches no real user store (temp dirs
  only) and does no network I/O.
- **`benchmarks/perf/RESULTS.md`**: recorded measurements and the threshold
  derivation. In the stable small-size region the read scan is linear at
  ≈ 0.63 ms/record (dominated by per-record composite schema validation in the
  frozen FR-1/FR-5 read path); 10k ≈ 6.4 s. At large sizes it degrades
  super-linearly with high run-to-run variance — measured 100k reads take
  minutes (`list`, ≈ 181–188 s across two runs; `get`/`trends` comparable or higher, and noisier), not the seconds a linear
  projection implied. Both large-size runs are recorded as-is (no averaging).
- **`tests/test_perf_harness.py`**: the generator's records are genuinely valid
  (read back and `doctor`-clean), ids unique and ordered, content fully redacted
  (PR-1); `validate` passes; `measure` runs on small sizes; and the runtime
  default agrees with the config-schema default.
- CI runs the perf harness smoke on the matrix (`benchmarks/perf/harness.py
  validate`).

#### Changed
- **Size-warning threshold `size_warn_records` set from measurement (O6),
  replacing the guessed `50000`.** Under the 1-second interactive-responsiveness
  bound and the measured ≈ 0.63 ms/record scan cost, a routine full-history read
  crosses one second at ≈ 1,600 records; the default is set to the largest round
  value at/under that bound, **`1000`** (which coincides with the config
  schema's own `minimum`). Updated in both
  `core/contracts/storage/config.schema.json` (default value + description; the
  field was documented as "provisional until M2 benchmarks set a measured
  value") and the runtime defaults in `src/prompt_debugger/store.py`; the
  vendored plugin copy was re-synced.
- **The threshold is wired into the CLI:** the `list` command (the full-history
  read) suggests running `archive` when the record count is at or above
  `size_warn_records`, emitted once to stderr so the stdout JSON is unchanged and
  passed through the sanitizer (S8). Storage behavior is unchanged (the check is
  CLI-side, reading the loaded config and the record count). Boundary tests cover
  threshold-1 / threshold / threshold+1.

### Milestone M2 — FR-10 (CLI)

Per the approved [specs/M2.md](specs/M2.md) FR-10. No contract, schema, or
policy change.

#### Added
- **`src/prompt_debugger/cli.py`** (stdlib-only): the `argparse` entry point
  that wraps the frozen library and is the dispatch target the M4 `history`
  skill shim will call (ARCHITECTURE §4). It adds no behavior of its own —
  argument parsing, file I/O, and dispatch to `store` (FR-5), `verify` (FR-2),
  `render` (FR-6), `schema` (FR-1), and `knowledge` (FR-7); all validation,
  redaction, sanitization, and fail-closed semantics remain in those modules.
  Subcommands are the **storage-contract operation names** (recorded open
  choice O10): `append`, `list`, `get`, `compare`, `trends`, `export`,
  `delete`, `purge`, `strip-raw`, `doctor`, `migrate`, `archive`, plus `verify`
  and `render` "where user-invocable". Store commands take `--home` (default
  `~/.prompt-debugger`, ADR-0004) and `--project` (default the working
  directory); `append`/`verify` take a Report JSON `--report` and a
  `--prompt-file` (the reference prompt) and load the EV-2 event-taxonomy id
  set from the report's declared provider via the FR-7 accessors. Structured
  results print as `json.dumps` (whose escaping neutralizes control characters,
  so untrusted echoed content cannot inject terminal sequences — S8); the
  text-producing commands (`compare`, `export`, `render`) print the frozen
  modules' already-sanitized output. Fail-closed exit codes: `0` success, `1`
  an operation error (message on stderr) or a `verify` run that found
  violations, `2` argparse usage errors. Runnable as `python -m
  prompt_debugger.cli`; no packaging entry point is added (M5). No skill files
  changed.
- **`tests/test_cli.py`** (19 tests): every storage operation through the CLI
  (append→list→get, compare/trends, delete/purge, strip-raw, doctor/migrate/
  archive); PR-1 redaction and PR-3 fingerprint-exclusion carried through the
  CLI; export in all three formats with provenance; raw gating (rejected
  without `--confirm-raw`, nothing written; accepted with it, visibly flagged);
  `verify` clean/violation/schema-invalid; `render` output and determinism;
  and fail-closed edges (unknown id, non-object report, unknown/no command →
  usage error).

### Milestone M2 — FR-9 (ADR-0009 revisit: truncation kind)

Per the approved [specs/M2.md](specs/M2.md) FR-9. The decision is a **re-defer**;
**no contract, schema, or taxonomy change** — the FR-9 carved-out exception goes
unused.

#### Changed
- **[ADR-0010](docs/adr/0010-truncation-kind-re-deferred.md) added, superseding
  [ADR-0009](docs/adr/0009-truncation-observables-deferred.md).** The M2 contract
  review of ADR-0009 (obligated by FR-9) **re-defers** adding a truncation /
  stop-condition `kind` and taxonomy entry, because the criterion ADR-0009 set —
  "the first milestone where the analyzer needs to *classify* truncation" — is
  unmet: M2 builds the deterministic library, not the analyzer (analyzer/rewrite
  behavior is M3). The member-granularity choice (one `stop_condition` kind vs.
  per-stop-reason kinds over the seven values in `clm-stop-reasons`) remains
  undecidable without real classification needs. ADR-0010 also **corrects**
  ADR-0009's "no migration debt" framing against the frozen Observable Event
  contract's own compatibility rule: adding a `kind` member is a version bump, so
  an M2 addition would spend a rare v1→v2 evolution on a kind no component
  consumes. Truncation reports continue through the contract-mandated `unknown`
  honesty path, with `clm-stop-reasons` citable in explanation prose. ADR-0009's
  status is now "Superseded by ADR-0010"; the ADR index reflects it. The deferral
  is renewed under concrete terms and its revisit obligation is carried forward to
  the milestone that authors the analyzer.
- **`tests/test_contract_invariants.py`:** one regression test making the
  re-deferral non-regressible — the Observable Event `kind` enum is exactly the
  frozen v1 seven-member set and `event_version` is still `1`, so a truncation
  kind cannot be added silently without the superseding-ADR + version-bump path.

### Milestone M2 — FR-8 (status promotion, claim-grounded classes)

Per the approved [specs/M2.md](specs/M2.md) and the promotion path in
[docs/process/policy-review.md](docs/process/policy-review.md). A reviewed
knowledge **content** change — no contract, schema, or policy semantics change.

#### Changed
- **Promotion decision (recorded here per the policy-review process):** with
  FR-7 the library is the first consumer bound to entry statuses; the owner
  commissioned the FR-8 promotion pass. Applying the spec's objective criterion
  mechanically per entry — promote `draft → active` where **every cited claim
  is `verified`** (the KN-2 posture) — promotes **all 10 techniques (T1–T10)**
  and **all 6 event-taxonomy entries (`evt-refusal-visible`,
  `evt-model-switch-visible`, `evt-api-refusal-stop-reason`,
  `evt-api-fallback-block`, `evt-user-visible-error`, `evt-none`)**: every
  claim in the registry has been `verified` since M1. Recorded interpretive
  note: `evt-none` cites zero claims by design (kind `none` asserts no provider
  behavior — the KN-1 carve-out), so it satisfies the criterion vacuously and
  the KN-2 posture trivially; it is promoted with the rest so the analyzer's
  status binding covers the no-event case. O7 granularity decision: mechanical
  per-entry application of the objective criterion, no additional editorial
  judgment (the criterion is objective; with the current corpus the effect is
  bulk promotion).
- **Rubric dimensions and patterns remain `draft` (deferral recorded):** they
  carry `status` fields but no claim-provenance relation, so no repository
  artifact grounds a promotion criterion for them; defining one (e.g. "active
  when all referenced techniques are active") would invent new metadata
  semantics. Their criterion stays **open choice O7** — an explicit governance
  decision, not made here.
- **Knowledge snapshot bumped `2026.07-m1` → `2026.07-m2`** (KN-10, one
  coordinated change): manifest `knowledge_version`, both `pack_version`
  fields, `rubric_version`, `taxonomy_version`, and the three `policy_version`
  fields (misuse-policy, rewrite-policy, notices — **label-only**; their
  content is unchanged, per the policy-review versioning rule that a file's
  label never desyncs from its pack snapshot). All six prose companions'
  headers state the new label; `techniques.md` and the knowledge README no
  longer describe the pre-promotion draft posture. The plugin's vendored
  `core/` was re-synced (`tools/sync_plugin.py`).

#### Added
- **`tests/test_knowledge_integrity.py`:** one test making the FR-8 acceptance
  criterion executable — every technique and event-taxonomy entry whose cited
  claims are all `verified` is `active`, and rubric dimensions and patterns
  remain `draft` (O7 deferral) — so the promoted state cannot silently regress.
  All existing KN-2/KN-7/KN-10 integrity tests pass unmodified on the promoted
  corpus, exactly as the spec's test strategy requires.

### Milestone M2 — FR-7 (knowledge accessors)

Per the approved [specs/M2.md](specs/M2.md). No contract, schema, or policy change.

#### Added
- **`src/prompt_debugger/knowledge.py`** (stdlib-only): the read-only query
  model the knowledge contract fixed at M0 (ADR-0007) — `load_manifest()`,
  `load_pack(provider)`, `technique(id)`, `rubric_dimension(id)`,
  `event_entry(id)`, `claims(status=...)`. Every knowledge file is validated
  against its schema in `core/contracts/knowledge/` via the FR-1 validator
  before any content is returned; missing, unparseable, or schema-invalid files
  are fail-closed errors (`KnowledgeError`/`KnowledgeValidationError`), never
  partial results. Accessors never mutate packs: every call parses fresh and
  returns objects that do not alias the corpus. Cross-file integrity (KN-1..
  KN-10) remains enforced by the contract's integrity tests, not re-implemented.
  Recorded implementation decisions (the contract fixes names and obligations;
  shapes are recorded in the module docstring): `load_pack`'s argument is the
  manifest pack id (equal to the provider identifier for provider packs;
  `"common"` for the provider-neutral pack) and returns `{"pack": ...}` plus
  one key per data file the contract's Structure section assigns to the pack's
  kind; id lookups search packs in manifest order; `claims`' optional status
  filter must name a contract lifecycle state (`recorded`/`verified`/`stale`/
  `retired`) — an unknown status is a fail-closed error, not an empty list.
- **`tests/test_knowledge.py`** (14 tests): validated manifest load; both
  packs' full contract file sets; unknown pack/technique/dimension/event-entry
  refusals; claims unfiltered + `verified` filter + unknown-status fail-closed;
  determinism across repeated calls; the read-only guarantee (caller mutation
  does not affect fresh loads; the corpus digest is byte-identical after every
  accessor runs); fail-closed loading against a temporary corpus
  (schema-invalid file, unparseable manifest, missing pack file).

### Milestone M2 — FR-6 (rendering)

Per the approved [specs/M2.md](specs/M2.md). No contract, schema, or policy change.

#### Added
- **`src/prompt_debugger/render.py`** (stdlib-only): the rendering module.
  `render_report_markdown` is the deterministic Markdown **projection** of a
  Report JSON (ADR-0002: the Markdown a user reads is regenerable from the
  canonical report) covering every content field the Report schema defines —
  knowledge pins, observed event, IR segments, findings with evidence,
  estimates, and the rewrite with its changes and notices. Input is
  composite-schema-validated (CV-1, fail-closed `RenderValidationError`); every
  interpolated value is sanitized (S8); **all fixed notice wording is emitted
  from `notices.json`** — schema-validated on load, `rationale` fields ignored
  (they must not affect runtime behavior), tokens without a text ignored per the
  Rewrite Report contract's additive-notices compatibility rule — never
  re-authored in code (PL-7). `render_export` formats storage-prepared history
  records as `markdown`/`csv`/`json`, each with a **provenance header**:
  generator name and library version, record count, content mode (redacted
  default vs the explicit raw opt-in), and the PRIVACY.md-required note that the
  export may contain prompt text; no generation timestamp (outputs are
  deterministic). Recorded open-choice decisions (O4/O5): CSV uses the `csv`
  module's excel dialect with LF line terminators, `#`-prefixed provenance lines
  above the header row, one row per record (columns: envelope scalars + event
  kind + finding count + prompts; nulls empty, booleans `true`/`false`), cells
  sanitized and formula-escaped (S9); Markdown renders prompt-like text as `>`
  blockquote lines so content cannot masquerade as document structure, and
  exports embed each record's report via the same projection function.
- **`tests/test_render.py`** (15 tests): full-fixture projection field coverage;
  notice wording verbatim-matched against `notices.json`; null sections omitted;
  declined-gate rendering (reason, no text, `gate_declined` notice); determinism
  (projection and every export format); sanitization of content (CSI/BEL
  stripped); fail-closed on invalid reports; markdown export provenance +
  embedded projection; CSV rows/columns/provenance and formula-leader escaping;
  empty-store exports in every format; unknown format refusal in `render`; and
  the real `store.export` path — markdown redacted with provenance, CSV one row
  per record without fingerprints, `include_raw` markdown loud (header states
  the mode, store's warning still printed).

#### Fixed (FR-6 independent review)
- **Free-form report fields can no longer alter rendered Markdown structure:**
  newline-permitting free-form fields (any string the frozen schemas leave
  unconstrained by enum/pattern/const — finding explanation and fix, event
  notes, IR segment notes, estimate hypothesis and reasoning, rewrite
  gate_reason and per-change text and rationale, and the knowledge version
  strings, which carry only `minLength`) were rendered inline, so a schema-valid
  value containing `"...\n## Injected section"` produced a real Markdown
  heading. Every such field now renders through the projection's existing
  structure-preserving representation — the `> ` blockquote already used for
  prompt-like text — with no new escaping mechanism and no Markdown heuristics.
  Schema-constrained values (ids, enums, kinds, severities, patterned versions
  and timestamps, booleans, counts) are unchanged. Two regression tests: the
  injected-heading explanation renders as literal blockquoted text with no real
  heading, and a payload planted in nine free-form fields across every report
  section produces no injected heading, list item, or rule anywhere in the
  document.

#### Changed
- **`store.export` completes the storage contract's format set** via the render
  module: `markdown` and `csv` now render (previously refused with an error
  naming the FR-6 boundary), and all three formats carry provenance headers —
  the `json` export is now a `{"provenance": ..., "records": [...]}` object.
  Storage remains the only preparer (validated reads, redaction defaults,
  fingerprint stripping, raw warning); render only formats. The three FR-5
  export tests were updated for the completed boundary (provenance wrapper;
  the boundary test now asserts an unsupported format such as `html` is
  refused).

### Milestone M2 — FR-5 (storage)

Per the approved [specs/M2.md](specs/M2.md). No contract, schema, or policy change.

#### Added
- **`src/prompt_debugger/store.py`** (stdlib-only): the Storage contract's layout,
  config, and operations, composing the frozen FR-1–FR-4 modules. `append` runs
  verify (against the raw prompt) → redact the whole record unless the raw opt-in
  applies (**PR-1 enforced at the real write path**) → envelope with PR-2 ids and
  PR-3 HMAC-SHA256 fingerprints over the stored text with the per-store salt →
  composite schema validation (CV-2) → one serialized line via a single `os.write`
  on an `O_APPEND` descriptor under the per-store advisory lock (PR-4, documented
  `fcntl`/`msvcrt.locking` shim, platform-guarded imports). Fail-closed refusals:
  schema/invariant failures, `raw=True` without per-save confirmation,
  `allow_raw_saves=false`, and `redaction_enabled=false` with `raw=false` (a
  "redacted" record with unredacted content would violate PR-1). Reads tolerate
  and report a trailing partial line; `get`/`list`/`export` schema-validate and
  sanitize (S10); PR-5 symlink/containment checks at open and read. Operations:
  `list`, `get`, `compare` (**unified diff of redacted prompts only** — the spec's
  scope decision; no score, no substitute aggregate), `trends` (id-ordered
  per-dimension finding counts), `export` (redacted and fingerprint-free by
  default — raw records' content is re-redacted so the PRIVACY.md default holds;
  `include_raw` prints a warning; `json` only, Markdown/CSV raise an error naming
  the FR-6 boundary), `delete`, `purge`, `strip-raw` (reverts a raw record and
  recomputes fingerprints), `doctor` (quarantines invalid/corrupt lines including
  a torn tail to `history.rejects.jsonl` with reasons), `migrate` (timestamped
  backup first; accepts every shipped `record_version` — PR-6 — and refuses
  unknown ones), `archive` (rotation into `archive/`). Config is schema-validated
  with the per-project override; project-local scope requires the acknowledgement
  flag and is created self-ignoring (`.gitignore` `*` + warning README, ADR-0004).
  Recorded open-choice decisions: O2 — project-key HMAC key is a user-level
  `user_salt` file; O3 — bounded lock wait (default 10 s, injectable) then
  `StoreLockedError`; O4 — `compare`/`trends` output shapes as above.
- **`tests/test_store.py`** (39 tests): layout/salt/stable key; project-local
  self-ignoring opt-in and its fail-closed variants; invalid config; symlink
  refusal (skips where unsupported); the PR-1 leak payload through the real
  `append`; schema- and invariant-refusals writing nothing; raw gating (reject
  without confirmation, flag in `list`, `strip-raw` reversion, disabled-raw and
  disabled-redaction configs); id order; lock-contention timeout; partial-tail
  tolerance + doctor reporting; doctor quarantine with reasons; migrate backup +
  unknown-version refusal; archive; delete/purge; sanitize-on-read; compare
  diff-only; trends; export defaults, raw flag + warning, FR-6 boundary error.

#### Fixed (FR-5 independent review, round 3)
- **`doctor` enforces PR-1's pattern clause, not only the substring clause:** the
  shared post-redaction verification covers the substring invariants (IR-1/RPT-1),
  but PR-1 also requires that a `raw: false` record "contains no secret/PII
  pattern in any field, including every content-bearing field of the embedded
  report" — a recognized secret in, e.g., `findings[].explanation` (a field no
  substring invariant governs) previously survived doctor and was rewritten into
  history. `doctor` now additionally verifies that every retained `raw: false`
  record is a **fixed point of the committed FR-3 redactor** (which is
  documented idempotent): `redact_report`/`redact_text` are applied to the
  stored report and `prompt_redacted`, and any difference means a recognized
  pattern survived — the record is quarantined with a PR-1 reason and never
  rewritten back. The check also covers PR-1's opening clause (`prompt_raw`
  must be null in a `raw: false` record), which the schema subset cannot
  express conditionally. No new detector was invented and no detection logic
  duplicated — the committed redaction mechanism is the sole authority on
  recognized patterns; `raw: true` records remain exempt.
- One regression test: a schema-valid `raw: false` record whose substring
  invariants all hold but whose finding explanation carries a recognized secret
  is quarantined by doctor with a PR-1 reason, removed from rewritten history,
  and the properly redacted record is kept.

#### Fixed (FR-5 independent review, round 2)
- **`doctor` enforces PR-1 on retained records:** a schema-valid `raw: false`
  record whose evidence quotes or IR segment text are not substrings of its
  `prompt_redacted` (the post-redaction PR-1 relation) is invalid content per the
  storage contract's integrity rules; `doctor` now runs the same post-redaction
  PR-1 verification used by `append`/`strip-raw` (shared implementation, not
  duplicated) and quarantines such records with a PR-1 reason instead of
  rewriting them back into history. `raw: true` records are untouched — PR-1
  binds `raw: false` records only.
- **Containment/symlink validation precedes directory creation (PR-5/S4):**
  every `mkdir` performed by the storage layer — the store directory in both
  scopes, the salt file's parent, and the archive directory — is now preceded by
  the existing containment/symlink check, so an escaping path (e.g. a
  `stores/` component swapped for a symlink) is refused before any filesystem
  mutation occurs, not after.
- **`migrate` schema-validates every record before backup:** after the strict
  parse and the shipped-`record_version` check, every record must pass the FR-1
  composite history-record validation; any failure aborts the migration — before
  the timestamped backup is written — directing recovery to `doctor`. Version
  handling is otherwise unchanged.
- Three regression tests: doctor quarantines a schema-valid but PR-1-violating
  `raw: false` record (and keeps the raw one); an escaping store path is refused
  with nothing created outside the root; a schema-invalid record aborts
  migration with no backup made, and migration succeeds after doctor.

#### Fixed (FR-5 independent review)
- **PR-1 enforced after redaction on every record-writing path:** pre-redaction
  verification alone could persist a `raw: false` record violating PR-1 — a quote
  that is a bare fragment of a secret (no recognizable prefix) survives redaction
  while the prompt's full secret is replaced, breaking the substring relation and
  leaking the fragment. `append` now re-verifies the redaction-sensitive
  invariants (IR-1 segment text, RPT-1 evidence quotes, against
  `prompt_redacted`) after redacting and refuses the save on any violation;
  `strip_raw` runs the same check after re-redacting and fails closed leaving the
  raw record unchanged.
- **Short writes are detected (PR-4):** the return value of the single `os.write`
  is now checked against the payload length; an incomplete write raises
  `StoreIntegrityError` (directing to `doctor`, which quarantines the torn line)
  instead of reporting success.
- **Symlink/containment checks run immediately before every filesystem write
  (PR-5/S4)**, not only at `open`: history append, atomic rewrites (temp file and
  replace target), doctor's rejects file, migrate's backup, archive rotation, the
  lock file, salt creation, and the project-local `.gitignore`/README. A path
  swapped for a symlink after the store was opened is refused at write time.
- **Every public read path fails closed on invalid records (S10):** `list`,
  `get`, `compare`, `trends`, and `export` now schema-validate every complete
  history line before exposing records; an unparseable or schema-invalid line is
  a `StoreIntegrityError` directing to `doctor` (recovery stays doctor's job — no
  invented tolerant recovery). The trailing partial line remains tolerated and
  reported (PR-4). `purge` deliberately does not require valid content —
  user-owned data must be destroyable even when the history is corrupt.
- **`migrate` fails closed on corrupt history:** torn or unparseable lines abort
  the migration (before any backup is written) with direction to run `doctor`
  first; the unknown-`record_version` refusal (PR-6) is unchanged.
- Seven regression tests: partial-secret quote refused post-redaction and the
  `strip-raw` fail-closed variant; short-write error + doctor recovery;
  write-time symlink race on `history.jsonl`; corrupt-history migration refusal
  and post-doctor success; fail-closed reads across all five read operations; two
  concurrent writers under the lock (per the M2 test strategy) yielding intact,
  unique, schema-valid lines.

### Milestone M2 — FR-4 (sanitization)

Per the approved [specs/M2.md](specs/M2.md). No contract, schema, or policy change.

#### Added
- **`src/prompt_debugger/sanitize.py`** (stdlib-only): the S8/S9 mitigation
  mechanisms. `sanitize_text` removes ANSI CSI sequences wholesale (both the
  `ESC [` and 8-bit `0x9B` introducer forms), then strips C0/C1 control characters
  and DEL. LF and TAB are preserved — the only formatting-bearing C0 characters
  that cannot initiate an escape sequence; stripping them would corrupt every
  multi-line record the storage contract requires to be displayable. CR is
  stripped (a line-overwrite spoofing vector), and stripping ESC neutralizes any
  non-CSI escape sequence by removing its introducer. `escape_csv_cell`
  prefix-escapes any cell leading with `=`, `+`, `-`, `@`, or TAB using the
  conventional `'` guard (threat S9). Both functions are deterministic and
  idempotent; benign content is byte-identical. This is the **mechanism**; records
  are untrusted input (S10), and the read/display/export paths that must apply it
  to every record field are the storage and rendering layers' job (FR-5/FR-6).
  No I/O.
- **`tests/test_sanitize.py`**: CSI removal (both introducer forms, parameter and
  intermediate bytes), non-CSI escape neutralization, C0/C1/DEL stripping with
  LF/TAB preservation and CR removal, printable-Unicode preservation,
  determinism/idempotency, byte-identical clean text; CSV formula-leader escaping
  for all five leaders, benign-cell passthrough, idempotency.

### Milestone M2 — FR-3 (redaction)

Per the approved [specs/M2.md](specs/M2.md). No contract, schema, or policy change.

#### Added
- **`src/prompt_debugger/redact.py`** (stdlib-only): deterministic, pattern-based
  secret/PII scrubbing with typed placeholders, covering exactly the classes
  `docs/PRIVACY.md` commits to — API keys/tokens (vendor-prefixed keys, GitHub/Slack
  tokens, AWS/Google keys, HTTP bearer), PEM private-key blocks, `password=`/`token=`
  style assignments, and emails → `[REDACTED_API_KEY]` / `[REDACTED_TOKEN]` /
  `[REDACTED_PEM_KEY]` / `[REDACTED_SECRET]` / `[REDACTED_EMAIL]`. Redaction is
  per-class stable (same secret ⇒ same placeholder everywhere, so the storage layer
  can satisfy PR-1's redacted-substring consistency) and idempotent (placeholders
  match no pattern). `redact_text` is the atom; `redact_report` redacts every
  content-bearing field of a Report JSON (IR segment text/notes, finding
  explanation/fix and evidence quotes, event verbatim/notes, estimate
  hypothesis/reasoning, rewrite text/gate_reason and change descriptions) without
  mutating its input. Assignment values are fully redacted whether unquoted or
  quoted (single/double quotes, embedded whitespace included), so a multi-word
  quoted secret leaves no fragment behind. The module's honest-limits docstring
  matches PRIVACY.md's "Honest limits". This is the redaction **mechanism**; PR-1
  enforcement on the whole record at write time is the storage layer's job (FR-5).
  No I/O, no fingerprints, no record envelope — those belong to FR-5.
- **`tests/test_redact.py`**: true-positive corpus (each secret class scrubbed),
  false-positive corpus (benign text untouched), determinism/idempotency, the PR-1
  substring property, and whole-report field coverage (every content field redacted;
  structural/enum/version fields and the input object preserved).

### Milestone M2 — FR-2 (runtime invariant verifier)

Per the approved [specs/M2.md](specs/M2.md). Enforces the catalogued relationships the
schema subset cannot express; no contract, schema, or policy change.

#### Added
- **`src/prompt_debugger/verify.py`** (stdlib-only): runtime enforcement of IR-1/IR-2,
  RPT-1–RPT-4, RW-1–RW-3, EV-1/EV-2, and PT-1–PT-3, returning structured
  `Violation(invariant, path, message)` records (empty list = upholds every in-scope
  invariant). Shape validation stays `schema.py`'s job (FR-1); this module checks only
  the cross-field, cross-document, and content relationships and assumes schema-valid
  input, coded defensively so malformed structure never raises. Two relationships take
  inputs that live outside the documents and are therefore parameters, not fetched
  here: the **reference prompt** (IR-1/RPT-1 — the source prompt is in neither schema)
  and the **event-taxonomy id set** (EV-2, the "loaded taxonomy version"). EV-2 is
  fail-closed — an empty taxonomy id set rejects any non-null `documented_match`.
  PL-6 is out of scope (M2 builds no policy decision engine).
- **`tests/test_verify.py`**: positive, negative, and edge cases for every in-scope
  invariant, plus the spec-required agreement check — the verifier produces the same
  verdicts as the existing reference checkers in `tests/test_contract_invariants.py`
  on the shared rewrite and event fixtures.

#### Changed
- `docs/CONTRACT-INVARIANTS.md`: the enforcement and test columns for IR-1/2,
  RPT-1–4, RW-1–3, EV-1/2, and PT-1–3 now name the runtime verifier (`verify.py`)
  and `tests/test_verify.py`. Invariant definitions are unchanged.

### Milestone M2 — FR-1 (runtime schema-subset validator)

First M2 runtime code, per the approved [specs/M2.md](specs/M2.md).

#### Added
- **`src/prompt_debugger/schema.py`** (stdlib-only): `find_subset_violations` treats
  the approved keyword subset as **exhaustive** — every keyword not explicitly allowed
  is rejected, including unknown `$`-prefixed keywords; boolean subschemas are rejected
  (the restricted subset has no boolean-schema semantics); and the closed-object rule
  applies to every object schema: with `properties`, `additionalProperties: false` is
  required; without `properties`, the object must be a composite placeholder carrying
  `$comment` (the documented form for fields governed by another contract); no value
  of `additionalProperties` other than `false` is accepted. `validate` implements
  draft 2020-12 semantics for exactly the subset keywords — including the subtle
  cases: booleans are never integers/numbers, integral floats are integers, `pattern`
  is an unanchored regex search, and enum/const/uniqueItems use JSON equality with
  bool distinction — and raises `SubsetViolationError` before validating any instance
  against a schema that fails the conformance rules above.
  `validate_report`/`validate_history_record` implement composite validation
  CV-1/CV-2 (envelope + every composed sub-document, record → embedded report
  recursively), resolving contracts through the existing `paths` module.
- **Differential validation in CI** (`tests/test_differential_validation.py`), the
  M1-inherited obligation: the runtime validator and the dev-only `jsonschema`
  package must return identical accept/reject verdicts for every repository schema
  and for an accept/reject corpus — every seed instance the repository already
  validates plus deterministic mutants of each (unknown root key, dropped first
  required key, retyped first required key). Subset-conformance verdicts are also
  held in parity with `tools/_subset.py`, so the library and the CI meta-check
  cannot drift. Any disagreement fails the build via pytest.
- Unit tests for the validator's semantics (`tests/test_schema_validator.py`), each
  subtle case cross-checked against `jsonschema`; composite and fail-closed paths
  covered against the real contract schemas and fixtures.

#### Changed
- Invariants CV-1/CV-2 in `docs/CONTRACT-INVARIANTS.md` now name the runtime
  enforcement point (`schema.py`) alongside the existing reference tests.

#### Fixed (FR-1 independent review)
- **Unknown `$` keywords no longer bypass subset validation:** both the runtime
  validator and the CI meta-check (`tools/_subset.py`) previously exempted any
  `$`-prefixed keyword; the subset's three approved `$` keywords (`$schema`, `$id`,
  `$comment`) are now the only ones accepted, and `$dynamicRef`-style keywords are
  rejected. The two implementations are held to exact violation-list parity by test.
- **Boolean subschemas are rejected** during subset conformance (they were accepted
  by the checker but silently unvalidated at runtime — an inconsistent hybrid); the
  restricted subset takes no boolean-schema semantics, so `validate` now fails closed
  on them.
- **Closed-object rule applied to every object schema**, not only those with
  `properties`: a bare `{"type": "object"}` (open object) is rejected unless it is a
  documented composite placeholder carrying `$comment`, and `additionalProperties`
  may never hold a value other than `false`. The subset-scan also no longer descends
  into annotation values (`default`/`examples`/`const`/`enum` hold data, not schemas).
- **Malformed values of supported keywords are rejected fail-closed:** the subset
  restricts *which* keywords are supported, and retained keywords keep their full
  draft 2020-12 definitions — so every supported keyword's value must have the
  shape the meta-schema gives it (`properties` an object, `enum` a list, `required`
  a list of **unique** property names, `type` a JSON type name or non-empty list of
  **unique** type names, length/count bounds non-negative integers, numeric bounds
  numbers, `pattern` a string that compiles as a regular expression, `uniqueItems`
  a boolean, annotations strings/lists; `const`/`default` any value). Previously,
  schemas like `{"properties": []}` or `{"enum": 1}` passed subset scanning and
  surfaced as Python `AttributeError`/`TypeError` during runtime validation, and
  duplicate members in `type`/`required` arrays were accepted; all now raise the
  normal `SubsetViolationError` before any instance is examined. Applied
  identically to `tools/_subset.py` (exact parity, test-held).

## [0.2.0-alpha] — 2026-07-14

Second pre-release: **Milestone M1 — Knowledge Verification & Policy Authoring**, complete
and independently approved. Knowledge content and its executable integrity floor only — no
analyzer, rewrite, or storage behavior is implemented (those arrive in M2–M4). Every claim
verified against live sources; the declarative policy layer authored and frozen; taxonomy
prose completed; pattern library completed; corpus versioned as `2026.07-m1`. Milestone
record: [docs/releases/M1.md](docs/releases/M1.md).

### Close-out
- Project versions bumped `0.1.0-alpha` → `0.2.0-alpha` (`0.1.0a0` → `0.2.0a0`) across
  pyproject, the library, and the plugin/marketplace/adapter manifests.
- Milestone record `docs/releases/M1.md` created; all status pages report M0 complete,
  M1 complete, M2 not started.
- Post-FR-6 verification fixes: the composite report fixture's rewrite made
  rewrite-policy-compliant using the slot convention (it pinned the current policy snapshot
  while violating RG-7); `specs/M1.md` status metadata corrected; M1 progress statements
  made consistent across every status page; a stale architecture document-version reference
  removed from the docs index.
- Status promotion (spec FR-2) applied as its constraint (KN-2, executable); bulk promotion
  deliberately deferred to M2 — all entries remain `draft` (see the milestone record §10).

### Milestone M1 — FR-6 (version bookkeeping)

#### Changed
- **Knowledge snapshot label bumped: `2026.07-draft` → `2026.07-m1`**, reflecting the
  M1 content change from the M0 seed: the claim registry fully verified and extended
  (FR-1, FR-4, FR-4.1: 12 claims, all `verified`), the authored policy layer
  (FR-3/3.1/3.2: misuse policy, rewrite policy, notices), the completed taxonomy
  prose (FR-4/4.1), and the completed pattern library (FR-5/5.1). Bumped coordinately
  in every authoritative field — `manifest.json` `knowledge_version`, both packs'
  `pack_version`, `rubric_version`, `taxonomy_version`, and the three
  `policy_version` fields — plus the six prose-companion headers, per the
  label-alignment rule (never desync a file's label from its pack snapshot). Test
  fixtures and the architecture example were aligned to the same label. The `-m1`
  tag is kept (rather than a bare `2026.07`) because per-entry `status` promotion is
  a separate, not-yet-performed pass; the label names the milestone content
  snapshot, not entry maturity.

#### Added
- **Invariant KN-10 with an executable test:** all knowledge snapshot labels —
  manifest, both packs, rubric, taxonomy, and the three policy files — must name one
  corpus snapshot, and the prose companions must state the same label in their
  headers. Label desynchronization now fails CI instead of relying on discipline.

### Milestone M1 — FR-5.1 (rewrite correctness in pattern examples)

Content correction only: the pattern library's own examples now satisfy the rewrite
guarantees they demonstrate. No contract, schema, policy, or architecture change.

#### Fixed
- **Fabricated content removed from every After example (RG-7/RG-8).** The After
  examples invented information absent from their Before — dates, metrics, thresholds,
  audiences, priorities, technologies, API details, domain facts (e.g. an invented
  "p95 / 2026-07-10 / June baseline / 10%" resolution; an invented audience "a new
  backend engineer joining next week"; an invented tech stack "Python 3.10, stdlib
  only, dedupe by email"; an invented example table row "Pagination offset/cursor").
  Information the user holds but the prompt lacks is now expressed as explicit
  angle-bracket slots (`<what the user would supply>`) or an explicit question —
  the convention is documented in `patterns/README.md`.
- **Intent preserved exactly (RG-1/RG-2).** "every function" → "every public
  function" (narrowing) corrected; tentative asides ("should probably", "might as
  well") are no longer silently promoted to firm requirements — they become explicit
  scope questions; an added "quote the log lines" instruction absent from the Before
  was removed; conflicting requirements are surfaced for the user's priority rather
  than resolved by invented context; "Prompt 1/2" labels replaced with "First/Second
  prompt" (no literals absent from the Before).
- Documentation kept strong, examples corrected to match it (not vice versa):
  `patterns/README.md` now states the After-content rule and the slot convention;
  KN-9 extended accordingly.

#### Added
- **Executable enforcement of the objective RG-7/RG-8 slice:** a new integrity test
  extracts each Before/After pair and rejects any After whose numeric literals or
  dotted (file-like) tokens do not appear in its Before, after excluding
  angle-bracket slots/tags and numbered-list markers. No heuristic quality judgment
  — only objectively checkable fabrication.

### Milestone M1 — FR-5 (pattern completion)

Knowledge content and its executable integrity floor; no runtime code, no contract changes.

#### Added
- **Seven new patterns**, completing the library to one per rubric dimension R1–R10
  (the analyzer's finding surface — the documented completeness definition in
  `patterns/README.md`): `pat-resolve-ambiguity` (R1/T1),
  `pat-reconcile-contradictions` (R3/T1), `pat-surface-real-scope` (R4/T8+T9),
  `pat-separate-instructions-from-data` (R6/T4+T6), `pat-state-goals-not-steps`
  (R7/T10), `pat-state-definition-of-done` (R8/T9), `pat-state-constraints` (R9/T9+T7).
  Every body is a complete before/after example whose After makes existing intent
  explicit — never fabricated context — per the rewrite policy. All `draft` pending
  the status-promotion pass.
- **Invariant KN-9 with four executable tests:** rubric-dimension coverage is total;
  index and on-disk bodies are bijective (no orphaned bodies); pattern ids and files
  are unique; every body carries the full authored structure and agrees with its
  index entry (id, title, dimensions, techniques) — so a stub or drifted body cannot
  pass CI.

#### Fixed
- The three original pattern bodies said "rewrite-contract compliant"; the artifact
  has been named the **rewrite policy** since FR-3 — wording corrected. The library
  README now documents the completeness definition, the authoring rules against the
  real policy file, and why T5 has no dedicated pattern (no rubric dimension maps
  to it).

### Milestone M1 — FR-4.2 (formatter determinism and claim-graph closure)

Resolves the verified findings of the second independent FR-4 review.

#### Fixed
- **Formatter gate non-determinism (P0), root cause found and reproduced:**
  `requirements-dev.txt` pinned `ruff>=0.5` — a floating lower bound. Ruff's formatter
  style evolves between versions (the assert-message wrapping style changed: older ruff
  parenthesizes the asserted condition, newer ruff parenthesizes the message), so two
  environments that both satisfy the declared range disagree on the same tree. Reproduced
  concretely: ruff 0.15.20 and 0.15.21 pass on this tree with exit 0 and an empty `--diff`;
  ruff 0.5.0 — fully conforming to the old bound — fails it (`tests/test_frontmatter.py`,
  `tests/test_knowledge_integrity.py` would be reformatted). Line endings were ruled out
  (`git ls-files --eol`: uniformly LF). The discrepancy between the FR-4.1 report and the
  independent verification was therefore **repository-caused**: both environments were
  self-consistent; the repo failed to make the gate reproducible. Fix: ruff is pinned
  exactly (`ruff==0.15.21`), the tree verifies clean under the pin, and version bumps are
  documented as deliberate pin-update-plus-reformat changes. The FR-4.1 "does not
  reproduce" record is superseded accordingly.
- **Orphaned cookbook claim (P1):** `clm-cookbook-fallback-billing` was verified but cited
  by no structured artifact. Integrated with real provenance: `evt-api-refusal-stop-reason`
  now documents the `fallback_credit_token` that `stop_details` may carry on a blocked
  request with a billable cached prefix (a user-visible response field), citing the claim.

#### Added
- **Executable orphan detection (P1), invariant KN-8:** the suite fails if any `verified`
  claim is cited by no technique or event-taxonomy entry, so the claim graph cannot
  silently accumulate dead verified claims that quarterly re-verification would maintain
  for nothing.

### Milestone M1 — FR-4.1 (taxonomy accuracy stabilization)

Resolves the verified findings of the independent FR-4 review. Knowledge content, tests,
and documentation truthfulness only; the frozen policy layer is untouched.

#### Fixed
- **Consumer-surface fallback overstatement (P0):** the taxonomy generalized a page-scoped
  verified negative into "consumer-surface fallback is not publicly documented" — falsified
  by the FR-4.1 survey of official sources. Product-specific documentation does cover it:
  the Claude Code docs document automatic model fallback with a visible transcript notice
  (new claim `clm-claude-code-fallback`), and the Claude Help Center documents the consumer
  apps' automatic switching, notice, and model label (new claim `clm-webapp-switch-notice`);
  the official Cookbook fallback/billing guide is captured as `clm-cookbook-fallback-billing`
  (developer-surface scope, per-platform availability). `clm-consumer-surface-fallback` is
  revised to exactly its evidence — the platform page's coverage — with explicit pointers to
  where product behavior IS documented. The model-switch taxonomy entry and the events
  companion now distinguish scopes per surface and never borrow one surface's documentation
  for another. Re-verification against the updated platform page (2026-07-14) also extended
  `clm-fallback-block` (usage.iterations; sticky routing serves fallback turns with no block)
  and `clm-refusal-stop-reason` (explanation not stable; batch results may carry null
  stop_details on a refusal).
- **Claim lifecycle drift (P1):** the KN-2 test compared entries against a nonexistent
  `active` claim status (the lifecycle is `recorded`/`verified`/`stale`/`retired`) and could
  never enforce the invariant. The test now treats `verified` as the citable state; KN-2's
  wording is corrected in the invariants catalogue, the knowledge contract, the contracts
  README, the policy-architecture design, and the policy-review process doc.
- **Event boundary ambiguity (P1):** `evt-refusal-visible` (surfaces included `api`) and
  `evt-api-refusal-stop-reason` could both match one observation. Resolved with the
  documented **observation-channel rule** (events companion): raw API response fields →
  `api_*` entries (surfaces exactly `["api"]`); rendered product-surface messages →
  `refusal_message`/`model_switch` (never `api`). Surface sets of paired entries are now
  disjoint; recorded as invariant EV-4 and enforced by tests.
- **Repository truthfulness (P1):** README (status banner, project status, roadmap table,
  ADR count now nine), docs/ROADMAP.md, docs/ARCHITECTURE.md (§2 facts updated to verified
  status with the corrected error-code list and the truncation/stop-reason distinction;
  §15 source list extended), and core/knowledge/README.md (status section reflects M1
  progress) now describe the repository as it exists today.

#### Added
- **Verified-claim integrity (P1), invariant KN-7 with executable tests:** every taxonomy
  entry cites only `verified` claims regardless of its own status; claim statuses stay
  within the schema lifecycle; every claim has an https source, ISO dates, and
  `last_verified >= retrieved`. Plus EV-4 tests: unique kinds and disjoint
  observation-channel surfaces.

#### Verified
- **`ruff format --check` (P0):** did not reproduce under ruff 0.15.20 (exit 0, zero-diff,
  all 23 tracked Python files in scope). **Superseded by FR-4.2**, which found the real root
  cause: the formatter version was unpinned, so the verdict was version-dependent — this
  check was correct for one environment, not for the gate.

### Milestone M1 — FR-4 (taxonomy prose)

Knowledge content only (per the M1 spec: no runtime code, no contract changes).

#### Added
- **`clm-stop-reasons`** (verified 2026-07-14 against the live handling-stop-reasons page):
  all seven documented `stop_reason` values with their meanings and follow-ups. Resolves the
  FR-1 deferral recorded in `clm-api-errors` (2026-07-12 fetch limit).
- **ADR-0009:** truncation observables (`max_tokens`, `model_context_window_exceeded`) are
  claim-backed but get no taxonomy kind while the v1 event contract is frozen; they flow
  through the `unknown`-kind honesty path until M2's contract review revisits the enum.
- Events prose companion: a "two families of *something stopped*" section separating HTTP
  errors from stop conditions, so analysis-layer adapters cannot conflate them.
- Three taxonomy integrity tests: prose completeness (`api_correlate` null only for
  `evt-none`), KN-1 made executable for events (non-`none` entries cite ≥1 claim), and
  inline `clm-*` mentions in prose must resolve to the registry *and* be cited in that
  entry's `source_claims`.

#### Changed
- **Taxonomy prose completed for all six entries** (`core/knowledge/packs/anthropic/events.json`),
  reflecting FR-1 verification outcomes: refusal entries state the HTTP-200 (not error)
  framing, documented `stop_details` categories, and the no-rephrasing-guarantee boundary;
  the model-switch entry replaces its stale "until clm-consumer-surface-fallback is
  verified" wording with the verified-negative outcome (consumer-surface mechanism is
  undocumented — user observation, never asserted mechanism); the error entry's boundary
  now cites `clm-stop-reasons` to separate truncation from HTTP errors; `evt-none` states
  that no estimates layer may attach. Statuses remain `draft` (promotion is FR-2).
- `clm-api-errors` notes updated: the stop-reasons deferral is resolved.

### Milestone M1 — FR-3.2 (policy consistency polish)

Resolves the minor consistency findings of the FR-3.1 review. No schema, semantic, or
functional change.

#### Fixed
- **Decline-template source of truth (Issue 1):** aligned with the notices philosophy —
  `misuse-policy.json` is canonical for decline wording; `misuse-policy.md` now declares
  itself derived and quotes both templates verbatim (it previously said the wording was
  "fixed here"), with a drift test. Invariant PL-7 generalized to cover all fixed
  user-facing wording (notice texts + decline templates).
- **Documentation consistency (Issue 2):** the artifact table in
  `docs/design/policy-architecture.md` no longer links `.json` labels to `.md` files —
  every label now links to the file it names, schemas link to their actual schema files,
  data and companions are separate rows, and the invariants row reads PL-1..PL-8.

#### Added
- **Companion parity tests (Issue 3):** decline-template quotes in `misuse-policy.md`
  must match `misuse-policy.json` byte-for-byte, and each companion's header must state
  the same `policy_version` as its JSON (both relationships were already documented).

### Milestone M1 — FR-3.1 (policy layer stabilization)

Resolves the verified findings of the independent FR-3 review. No redesign, no new features.

#### Fixed
- **Report version pinning (Issue 1):** the Report JSON contract can now represent the
  documented `policy_version` pinning — `report.knowledge.policy_version` added as an
  optional, nullable field (additive within Report v1 per its compatibility rule). Contract
  prose, the knowledge contract, and `docs/COMPATIBILITY.md` now agree; the composite
  fixture exercises the populated field, the history-record fixtures the absent one.
- **Single source of truth for notices (Issue 2):** `notices.json` is authoritative for
  notice wording; `notices.md` is explicitly derived, quotes each text verbatim, and an
  integrity test fails on any drift. The Rewrite Report contract's pointer corrected from
  `notices.md` to `notices.json`.
- **Architecture documentation drift (Issue 3):** `docs/design/policy-architecture.md`
  updated to the implemented state — status header, §4.2 note that the procedure is data
  as an ordered prose checklist (dispatch lives in analyzer code), §6 rewritten to defer to
  `policy-schemas.md` and the real artifacts (the superseded `on_yes`/`on_no` field sketch
  and the resolved Option-A/B decision box removed), closing section reflects FR-3 completion.
- **Provider-name leak:** `rewrite-policy.md` referred to "the Anthropic techniques file";
  now provider-neutral ("the active provider pack's techniques file"), per KN-5 and the
  governance neutrality rule — enforced by a new test.

#### Added
- **Integrity coverage (Issue 4):** seven new tests — RG binding equals the documented
  RG-1..RG-8 set; the notices file covers the complete Rewrite Report enum exactly once;
  `policy_version` aligns across the three files and their pack snapshot; every registry id
  appears in its `.md` companion; `notices.md` quotes match `notices.json` byte-for-byte;
  no provider names in policy files; the `policy_version` pattern is shared and
  calendar-valid. Recorded as invariants PL-7/PL-8.
- **Version validation (Issue 5):** the `policy_version` pattern in all three policy schemas
  now rejects calendar-impossible months (`00`, `13`–`99`). Formally a pattern-tightening,
  taken in-version under the alpha pre-release rule because no valid instance existed in the
  rejected space; the exception is recorded in `docs/design/policy-schemas.md`.

### Milestone M1 — FR-3 (policy authoring)

Adds the provider-neutral policy layer as declarative data, per
[docs/design/policy-schemas.md](docs/design/policy-schemas.md). No analyzer, rewrite, or
storage behavior is implemented (that remains M2–M4); the policy files are inert data the
future engine will interpret.

#### Added
- Three additive knowledge schemas under `core/contracts/knowledge/`: `misuse-policy.schema.json`,
  `rewrite-policy.schema.json`, `notices.schema.json`. Recursion-free subset, `additionalProperties:
  false` on every object; purely declarative (closed enums and prose only — no branching fields,
  expressions, or embedded logic).
- Three `common`-pack policy files plus Markdown companions: `misuse-policy.json`/`.md`
  (legitimacy classification: three classes, the neutral ordered procedure, the ask-don't-guess
  elicitation rule, fixed decline templates), `rewrite-policy.json`/`.md` (allowed and prohibited
  transformations, the RG-1..RG-8 guarantees with hard/judged mode, notice-attachment rules), and
  `notices.json`/`.md` (fixed notice texts keyed to the Rewrite Report `notices` enum).
- Every policy entry carries a **stable, permanent registry id** (`MISUSE-###` / `RW-###` /
  `NOTICE-###`), never reused, distinct from any closed semantic role (`class`, `notice`,
  `guarantee_ref`).
- Every policy entry carries a maintainer-facing `rationale`, documented and schema-annotated as
  **documentation only — not read at runtime**.
- Policy invariants PL-1..PL-6 in `docs/CONTRACT-INVARIANTS.md`, and integrity tests in
  `tests/test_knowledge_integrity.py` (id uniqueness/form; three complete classes; `notice`
  values ⊆ Rewrite Report enum; notice rules resolve to notice texts; technique references and
  `guarantee_ref`s well-formed; provider-neutrality of the new files).
- [docs/process/policy-review.md](docs/process/policy-review.md) — maintainer governance for
  policy evolution: contribution workflow, review and evidence expectations, compatibility and
  versioning rules, schema evolution discipline, rationale standards, regression requirements,
  and the approval process. Documentation only; no runtime effect.

#### Changed
- Policy files use **`schema_version`** (format axis) alongside **`policy_version`** (content
  axis) to keep schema evolution and policy evolution independent; the knowledge contract records
  the divergence from the older `file_version` spelling.
- `core/knowledge/packs/common/pack.json` description updated to present-tense (the policy files
  now exist); the pack stays on the `2026.07-draft` snapshot.
- `tools/validate_schemas.py` validates the three new policy files against their schemas;
  `core/contracts/knowledge/CONTRACT.md` lists them in the structure tree.

## [0.1.0-alpha] — 2026-07-12

First public pre-release: the **engineering foundation**. No analyzer, rewrite, or storage
behavior is implemented yet (those arrive in Milestones M2–M4). This tag bundles the M0
foundation with the M0.1 and M0.1.1 stabilization passes so the architecture, contracts, and
knowledge engine can be reviewed in the open. Milestone record: [docs/releases/M0.md](docs/releases/M0.md).

### Stabilization — M0.1.1 (release polish)
Resolves the verified findings from independent review. No functional/analyzer work; no scope change.

#### Fixed
- **Architecture accuracy:** the architecture document no longer describes M2 library modules
  (`store`/`schema`/`verify`/`redact`/`sanitize`/`render`/`cli`) in the present tense, and no
  longer references files that do not exist (`core/sources/claims.yaml`, a flat `core/schemas/`,
  `core/guides/`, `INSTALL.md`/`SECURITY-REVIEW.md`). §5 now shows the actual current tree with
  a separate "planned additions" list; the claim registry is correctly located at
  `core/knowledge/packs/anthropic/claims.json`; M2/M5 components are labelled as future work.
- **Pattern library integrity:** the three patterns named in the Anthropic pattern index now
  have authored markdown bodies (Option A); a new integrity test asserts every indexed pattern
  file exists, so there can be no dangling reference.
- **Release gate parity:** the release workflow now runs `check_versions.py` (version
  consistency) as part of a gate identical to PR CI, then additionally verifies the plugin,
  marketplace, and adapter-manifest versions against the git tag. The release gate is no longer
  weaker than the PR gate. `check_release_version.py`'s docstring corrected to reflect that it
  already validates the adapter manifest.

#### Added
- Concrete composite-validation fixtures and `tests/test_composite_validation.py`: a Report JSON
  with populated `event` and `rewrite` sub-documents, validated through the full composite chain
  (report → ir → event → rewrite, and embedded in a history record), plus a case proving a
  schema-valid-but-invariant-violating rewrite is caught by the reference checker.
- Invariants KN-6 (pattern files exist) and refreshed CV-1/CV-2 test references in
  `docs/CONTRACT-INVARIANTS.md`.

### Stabilization — M0.1
Correctness, consistency, and privacy-safety of the M0 foundation. No functional/analyzer
work; no scope change.

#### Fixed
- **Privacy (PR-1):** persisted history records embedded the full Report JSON, whose IR
  segment text and evidence quotes carry verbatim prompt substrings — so a secret scrubbed
  from `prompt_redacted` could survive in the embedded report. The storage contract now
  requires redaction of the **entire record** for a `raw: false` save, the `raw` flag's
  semantics were clarified to govern the whole record, and the invariant is guarded by an
  executable test (`tests/test_privacy_invariants.py`) with compliant and leak fixtures.

#### Changed
- **Host-neutral core:** the Observable Event contract's `surface` enum no longer encodes
  provider product names (`claude_ai`, `claude_code`). It now uses host-neutral categories
  (`web`, `cli`, `desktop`, `api`, `other`, `unspecified`); the Anthropic pack maps its
  product surfaces onto them. (Pre-release interface change, permitted under alpha.)
- Documentation synchronized with implementation: the architecture repository tree is
  labelled as the target layout, and the performance section marks the benchmark store
  generators as M2 work rather than present.
- Report and Prompt IR contracts clarify that the verbatim-substring rule references the
  redacted prompt inside a persisted `raw: false` record.

#### Added
- `docs/CONTRACT-INVARIANTS.md` — the catalogue of invariants the schema subset cannot
  express, each with its enforcement point and test.
- `tests/test_contract_invariants.py` and `tests/test_privacy_invariants.py` — executable
  enforcement of the rewrite-report, observable-event, and persisted-redaction invariants.
- `tools/check_versions.py` — verifies all version-bearing files agree; wired into CI and
  the local gate. `tools/check_release_version.py` now also checks the adapter manifest.
- Strengthened knowledge-integrity tests: provider-neutral surface enum, taxonomy surface
  categories, and the active-cites-active claim-provenance rule.

### Foundation — M0

- **Repository foundation** separating host-neutral core, adapters, contracts, knowledge,
  benchmarks, evals, tests, tooling, docs, and CI.
- **Versioned contracts (v1):** Prompt IR, Report JSON, Rewrite Report, Observable Event,
  Storage (history record + config), Knowledge Engine file formats, Plugin/Adapter API,
  Prompt Tree — each a JSON schema (restricted, recursion-free subset) plus a prose contract.
- **Knowledge Engine:** versioned data packs — a provider-neutral `common` rubric pack
  (R1–R10) and an `anthropic` provider pack (dated claim registry, techniques T1–T10,
  observable-event taxonomy, pattern-library index). Seed content is `draft`/`recorded`,
  pending the M1 verification pass.
- **Claude Code adapter** scaffold: plugin and marketplace manifests, adapter manifest,
  four skill skeletons (`analyze`, `rewrite`, `history`, `pd`) with a corrected
  tool-permission model, and a CI-verified vendored copy of `core/`.
- **Benchmark corpus** across nine categories with a schema-validated runner, wired into CI.
- **Semantic-evaluation protocols** (meaning preservation, red-team rewrite, rubric
  calibration) as documented stubs for the release gate.
- **Tooling:** schema/subset validation, AST import-policy check, relative-link check,
  plugin vendor sync, and release-version verification.
- **Documentation:** architecture, eight ADRs, data flow, glossary, threat model, privacy
  model, roadmap, compatibility policy, ethics/use policy, and the Prompt Tree design.
- **CI/CD:** three-OS × two-Python matrix gate; release workflow skeleton with checksums
  and build-provenance attestations.

### Security & privacy
- Shipped code performs no runtime network I/O — enforced by an AST import allowlist and a
  socket-blocking test harness, not by convention.
- Storage defaults to user-local; project-local storage is explicit opt-in and self-ignoring.

### Notes
- This is `alpha`: interfaces may still change before `v1.0.0`. Every such change will be
  recorded here.

[Unreleased]: https://github.com/Harshith029/prompt-debugger/compare/v0.2.0-alpha...HEAD
[0.2.0-alpha]: https://github.com/Harshith029/prompt-debugger/releases/tag/v0.2.0-alpha
[0.1.0-alpha]: https://github.com/Harshith029/prompt-debugger/releases/tag/v0.1.0-alpha
