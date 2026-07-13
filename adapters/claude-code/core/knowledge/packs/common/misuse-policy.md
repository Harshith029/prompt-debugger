# Misuse Policy — prose companion (policy_version 2026.07-draft)

Human/model-readable exposition of the misuse classification defined in [`misuse-policy.json`](misuse-policy.json). Ids match one-to-one. The JSON is what machines validate; this file is what analysis-layer adapters read. Design basis: [policy architecture §4](../../../../docs/design/policy-architecture.md).

**Scope.** The misuse model decides one thing: **whether rewriting is legitimate.** It never adjudicates whether content is permitted by any provider, and it never makes a request more permissible. It is provider-neutral and topic-agnostic — it classifies by *intent relative to safeguards*, not by subject matter. This policy contains no executable logic: the analyzer interprets these classes, steps, and templates; the data never dispatches.

## Classes

- **MISUSE-001 legitimate** → `passed_or_conditional`. A plausible benign reading exists and fits the user's stated purpose and context, and the request is not primarily aimed at defeating a safety system. The analyzer produces a rewrite that makes intent more explicit — `conditional` when the report also says the same visible behavior may still occur under provider policy.
- **MISUSE-002 ambiguous** → `elicit`. Purpose is unstated or under-stated and a harmful reading is plausible alongside a benign one. **Do not guess.** Elicit purpose, treat the answer as stated context, and re-classify. Absent clarification, fail closed.
- **MISUSE-003 prohibited** → `declined`. The evident purpose is to bypass, evade, or defeat a safety system, or there is no plausible legitimate reading. Decline the rewrite; still explain the observable event honestly.

## Procedure (applied in order — a checklist, not a flowchart)

1. **MISUSE-010 Dual-reading.** Construct the most plausible legitimate reading and the most plausible harmful reading, with any stated purpose and context.
2. **MISUSE-011 Safeguard-targeting test.** Is the evident aim to defeat, evade, or get content past a safety system, rather than to accomplish a benign task?
3. **MISUSE-012 Legitimate-reading test.** Is there a plausible benign reading consistent with stated purpose and context?
4. **MISUSE-013 Sufficiency test.** Is stated (or clearly implied) purpose enough to select the legitimate reading over the harmful one?
5. **MISUSE-014 Record.** Record the class and the deciding step in the Rewrite Report `gate_reason`: prohibited when safeguard-targeting is evident or no legitimate reading exists; ambiguous when a harmful reading remains plausible and purpose is insufficient; legitimate otherwise.

The step order is data the analyzer follows; there are no `on_yes`/`on_no` directives. The conditional language in MISUSE-014 is prose the analyzer applies, not a branching field.

## Elicitation (the ask-don't-guess rule)

When a request is ambiguous, ask what the user is trying to accomplish and why, in specific terms; treat the answer as newly stated context and re-run the procedure from the first step. Never resolve ambiguity in the permissive direction on the user's behalf.

## Decline templates

- **MISUSE-020** — used when the request appears aimed at getting around a safety system. Invites a legitimate user to restate intent; the observable event is still explained.
- **MISUSE-021** — used when no legitimate reading could be found that a rewrite would clarify.

Decline wording is fixed here (not model-authored) so refusals are stable and testable. A declined gate produces no rewritten text but still yields an honest event explanation.
