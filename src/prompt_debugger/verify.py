"""Runtime invariant verifier (M2 FR-2).

Enforces the relationships the schema subset cannot express — the invariants
catalogued in ``docs/CONTRACT-INVARIANTS.md`` for the Prompt IR, Report, Rewrite
Report, Observable Event, and Prompt Tree contracts. Shape validation is
``schema.py``'s job (FR-1); this module assumes its input is already
schema-valid and checks only the cross-field, cross-document, and content
relationships:

- IR-1/IR-2  — segment text is a verbatim substring of the reference prompt;
              segment ids are unique.
- RPT-1..4   — evidence quotes are verbatim substrings of the reference prompt;
              evidence segments reference existing IR segments; estimates only
              accompany a reported event; finding ids are unique.
- RW-1..3    — gate/text/notices/gate_reason consistency.
- EV-1/EV-2  — kind unknown/none ⇒ no documented_match; a documented_match must
              exist in the supplied event-taxonomy id set.
- PT-1..3    — parent graph references existing nodes and is acyclic; segment_ids
              reference existing IR segments; annotation finding_ids reference
              existing findings.

Two relationships require inputs that live outside the documents themselves and
are therefore parameters, not something this module fetches: the **reference
prompt** (IR-1/RPT-1; the source prompt is in neither schema — contracts README)
and the **event-taxonomy id set** (EV-2; the "loaded taxonomy version"). EV-2 is
fail-closed: an empty ``taxonomy_ids`` rejects any non-null ``documented_match``.

Verification failures are returned as a deterministic list of :class:`Violation`
records ``(invariant, path, message)``; an empty list means the document upholds
every in-scope invariant. The one-repair-pass interaction loop belongs to the M3
skill workflow, not this module. PL-6 is out of scope — M2 builds no policy
decision engine to instrument.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Violation:
    """A single invariant breach.

    ``invariant`` is the catalogue id (e.g. ``"IR-1"``), ``path`` a JSON-path to
    the offending location, ``message`` a human-readable description.
    """

    invariant: str
    path: str
    message: str


def _reroot(violations: list[Violation], prefix: str) -> list[Violation]:
    """Re-root sub-document paths (``$.x``) under ``prefix`` (``$.ir`` -> ``$.ir.x``)."""
    return [Violation(v.invariant, prefix + v.path[1:], v.message) for v in violations]


# --- Prompt IR (IR-1, IR-2) ------------------------------------------------------------


def verify_ir(ir: Mapping[str, Any], reference_prompt: str) -> list[Violation]:
    """IR-1 (segment text ⊂ reference prompt) and IR-2 (unique segment ids)."""
    violations: list[Violation] = []
    seen_ids: set[str] = set()
    segments = ir.get("segments", [])
    for i, segment in enumerate(segments):
        text = segment.get("text")
        if isinstance(text, str) and text not in reference_prompt:
            violations.append(
                Violation(
                    "IR-1",
                    f"$.segments[{i}].text",
                    "segment text is not a verbatim substring of the reference prompt",
                )
            )
        sid = segment.get("id")
        if sid in seen_ids:
            violations.append(
                Violation("IR-2", f"$.segments[{i}].id", f"duplicate segment id '{sid}'")
            )
        elif isinstance(sid, str):
            seen_ids.add(sid)
    return violations


# --- Rewrite Report (RW-1, RW-2, RW-3) -------------------------------------------------


def verify_rewrite(rewrite: Mapping[str, Any]) -> list[Violation]:
    """RW-1 (gate=declined ⇔ text=null), RW-2 (produced rewrite carries non_guarantee),
    RW-3 (gate!=passed ⇒ gate_reason)."""
    violations: list[Violation] = []
    gate = rewrite.get("gate")
    text = rewrite.get("text")
    notices = rewrite.get("notices", [])
    gate_reason = rewrite.get("gate_reason")

    if gate == "declined" and text is not None:
        violations.append(Violation("RW-1", "$.text", "gate=declined requires text=null"))
    if gate != "declined" and text is None:
        violations.append(
            Violation("RW-1", "$.text", "text=null is only allowed when gate=declined")
        )
    if text is not None and "non_guarantee" not in notices:
        violations.append(
            Violation("RW-2", "$.notices", "a produced rewrite must carry the non_guarantee notice")
        )
    if gate != "passed" and gate_reason is None:
        violations.append(Violation("RW-3", "$.gate_reason", "gate!=passed requires gate_reason"))
    return violations


# --- Observable Event (EV-1, EV-2) -----------------------------------------------------


def verify_event(event: Mapping[str, Any], *, taxonomy_ids: Collection[str]) -> list[Violation]:
    """EV-1 (kind unknown/none ⇒ documented_match=null) and EV-2 (documented_match
    exists in the supplied taxonomy id set). EV-2 is fail-closed: an empty
    ``taxonomy_ids`` rejects any non-null ``documented_match``."""
    violations: list[Violation] = []
    kind = event.get("kind")
    documented_match = event.get("documented_match")

    if kind in {"unknown", "none"} and documented_match is not None:
        violations.append(
            Violation(
                "EV-1", "$.documented_match", "kind unknown/none requires documented_match=null"
            )
        )
    if documented_match is not None and documented_match not in taxonomy_ids:
        violations.append(
            Violation(
                "EV-2",
                "$.documented_match",
                f"documented_match '{documented_match}' is not in the loaded event taxonomy",
            )
        )
    return violations


# --- Report JSON (RPT-1..4, composing IR/event/rewrite) --------------------------------


def verify_report(
    report: Mapping[str, Any], reference_prompt: str, *, taxonomy_ids: Collection[str]
) -> list[Violation]:
    """RPT-1..4 plus the composed IR, event, and rewrite invariants.

    ``reference_prompt`` is the source prompt the evidence and segments are
    quoted from (the original prompt for a live report, or ``prompt_redacted``
    for a report embedded in a persisted ``raw: false`` record — contracts README
    / PR-1). ``taxonomy_ids`` is the loaded event-taxonomy id set for EV-2.
    """
    violations: list[Violation] = []

    ir = report.get("ir")
    if isinstance(ir, Mapping):
        violations += _reroot(verify_ir(ir, reference_prompt), "$.ir")
    segment_ids = _segment_ids(ir)

    event = report.get("event")
    if event is not None and isinstance(event, Mapping):
        violations += _reroot(verify_event(event, taxonomy_ids=taxonomy_ids), "$.event")

    rewrite = report.get("rewrite")
    if rewrite is not None and isinstance(rewrite, Mapping):
        violations += _reroot(verify_rewrite(rewrite), "$.rewrite")

    seen_finding_ids: set[str] = set()
    findings = report.get("findings", [])
    for i, finding in enumerate(findings):
        fid = finding.get("id")
        if fid in seen_finding_ids:
            violations.append(
                Violation("RPT-4", f"$.findings[{i}].id", f"duplicate finding id '{fid}'")
            )
        elif isinstance(fid, str):
            seen_finding_ids.add(fid)
        for j, evidence in enumerate(finding.get("evidence", [])):
            quote = evidence.get("quote")
            if isinstance(quote, str) and quote not in reference_prompt:
                violations.append(
                    Violation(
                        "RPT-1",
                        f"$.findings[{i}].evidence[{j}].quote",
                        "evidence quote is not a verbatim substring of the reference prompt",
                    )
                )
            segment = evidence.get("segment")
            if segment is not None and segment not in segment_ids:
                violations.append(
                    Violation(
                        "RPT-2",
                        f"$.findings[{i}].evidence[{j}].segment",
                        f"evidence segment '{segment}' does not reference an existing IR segment",
                    )
                )

    if report.get("estimates") is not None and report.get("event") is None:
        violations.append(
            Violation("RPT-3", "$.estimates", "estimates require a reported event (event=null)")
        )
    return violations


def _segment_ids(ir: Any) -> set[str]:
    if not isinstance(ir, Mapping):
        return set()
    return {s["id"] for s in ir.get("segments", []) if isinstance(s.get("id"), str)}


# --- Prompt Tree (PT-1, PT-2, PT-3) ----------------------------------------------------


def verify_prompt_tree(
    tree: Mapping[str, Any], *, ir: Mapping[str, Any], report: Mapping[str, Any]
) -> list[Violation]:
    """PT-1 (parent_id references an existing node; parent graph acyclic),
    PT-2 (segment_ids reference existing IR segments), PT-3 (annotation finding_ids
    reference findings in the accompanying report)."""
    violations: list[Violation] = []
    nodes = tree.get("nodes", [])
    node_ids = {n["id"] for n in nodes if isinstance(n.get("id"), str)}
    parent_of: dict[str, Any] = {
        n["id"]: n.get("parent_id") for n in nodes if isinstance(n.get("id"), str)
    }
    ir_segment_ids = _segment_ids(ir)
    finding_ids = {f["id"] for f in report.get("findings", []) if isinstance(f.get("id"), str)}

    for i, node in enumerate(nodes):
        parent_id = node.get("parent_id")
        if parent_id is not None and parent_id not in node_ids:
            violations.append(
                Violation(
                    "PT-1", f"$.nodes[{i}].parent_id", "parent_id references a non-existent node"
                )
            )
        node_id = node.get("id")
        if isinstance(node_id, str) and _in_cycle(node_id, parent_of):
            violations.append(
                Violation("PT-1", f"$.nodes[{i}].parent_id", "the parent graph contains a cycle")
            )
        for k, sid in enumerate(node.get("segment_ids", [])):
            if sid not in ir_segment_ids:
                violations.append(
                    Violation(
                        "PT-2",
                        f"$.nodes[{i}].segment_ids[{k}]",
                        f"segment_id '{sid}' does not reference an existing IR segment",
                    )
                )
        for a, annotation in enumerate(node.get("annotations", [])):
            finding_id = annotation.get("finding_id")
            if finding_id not in finding_ids:
                violations.append(
                    Violation(
                        "PT-3",
                        f"$.nodes[{i}].annotations[{a}].finding_id",
                        f"finding_id '{finding_id}' does not reference a finding in the report",
                    )
                )
    return violations


def _in_cycle(start: str, parent_of: Mapping[str, Any]) -> bool:
    """True if following parent pointers from ``start`` returns to ``start``.

    Terminates on any revisited node, so a cycle that does not contain ``start``
    is traversed without a false positive.
    """
    seen: set[str] = set()
    current = parent_of.get(start)
    while current is not None and current not in seen:
        if current == start:
            return True
        seen.add(current)
        current = parent_of.get(current)
    return False
