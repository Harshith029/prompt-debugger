# Quality Rubric — prose companion (rubric_version 2026.07-m1)

Extended detection guidance for the dimensions defined in [`rubric.json`](rubric.json). Ids match one-to-one. This file is what analysis-layer adapters read; the JSON is what machines validate.

**Global rule:** severity always measures *impact on a model's ability to understand intent*. The rubric never claims a finding "caused" a safeguard event — causal hypotheses belong in the report's Estimated layer, with confidence labels.

**Finding format:** every finding cites verbatim evidence from the prompt (machine-verified), names the dimension, grades severity per the dimension's guidance, explains why it impedes communication, and proposes a concrete fix mapped to technique ids.

## R1 Ambiguity
Apply the colleague test: would a competent colleague with no extra context know what to do? Look for pronouns without referents ("fix it", "make this better"), undefined jargon, quantifiers without measures ("fast", "short", "professional"), and requests where two reasonable readings produce different work.

## R2 Missing context
Who is the output for, what is it part of, why is it needed? A prompt that names its purpose lets the model connect the task to relevant knowledge instead of guessing intent. Missing purpose is the single most common gap in prompts that receive unexpected responses.

## R3 Contradictory instructions
Check every pair of requirements for compatibility ("be brief" + "cover everything in detail"), and check terminology drift — the same artifact called three different names reads as three artifacts.

## R4 Scope creep
Distinguish the stated task from the implied one. Asides ("oh and also…", "while you're at it…") often carry requirements that belong in the objective or in a separate request.

## R5 Multiple unrelated tasks
If removing one goal leaves the others fully intact, they are separable. Recommend splitting or explicit sequencing (chaining) rather than deletion — meaning preservation is mandatory.

## R6 Poor formatting
Instructions and data must be visually separable (tags, fences, headings). For long material, the documented ordering is data first, instructions/question last, with quote-grounding for long documents.

## R7 Excessive complexity / over-prescription
Current-generation models follow instructions literally; scaffolding written to overcome older models' reluctance (ALL CAPS, "CRITICAL: you MUST…", exhaustive step lists) now over-triggers or degrades output. Prefer stating goals and constraints over enumerating steps.

## R8 Weak objective
A response can only be as good as the definition of done. Ask: could two people disagree about whether a given response satisfied this prompt? If yes, the objective is weak.

## R9 Missing constraints
Constraints the user holds but does not state (length limits, stack choices, tone, forbidden approaches) surface as "wrong" answers. Elicit and state them.

## R10 Missing output specification
State the expected shape: format, structure, sections, or a short example. Positive instruction ("respond as a table with columns X, Y") beats negative ("don't write paragraphs").
