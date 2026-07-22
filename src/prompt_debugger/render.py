"""Rendering (M2 FR-6).

Report JSON → Markdown projection, and history-record exports in the storage
contract's three formats (markdown/csv/json) with provenance headers.

- **ADR-0002:** Report JSON is canonical; the Markdown a user reads is a
  deterministic projection of it, regenerable at any time. Rendering is never a
  source of truth. The projection covers every content field the Report schema
  defines (knowledge pins, event, IR segments, findings with evidence,
  estimates, rewrite with changes and notices); layout is this module's
  recorded design.
- **Notices (PL-7):** all fixed notice wording is emitted from
  ``core/knowledge/packs/common/notices.json`` — the single source of truth —
  never re-authored in code. The file is schema-validated on load (fail-closed);
  its ``rationale`` fields are maintainer documentation and are ignored at
  runtime. Notice tokens without a text (a future additive enum member) are
  ignored, per the Rewrite Report contract's compatibility rule.
- **Sanitization (S8):** every value this module interpolates into markdown or
  csv output passes ``sanitize_text``; csv cells are additionally
  formula-escaped (S9) and quoted by the ``csv`` module.
- **Fail-closed:** ``render_report_markdown`` schema-validates its input
  (composite CV-1) and refuses invalid reports with a specific error. Export
  rendering formats records the storage layer has already validated on read
  (S10) and prepared per its privacy rules (redaction, fingerprint stripping) —
  storage remains the only preparer; this module only formats.

Recorded implementation decisions (spec open choices O4/O5):

- **CSV dialect:** the ``csv`` module's default (``excel``) dialect with ``\\n``
  line terminator; provenance emitted as leading ``#``-prefixed lines above the
  header row (``#`` is not an S9 formula leader). One row per record; columns
  ``id, created_at, raw, parent_id, event_kind, findings, prompt_redacted,
  prompt_raw`` — envelope scalars plus the event kind and finding count from
  the embedded report; nulls render as empty cells, booleans as
  ``true``/``false``.
- **Provenance-header wording:** generator name and library version, record
  count, content mode (``redacted (default)`` vs the explicit raw opt-in), and
  the note PRIVACY.md requires — the export may contain prompt text. No
  generation timestamp: outputs must be deterministic (the only sanctioned
  time-dependent values are record ids and fields already inside the data).
- **Markdown layout:** every free-form report field — any string the schemas
  leave unconstrained by enum/pattern/const, and therefore newline-permitting
  (segment text and notes, evidence quotes, event verbatim and notes, finding
  explanation and fix, estimate hypothesis and reasoning, rewrite text,
  gate_reason, change text and rationale, the knowledge version strings, notice
  texts, and prompts in exports) — renders as ``> `` blockquote lines, the one
  structure-preserving representation, so content cannot masquerade as document
  structure (no injected headings, list items, or rules). Schema-constrained
  values (ids, enums, kinds, severities, patterned versions and timestamps,
  booleans, counts) stay inline. Exports embed each record's report via the
  same projection function that renders a live report (regenerability,
  ADR-0002), separated by ``---`` rules.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from . import __version__
from .paths import contracts_dir, knowledge_dir
from .sanitize import escape_csv_cell, sanitize_text
from .schema import validate, validate_report

_EXPORT_FORMATS = ("csv", "json", "markdown")

_CSV_COLUMNS = (
    "id",
    "created_at",
    "raw",
    "parent_id",
    "event_kind",
    "findings",
    "prompt_redacted",
    "prompt_raw",
)


class RenderError(Exception):
    """Base class for rendering failures. Every failure is specific and fail-closed."""


class RenderValidationError(RenderError):
    """The input failed schema validation; nothing was rendered."""

    def __init__(self, message: str, problems: list[str]) -> None:
        self.problems = problems
        super().__init__(message + ": " + "; ".join(problems))


# --- notices (single source of truth) --------------------------------------------------


def _notice_texts() -> dict[str, str]:
    """Map notice token → fixed text from ``notices.json`` (PL-7: canonical
    wording, never re-authored). Schema-validated on load, fail-closed.
    ``rationale`` fields must not affect runtime behavior and are dropped."""
    path = knowledge_dir() / "packs" / "common" / "notices.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RenderError(f"invalid notices file at {path}: {exc}") from exc
    schema = json.loads(
        (contracts_dir() / "knowledge" / "notices.schema.json").read_text(encoding="utf-8")
    )
    errors = validate(data, schema)
    if errors:
        raise RenderValidationError(f"notices file at {path} failed validation", errors)
    return {n["notice"]: n["text"] for n in data["notices"]}


# --- Report JSON → Markdown projection (ADR-0002) --------------------------------------


def render_report_markdown(report: dict[str, Any]) -> str:
    """The deterministic Markdown projection of one Report JSON.

    Fail-closed: the report is composite-schema-validated (CV-1) first. Every
    interpolated value is sanitized (S8). Fixed notice wording comes from
    ``notices.json`` (PL-7)."""
    errors = validate_report(report)
    if errors:
        raise RenderValidationError("report failed schema validation", errors)

    lines: list[str] = ["# Prompt analysis report", ""]
    knowledge = report["knowledge"]
    policy = knowledge.get("policy_version")
    # created_at is pattern-anchored by the schema (structured); the knowledge
    # version strings carry no schema pattern, so they are free-form text and
    # render inside the structure-preserving blockquote like all such fields.
    lines.append(f"- Created: {_s(report['created_at'])}")
    lines.append("- Knowledge:")
    lines += _quote_block(
        f"{knowledge['provider']} {knowledge['knowledge_version']}"
        f" · rubric {knowledge['rubric_version']}"
        f" · policy {policy if policy is not None else 'none'}"
    )

    event = report.get("event")
    if event is not None:
        lines += ["", "## Observed event", ""]
        lines.append(f"- Kind: {_s(event['kind'])}")
        lines.append(f"- Surface: {_s(event['surface'])}")
        verbatim = event.get("verbatim")
        if verbatim is None:
            lines.append("- Verbatim: (not provided)")
        else:
            lines.append("- Verbatim:")
            lines += _quote_block(verbatim)
        match = event.get("documented_match")
        lines.append(f"- Documented match: {_s(match) if match is not None else 'none'}")
        notes = event.get("notes")
        if notes is not None:
            lines.append("- Notes:")
            lines += _quote_block(notes)

    ir = report["ir"]
    lines += ["", "## Prompt structure", ""]
    for segment in ir.get("segments", []):
        lines.append(f"- {_s(segment['id'])} ({_s(segment['kind'])}):")
        lines += _quote_block(segment["text"])
        note = segment.get("note")
        if note is not None:
            lines.append("  - Note:")
            lines += _quote_block(note)
    remainder = "yes" if ir.get("unsegmented_remainder") else "no"
    lines.append(f"- Unsegmented remainder: {remainder}")

    findings = report["findings"]
    lines += ["", f"## Findings ({len(findings)})"]
    if not findings:
        lines += ["", "- none"]
    for finding in findings:
        lines += [
            "",
            f"### {_s(finding['id'])} — {_s(finding['dimension'])},"
            f" severity {_s(finding['severity'])}",
            "",
        ]
        for evidence in finding["evidence"]:
            segment_id = evidence.get("segment")
            where = f"segment {_s(segment_id)}" if segment_id is not None else "unsegmented"
            lines.append(f"- Evidence ({where}):")
            lines += _quote_block(evidence["quote"])
        lines.append("- Explanation:")
        lines += _quote_block(finding["explanation"])
        lines.append("- Fix:")
        lines += _quote_block(finding["fix"])

    estimates = report.get("estimates")
    if estimates:
        lines += ["", "## Estimated contributing factors", ""]
        for estimate in estimates:
            lines.append(f"- Confidence {_s(estimate['confidence'])}:")
            lines += _quote_block(estimate["hypothesis"])
            lines.append("  - Reasoning:")
            lines += _quote_block(estimate["reasoning"])

    rewrite = report.get("rewrite")
    if rewrite is not None:
        lines += ["", "## Rewrite", ""]
        lines.append(f"- Gate: {_s(rewrite['gate'])}")
        gate_reason = rewrite.get("gate_reason")
        if gate_reason is not None:
            lines.append("- Gate reason:")
            lines += _quote_block(gate_reason)
        text = rewrite.get("text")
        if text is None:
            lines.append("- Rewritten prompt: none (gate declined)")
        else:
            lines.append("- Rewritten prompt:")
            lines += _quote_block(text)
        changes = rewrite.get("changes", [])
        if changes:
            lines.append("- Changes:")
            for change in changes:
                technique = change.get("technique")
                label = _s(technique) if technique is not None else "mechanical edit"
                lines.append(f"  - Change ({label}):")
                lines += _quote_block(change["change"])
                lines.append("  - Rationale:")
                lines += _quote_block(change["rationale"])
        else:
            lines.append("- Changes: none")
        notice_lines = _notice_block(rewrite.get("notices", []))
        if notice_lines:
            lines.append("- Notices:")
            lines += notice_lines

    return "\n".join(lines) + "\n"


def _notice_block(tokens: list[str]) -> list[str]:
    """Blockquoted fixed texts for the notice tokens present, from notices.json.
    Tokens without a text (future additive enum members) are ignored per the
    Rewrite Report contract's compatibility rule."""
    texts = _notice_texts()
    lines: list[str] = []
    for token in tokens:
        text = texts.get(token)
        if text is None:
            continue
        lines += _quote_block(text)
    return lines


