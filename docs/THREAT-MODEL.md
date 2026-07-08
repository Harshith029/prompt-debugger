# Threat model

The system is local-first with no network I/O, so classic remote-attack surface is minimal. The real risks are content-driven (analyzed text is untrusted), storage integrity, misuse, and supply chain. This model is the M0 baseline; M6 finalizes it after implementation.

## Assets

- The user's prompts and pasted evidence (may contain sensitive text or secrets).
- Locally stored history.
- The integrity of the tool's claims (its trustworthiness depends on never over-claiming).

## Trust boundaries

See [DATAFLOW.md](DATAFLOW.md) for the diagram. In short: pasted content is untrusted; model output is untrusted until validated; stored records are untrusted on read; exports cross into other applications.

## Threats and mitigations

| # | Threat | Mitigation | Status at M0 |
|---|---|---|---|
| S1 | Prompt injection via analyzed content (incl. "invoke a tool" instructions) | Content wrapped as data; `analyze`/`rewrite`/`pd` set `disallowed-tools: Write Edit NotebookEdit Bash`; injection eval cases (M3) | permission model in place + contract-tested; evals pending |
| S2 | Excessive tool grants | Minimal `allowed-tools` (pre-approval only); scripts pre-approved by `${CLAUDE_SKILL_DIR}` path | in place |
| S3 | Dynamic context injection abuse (`` !`cmd` ``) | Zero use in v1; frontmatter test forbids the pattern | test in place |
| S4 | Path traversal / symlink races in storage | `pathlib` resolution + containment; symlink refusal; no eval/exec of content | spec'd (contract); enforced in M2 |
| S5 | Secrets persisted to history | Redaction by default; raw saves rare/loud/reversible; self-ignoring project stores | spec'd; enforced in M2/M4 |
| S6 | Hidden network I/O / supply chain | Zero runtime deps; AST import allowlist; socket-block test harness | enforced now |
| S7 | Misuse as a bypass assistant | Specified legitimacy gate + transformation rules; adversarial evals; public ETHICS.md | policy at M1, evals at M3 |
| S8 | Terminal escape / control-char injection via stored/echoed content | `sanitize.py` strips C0/C1 + ANSI on any echoed content | spec'd; enforced in M2 |
| S9 | Export injection (CSV formulas, markup) | CSV cells with `= + - @`/tab prefix-escaped; plain formats only | spec'd; enforced in M2 |
| S10 | Malicious hand-crafted history records | Schema-validate + sanitize on read; `doctor` quarantine | spec'd; enforced in M2 |
| S11 | Plugin update compromise | Marketplace pinned to tags; checksums + provenance attestations | release pipeline at M5 |
| S12 | Permission-profile drift | CI contract test: frontmatter must equal the documented profile | enforced now |
| S13 | Injection-steered persistence | `history` is `disable-model-invocation: true`; only the user can save | enforced now (frontmatter test) |

## Residual risk

Prompt injection is not fully solvable at the prompt layer. The mitigations reduce blast radius — no write/execute tools active during analysis, no autonomous persistence, content treated as data — rather than claiming prevention. This is stated plainly to users; the tool never promises what it cannot enforce.
