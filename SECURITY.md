# Security policy

## Reporting a vulnerability

Please report suspected vulnerabilities privately. Until a dedicated address is published, open a **GitHub security advisory** (Security → Report a vulnerability) on the repository rather than a public issue. Include:

- what you observed and how to reproduce it,
- the affected files or components,
- the impact you believe it has.

You will get an acknowledgement and, where the report is valid, a fix and a credit (if you want one).

## Scope

In scope: the shipped library (`src/prompt_debugger/`), the tooling, the contracts and knowledge that drive behavior, the Claude Code adapter, and the release pipeline.

Particularly relevant classes (see [docs/THREAT-MODEL.md](docs/THREAT-MODEL.md)):

- prompt-injection paths that could cause tool use or persistence the user didn't intend,
- storage integrity issues (path traversal, symlink races, malicious records),
- redaction bypasses that leak secrets into stored/exported data,
- export injection (e.g. CSV formula injection),
- any runtime network I/O in shipped code (there must be none),
- misuse paths that weaken the legitimacy gate.

## Out of scope

- The behavior of the underlying model or provider systems — this project makes no claims about provider internals and cannot change them.
- Social-engineering of a user into pasting their own secrets (mitigated by redaction, but not preventable at the tool layer).

## Our commitments

- Shipped code performs no network I/O; this is enforced by CI (import policy) and tests (socket block).
- Releases carry checksums and provenance attestations (M5+).
- Security-relevant fixes are noted in [CHANGELOG.md](CHANGELOG.md).
