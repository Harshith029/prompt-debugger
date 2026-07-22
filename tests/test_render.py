"""Rendering tests (M2 FR-6).

Covers the Report JSON → Markdown projection (ADR-0002: every content field of
the canonical report appears in the projection; deterministic; fail-closed on
invalid input; sanitized per S8), notice wording sourced verbatim from
notices.json (PL-7 — never re-authored in code), and the history-record exports
in the storage contract's three formats with provenance headers (PRIVACY.md:
the header notes the export may contain prompt text; CSV cells formula-escaped
per S9; each format verified independently, including through the real
``store.export`` path).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from prompt_debugger import render as pdrender
from prompt_debugger import store as pdstore

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

PROMPT = "Explain how our caching layer works."
LEAKY_PROMPT = "deploy with key sk-ABCDEFGHIJKLMNOP1234 and email alice@example.com today"


def _report() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / "report-full.json").read_text("utf-8"))
    return data


def _notices() -> dict[str, str]:
    data = json.loads(
        (REPO / "core" / "knowledge" / "packs" / "common" / "notices.json").read_text("utf-8")
    )
    return {n["notice"]: n["text"] for n in data["notices"]}


def _taxonomy_ids() -> set[str]:
    entries = json.loads(
        (REPO / "core" / "knowledge" / "packs" / "anthropic" / "events.json").read_text("utf-8")
    )["entries"]
    return {e["id"] for e in entries}


TAXONOMY = _taxonomy_ids()


def _open(tmp_path: Path) -> pdstore.Store:
    return pdstore.Store.open(tmp_path / "project", home=tmp_path / "home")


# --- Report JSON → Markdown projection --------------------------------------------------


def test_projection_contains_every_content_field() -> None:
    report = _report()
    md = pdrender.render_report_markdown(report)
    # knowledge pins
    assert "2026-07-07T12:00:00Z" in md
    assert "anthropic 2026.07-m1" in md and "rubric 2026.07-m1" in md
    assert "policy 2026.07-m1" in md
    # observed event
    assert "model_switch" in md and "cli" in md
    assert "Response produced by a fallback model." in md
    assert "evt-model-switch-visible" in md
    assert "citation stays within documented API mechanisms" in md
    # IR
    assert "s1 (task):" in md
    assert "> Explain how our caching layer works." in md
    assert "Unsegmented remainder: yes" in md
    # findings with evidence
    assert "## Findings (1)" in md
    assert "f1 — R2, severity medium" in md
    assert "Evidence (segment s1):" in md
    assert "names no audience or purpose" in md  # explanation
    assert "Name who the explanation is for" in md  # fix
    # estimates
    assert "Confidence low:" in md
    assert "left the intended audience ambiguous" in md
    assert "observation about the prompt, not the provider" in md  # reasoning
    # rewrite
    assert "Gate: passed" in md
    assert "for <who will read this" in md  # rewritten text
    assert "added explicit slots" in md and "(T2)" in md
    assert "surfaces missing context as slots" in md  # rationale


def test_projection_notice_wording_is_verbatim_from_notices_json() -> None:
    md = pdrender.render_report_markdown(_report())
    non_guarantee = _notices()["non_guarantee"]
    assert f"> {non_guarantee}" in md  # exact fixed wording, single source of truth


def test_projection_omits_null_sections() -> None:
    report = _report()
    report["event"] = None
    report["estimates"] = None
    report["rewrite"] = None
    md = pdrender.render_report_markdown(report)
    assert "## Observed event" not in md
    assert "## Estimated contributing factors" not in md
    assert "## Rewrite" not in md
    assert "## Prompt structure" in md and "## Findings (1)" in md


def test_projection_declined_gate_renders_reason_and_declined_notice() -> None:
    report = _report()
    report["estimates"] = None
    report["event"] = None
    report["rewrite"] = {
        "rewrite_version": 1,
        "gate": "declined",
        "gate_reason": "circumvention intent per the misuse policy",
        "text": None,
        "changes": [],
        "notices": ["gate_declined"],
    }
    md = pdrender.render_report_markdown(report)
    assert "Gate: declined" in md
    assert "circumvention intent per the misuse policy" in md
    assert "Rewritten prompt: none (gate declined)" in md
    assert "Changes: none" in md
    assert f"> {_notices()['gate_declined']}" in md


def test_projection_is_deterministic() -> None:
    report = _report()
    assert pdrender.render_report_markdown(report) == pdrender.render_report_markdown(report)


def test_projection_sanitizes_content() -> None:
    report = _report()
    report["findings"][0]["explanation"] = "bad \x1b[31mred\x1b[0m text\x07 here"
    md = pdrender.render_report_markdown(report)
    assert "\x1b" not in md and "\x07" not in md
    assert "bad red text here" in md


def test_multiline_explanation_cannot_inject_markdown_structure() -> None:
    """A schema-valid free-form field containing a newline plus '## ...' must
    render as literal blockquoted content, never as a real Markdown heading."""
    report = _report()
    report["findings"][0]["explanation"] = "ordinary explanation\n## Injected section"
    md = pdrender.render_report_markdown(report)
    assert "ordinary explanation" in md
    assert "## Injected section" in md  # the literal text is preserved
    assert "> ## Injected section" in md  # ...inside the blockquote
    # ...and no line of the document is an actual injected heading
    assert not any(line.startswith("## Injected section") for line in md.splitlines())


def test_multiline_free_form_fields_are_structure_preserving_everywhere() -> None:
    """The protection is generalized: newline-permitting free-form fields from
    other report sections (event notes, IR segment note, estimate reasoning,
    rewrite gate_reason and change rationale, knowledge version strings) cannot
    create document structure either."""
    payload = "text\n## Injected section\n- injected item\n---"
    report = _report()
    report["knowledge"]["provider"] = "anthropic\n## Injected section"
    report["event"]["notes"] = payload
    report["ir"]["segments"][0]["note"] = payload
    report["findings"][0]["fix"] = payload
    report["estimates"][0]["hypothesis"] = payload
    report["estimates"][0]["reasoning"] = payload
    report["rewrite"]["gate"] = "conditional"
    report["rewrite"]["gate_reason"] = payload
    report["rewrite"]["changes"][0]["change"] = payload
    report["rewrite"]["changes"][0]["rationale"] = payload
    md = pdrender.render_report_markdown(report)
    document_lines = md.splitlines()
    headings = [line for line in document_lines if line.startswith("#")]
    assert all("Injected" not in heading for heading in headings)
    assert not any(line == "- injected item" for line in document_lines)
    assert not any(line == "---" for line in document_lines)
    assert md.count("> ## Injected section") >= 9  # every field stayed blockquoted


def test_projection_fails_closed_on_invalid_report() -> None:
    report = _report()
    del report["knowledge"]
    with pytest.raises(pdrender.RenderValidationError, match="knowledge"):
        pdrender.render_report_markdown(report)


# --- exports with provenance headers ----------------------------------------------------


def _prepared_record(record_id: str = "pd-1751884800000-0a1b2c3d") -> dict[str, Any]:
    """A record shaped as the storage layer prepares it for export
    (fingerprints stripped, prompt_raw defaulted to null)."""
    return {
        "record_version": 1,
        "id": record_id,
        "created_at": "2026-07-07T12:00:00+00:00",
        "raw": False,
        "prompt_redacted": PROMPT,
        "prompt_raw": None,
        "parent_id": None,
        "report": _report(),
    }


def test_markdown_export_has_provenance_and_embedded_projection() -> None:
    md = pdrender.render_export("markdown", [_prepared_record()])
    assert "# Prompt Debugger — history export" in md
    assert "- Records: 1" in md
    assert "- Content: redacted (default)" in md
    assert "may contain prompt text" in md  # PRIVACY.md-required note
    assert "## Record pd-1751884800000-0a1b2c3d" in md
    assert "- Raw: no" in md
    assert "# Prompt analysis report" in md  # embedded projection, same renderer


def test_csv_export_rows_columns_and_provenance() -> None:
    out = pdrender.render_export(
        "csv", [_prepared_record(), _prepared_record("pd-1751884800001-0a1b2c3e")]
    )
    lines = out.splitlines()
    comment_lines = [ln for ln in lines if ln.startswith("#")]
    assert any("may contain prompt text" in ln for ln in comment_lines)
    assert any("Records: 2" in ln for ln in comment_lines)
    data_lines = [ln for ln in lines if ln and not ln.startswith("#")]
    assert data_lines[0] == (
        "id,created_at,raw,parent_id,event_kind,findings,prompt_redacted,prompt_raw"
    )
    assert len(data_lines) == 3  # header + 2 records
    assert data_lines[1].startswith("pd-1751884800000-0a1b2c3d,")
    assert ",model_switch,1," in data_lines[1]  # event kind + finding count


def test_csv_export_escapes_formula_leaders() -> None:
    record = _prepared_record()
    record["prompt_redacted"] = "=SUM(A1:A9) explain this sheet"
    out = pdrender.render_export("csv", [record])
    assert "'=SUM(A1:A9) explain this sheet" in out  # S9 prefix-escape
    assert "\n=SUM" not in out and ",=SUM" not in out


def test_export_rendering_is_deterministic() -> None:
    records = [_prepared_record()]
    for fmt in ("markdown", "csv", "json"):
        assert pdrender.render_export(fmt, records) == pdrender.render_export(fmt, records)


def test_empty_export_renders_in_every_format() -> None:
    for fmt in ("markdown", "csv", "json"):
        out = pdrender.render_export(fmt, [])
        assert "prompt-debugger" in out
    assert json.loads(pdrender.render_export("json", []))["provenance"]["records"] == 0


def test_render_export_unknown_format_fails_closed() -> None:
    with pytest.raises(pdrender.RenderError, match="not supported"):
        pdrender.render_export("html", [])


# --- through the real store.export path -------------------------------------------------


def test_store_markdown_export_is_redacted_with_provenance(tmp_path: Path) -> None:
    s = _open(tmp_path)
    report = _report()
    report["ir"]["segments"] = [
        {"id": "s1", "kind": "task", "text": "deploy with key", "note": None}
    ]
    report["findings"][0]["evidence"] = [{"segment": "s1", "quote": "deploy with key"}]
    s.append(prompt=LEAKY_PROMPT, report=report, taxonomy_ids=TAXONOMY)
    md = s.export("markdown")
    assert "# Prompt Debugger — history export" in md
    assert "- Content: redacted (default)" in md
    assert "sk-ABCDEFGHIJKLMNOP1234" not in md and "alice@example.com" not in md
    assert "[REDACTED_API_KEY]" in md  # redacted prompt rendered


def test_store_csv_export_one_row_per_record(tmp_path: Path) -> None:
    s = _open(tmp_path)
    for _ in range(2):
        s.append(prompt=PROMPT, report=_report(), taxonomy_ids=TAXONOMY)
    out = s.export("csv")
    data_lines = [ln for ln in out.splitlines() if ln and not ln.startswith("#")]
    assert len(data_lines) == 3  # header + one row per record
    assert "fingerprints" not in out  # PR-3 holds for csv exports too


def test_store_include_raw_markdown_export_is_loud(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = _open(tmp_path)
    report = _report()
    report["ir"]["segments"] = [
        {"id": "s1", "kind": "task", "text": "deploy with key", "note": None}
    ]
    report["findings"][0]["evidence"] = [{"segment": "s1", "quote": "deploy with key"}]
    s.append(
        prompt=LEAKY_PROMPT,
        report=report,
        taxonomy_ids=TAXONOMY,
        raw=True,
        confirm_raw=True,
    )
    md = s.export("markdown", include_raw=True)
    assert "raw content included (explicit opt-in)" in md  # header states the mode
    assert "- Prompt (raw):" in md and "sk-ABCDEFGHIJKLMNOP1234" in md
    assert "WARNING" in capsys.readouterr().err  # store's warning still printed
