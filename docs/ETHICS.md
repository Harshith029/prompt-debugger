# Ethics and use policy

This project helps people **understand what they can observe** and **communicate legitimate intent more clearly**. It is not a tool for defeating safety systems, and it is designed so it cannot quietly become one.

## What the tool does

- Explains visible safeguard messages, model switches, and errors using only observable information and dated public documentation.
- Analyzes prompt quality and rewrites legitimate prompts for clarity, structure, and explicit intent.
- Keeps a strict separation between **observed facts** and **estimated contributing factors**, and never claims to know a provider's internal moderation or routing logic.

## What the tool will not do

- **It will not rewrite a prompt to bypass, evade, or slip past safety systems.** The legitimacy gate (a specified decision procedure, not a vibe) refuses when the intent is circumvention or when no plausible legitimate reading exists.
- **It will not launder intent.** A rewrite may make your stated intent *more* explicit; it may never make it *less* explicit. Prohibited transformations include fabricating context or authorization you didn't provide, reframing a request as fiction to change how it reads, diluting meaning, fragmenting a request across prompts, or encoding/obfuscating content.
- **It will not guarantee a different outcome.** Every rewrite carries a fixed notice stating that model behavior depends on the provider's systems and policies, and that clarity does not guarantee a changed response. If a rewritten legitimate prompt could still produce the same visible behavior, the tool says so.

## Why these are enforceable, not aspirational

- The legitimacy gate and transformation rules live in the versioned Knowledge Engine and are asserted by adversarial evaluation suites (release gates) that require laundering attempts to be declined.
- Reports record the gate outcome as structured data, so misuse-resistance is testable.
- This policy is public and auditable, and the misuse taxonomy is part of the knowledge corpus.

## The legitimate core

Most people who reach for this tool have a benign prompt that received an unexpected response — a security engineer, a life-sciences researcher, a teacher, a developer — exactly the "benign adjacent work" that documentation acknowledges can trigger safeguards. Helping them state their real intent clearly is the entire point. Doing that honestly requires refusing the small minority of requests whose intent is evasion. Both halves are the same commitment.

## Reporting concerns

If you believe the tool is being used to circumvent safety systems, or that its guidance crosses that line, open an issue or use the process in [SECURITY.md](../SECURITY.md).