def _quote_block(text: str) -> list[str]:
    """Content as ``> `` blockquote lines: prompt-like text cannot masquerade
    as document structure, and multi-line content stays visibly one value."""
    sanitized = sanitize_text(text)
    return ["> " + line for line in sanitized.splitlines()] or ["> "]


def _s(value: Any) -> str:
    """Sanitize any interpolated value (S8: applied on every export path)."""
    return sanitize_text(str(value))


# --- history-record exports with provenance headers ------------------------------------


def render_export(fmt: str, records: list[dict[str, Any]], *, include_raw: bool = False) -> str:
    """Render storage-prepared history records in one of the storage contract's
    export formats, each carrying a provenance header. The storage layer is the
    only preparer (validation on read, redaction defaults, fingerprint
    stripping); this module only formats."""
    if fmt == "markdown":
        return _export_markdown(records, include_raw)
    if fmt == "csv":
        return _export_csv(records, include_raw)
    if fmt == "json":
        return _export_json(records, include_raw)
    raise RenderError(
        f"export format '{fmt}' is not supported; available: {', '.join(_EXPORT_FORMATS)}"
    )


def _provenance(records: list[dict[str, Any]], include_raw: bool) -> dict[str, Any]:
    """Deterministic provenance: no generation timestamp — the only sanctioned
    time-dependent values are record ids and fields already inside the data."""
    content = "raw content included (explicit opt-in)" if include_raw else "redacted (default)"
    return {
        "generator": "prompt-debugger",
        "generator_version": __version__,
        "records": len(records),
        "content": content,
        "note": "This export may contain prompt text; handle it accordingly.",
    }


def _export_markdown(records: list[dict[str, Any]], include_raw: bool) -> str:
    prov = _provenance(records, include_raw)
    lines: list[str] = [
        "# Prompt Debugger — history export",
        "",
        f"- Generator: {prov['generator']} {prov['generator_version']}",
        f"- Records: {prov['records']}",
        f"- Content: {prov['content']}",
        f"- Note: {prov['note']}",
    ]
    for record in records:
        lines += ["", "---", "", f"## Record {_s(record['id'])}", ""]
        lines.append(f"- Created: {_s(record.get('created_at', ''))}")
        lines.append(f"- Raw: {'yes' if record.get('raw') else 'no'}")
        parent = record.get("parent_id")
        lines.append(f"- Parent: {_s(parent) if parent is not None else 'none'}")
        lines.append("- Prompt (redacted):")
        lines += _quote_block(str(record.get("prompt_redacted", "")))
        prompt_raw = record.get("prompt_raw")
        if prompt_raw is not None:
            lines.append("- Prompt (raw):")
            lines += _quote_block(str(prompt_raw))
        lines += ["", render_report_markdown(record["report"]).rstrip("\n")]
    return "\n".join(lines) + "\n"


def _export_csv(records: list[dict[str, Any]], include_raw: bool) -> str:
    prov = _provenance(records, include_raw)
    header_lines = [
        "# Prompt Debugger history export",
        f"# Generator: {prov['generator']} {prov['generator_version']}",
        f"# Records: {prov['records']}",
        f"# Content: {prov['content']}",
        f"# Note: {prov['note']}",
    ]
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_CSV_COLUMNS)
    for record in records:
        report = record["report"]
        event = report.get("event")
        writer.writerow(
            [
                _cell(record.get("id")),
                _cell(record.get("created_at")),
                _cell(record.get("raw", False)),
                _cell(record.get("parent_id")),
                _cell(event["kind"] if event is not None else "none"),
                _cell(len(report.get("findings", []))),
                _cell(record.get("prompt_redacted")),
                _cell(record.get("prompt_raw")),
            ]
        )
    return "\n".join(header_lines) + "\n" + buffer.getvalue()


def _cell(value: Any) -> str:
    """CSV cell: nulls empty, booleans lowercase, everything sanitized (S8) and
    formula-escaped (S9); the csv module handles quoting."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return escape_csv_cell(sanitize_text(str(value)))


def _export_json(records: list[dict[str, Any]], include_raw: bool) -> str:
    payload = {"provenance": _provenance(records, include_raw), "records": records}
    return json.dumps(payload, ensure_ascii=False, indent=2)
