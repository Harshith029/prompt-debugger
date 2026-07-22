"""CLI tests (M2 FR-10).

Exercises the argparse entry point that wraps the frozen library: every
storage-contract operation plus verify/render, dispatched through ``cli.main``.
Covers positive/negative/edge cases, fail-closed exit codes, contract naming
(O10), privacy carried through from the wrapped modules (PR-1 redaction, PR-3
fingerprint exclusion), determinism, and integration with FR-1..FR-7.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from prompt_debugger import cli
from prompt_debugger import store as pdstore

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_generate_store() -> Any:
    # Reuse the FR-11 perf harness's tested generator to make many valid records
    # quickly (the size-warning boundary needs stores near the 1000 threshold).
    spec = importlib.util.spec_from_file_location(
        "perf_gen_for_cli", REPO / "benchmarks" / "perf" / "harness.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.generate_store


_generate_store = _load_generate_store()

PROMPT = "Explain how our caching layer works."
LEAKY_PROMPT = "deploy with key sk-ABCDEFGHIJKLMNOP1234 and email alice@example.com today"


def _report() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / "report-full.json").read_text("utf-8"))
    return data


def _leaky_report() -> dict[str, Any]:
    report = _report()
    report["ir"]["segments"] = [
        {
            "id": "s1",
            "kind": "task",
            "text": "deploy with key sk-ABCDEFGHIJKLMNOP1234",
            "note": None,
        }
    ]
    report["findings"][0]["evidence"] = [
        {"segment": "s1", "quote": "key sk-ABCDEFGHIJKLMNOP1234 and email alice@example.com"}
    ]
    report["findings"][0]["explanation"] = "the prompt leaks a key"
    report["event"]["verbatim"] = "error mentioning alice@example.com"
    return report


def _files(tmp_path: Path, report: dict[str, Any] | None = None, prompt: str = PROMPT) -> Path:
    rp = tmp_path / "report.json"
    rp.write_text(json.dumps(report if report is not None else _report()), encoding="utf-8")
    pp = tmp_path / "prompt.txt"
    pp.write_text(prompt, encoding="utf-8")
    return tmp_path


def _store(tmp_path: Path) -> list[str]:
    return ["--home", str(tmp_path / "home"), "--project", str(tmp_path / "project")]


def _append(tmp_path: Path, *extra: str) -> list[str]:
    return [
        "append",
        *_store(tmp_path),
        "--report",
        str(tmp_path / "report.json"),
        "--prompt-file",
        str(tmp_path / "prompt.txt"),
        *extra,
    ]


def _verify(tmp_path: Path) -> list[str]:
    return [
        "verify",
        "--report",
        str(tmp_path / "report.json"),
        "--prompt-file",
        str(tmp_path / "prompt.txt"),
    ]


# --- storage operations through the CLI -------------------------------------------------


def test_list_empty_store_is_ok(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["list", *_store(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out) == []


def test_append_prints_id_then_list_and_get(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _files(tmp_path)
    assert cli.main(_append(tmp_path)) == 0
    record_id = capsys.readouterr().out.strip()
    assert record_id.startswith("pd-")

    assert cli.main(["list", *_store(tmp_path)]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert [r["id"] for r in listed] == [record_id]

    assert cli.main(["get", *_store(tmp_path), record_id]) == 0
    got = json.loads(capsys.readouterr().out)
    assert got["id"] == record_id and got["raw"] is False


def test_append_redacts_by_default_pr1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _files(tmp_path, report=_leaky_report(), prompt=LEAKY_PROMPT)
    assert cli.main(_append(tmp_path)) == 0
    record_id = capsys.readouterr().out.strip()
    assert cli.main(["get", *_store(tmp_path), record_id]) == 0
    blob = capsys.readouterr().out
    assert "sk-ABCDEFGHIJKLMNOP1234" not in blob and "alice@example.com" not in blob
    assert "[REDACTED_API_KEY]" in blob


def test_export_json_excludes_fingerprints_pr3(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _files(tmp_path)
    assert cli.main(_append(tmp_path)) == 0
    capsys.readouterr()
    assert cli.main(["export", *_store(tmp_path), "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["provenance"]["records"] == 1
    assert "fingerprints" not in json.dumps(payload)


def test_export_markdown_and_csv_have_provenance(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _files(tmp_path)
    assert cli.main(_append(tmp_path)) == 0
    capsys.readouterr()
    assert cli.main(["export", *_store(tmp_path), "markdown"]) == 0
    assert "# Prompt Debugger — history export" in capsys.readouterr().out
    assert cli.main(["export", *_store(tmp_path), "csv"]) == 0
    assert "# Prompt Debugger history export" in capsys.readouterr().out


def test_compare_and_trends(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _files(tmp_path)
    assert cli.main(_append(tmp_path)) == 0
    a = capsys.readouterr().out.strip()
    assert cli.main(_append(tmp_path)) == 0
    b = capsys.readouterr().out.strip()
    assert cli.main(["compare", *_store(tmp_path), a, b]) == 0
    capsys.readouterr()
    assert cli.main(["trends", *_store(tmp_path)]) == 0
    trends = json.loads(capsys.readouterr().out)
    assert {t["id"] for t in trends} == {a, b}


def test_raw_requires_confirmation_fail_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _files(tmp_path, report=_leaky_report(), prompt=LEAKY_PROMPT)
    assert cli.main(_append(tmp_path, "--raw")) == 1
    assert "confirm" in capsys.readouterr().err.lower()
    # fail-closed: nothing was written
    assert cli.main(["list", *_store(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out) == []


def test_raw_with_confirmation_and_strip_raw(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _files(tmp_path, report=_leaky_report(), prompt=LEAKY_PROMPT)
    assert cli.main(_append(tmp_path, "--raw", "--confirm-raw")) == 0
    record_id = capsys.readouterr().out.strip()
    assert cli.main(["list", *_store(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)[0]["raw"] is True
    assert cli.main(["strip-raw", *_store(tmp_path), record_id]) == 0
    capsys.readouterr()
    assert cli.main(["get", *_store(tmp_path), record_id]) == 0
    assert json.loads(capsys.readouterr().out)["raw"] is False


def test_delete_and_purge(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _files(tmp_path)
    assert cli.main(_append(tmp_path)) == 0
    rid = capsys.readouterr().out.strip()
    assert cli.main(["delete", *_store(tmp_path), rid]) == 0
    assert capsys.readouterr().out.strip() == f"deleted {rid}"
    assert cli.main(_append(tmp_path)) == 0
    capsys.readouterr()
    assert cli.main(["purge", *_store(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == "purged 1"


def test_doctor_migrate_archive(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _files(tmp_path)
    assert cli.main(_append(tmp_path)) == 0
    capsys.readouterr()
    assert cli.main(["doctor", *_store(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] == 1
    assert cli.main(["migrate", *_store(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["records"] == 1
    assert cli.main(["archive", *_store(tmp_path)]) == 0
    assert "archive" in capsys.readouterr().out


def test_archive_output_is_sanitized_s8(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # The archive path is built from --home/--project (untrusted) and stringified
    # by the CLI. A filesystem cannot hold control bytes in a name, so the crafted
    # path is injected; the CLI must sanitize it before printing (S8), not emit
    # the CSI / C0 / C1 bytes raw.
    crafted = Path("ARCHIVED-\x1b[31m\x07\x85-OK.jsonl")

    def fake_archive(self: object, **kwargs: object) -> Path:
        return crafted

    # Patch the Store class the CLI uses (same class object it imported).
    monkeypatch.setattr(pdstore.Store, "archive", fake_archive)
    assert cli.main(["archive", *_store(tmp_path)]) == 0
    out = capsys.readouterr().out
    for control in ("\x1b", "\x07", "\x85", "\x9b"):
        assert control not in out
    assert "ARCHIVED" in out and "OK" in out  # benign path text and structure preserved


def test_migrate_json_output_is_sanitized_s8(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # migrate emits {"backup": <path>, "records": N} as JSON. The backup path is
    # CLI-derived (from --home/--project); json.dumps(ensure_ascii=False) would
    # emit C1 controls (0x85 NEL, 0x9b 8-bit CSI) in it raw. The CLI must sanitize
    # dynamic string values before emission (S8), keeping the JSON valid.
    crafted = {"backup": "backup-\x1b[31m\x9b31m\x85\x07-OK.jsonl", "records": 1}

    def fake_migrate(self: object, **kwargs: object) -> dict[str, object]:
        return crafted

    monkeypatch.setattr(pdstore.Store, "migrate", fake_migrate)
    assert cli.main(["migrate", *_store(tmp_path)]) == 0
    out = capsys.readouterr().out
    for control in ("\x1b", "\x07", "\x85", "\x9b"):
        assert control not in out
    payload = json.loads(out)  # JSON remains valid
    assert payload["records"] == 1  # value type and wording preserved
    assert "OK" in payload["backup"]  # the sanitized path value is still present


def test_get_unknown_id_fails_closed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["get", *_store(tmp_path), "pd-0000000000-00000000"]) == 1
    assert "error:" in capsys.readouterr().err


def test_list_suggests_archive_at_size_threshold(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Documented behavior (config size_warn_records, measured default 1000 in
    # M2 FR-11): `list` suggests 'archive' at or above the threshold and stays
    # silent below it. Boundary at threshold-1 / threshold / threshold+1.
    for count, expect_warning in ((999, False), (1000, True), (1001, True)):
        home = tmp_path / f"home-{count}"
        project = tmp_path / f"project-{count}"
        _generate_store(home, project, count)
        assert cli.main(["list", "--home", str(home), "--project", str(project)]) == 0
        captured = capsys.readouterr()
        assert len(json.loads(captured.out)) == count  # stdout JSON preserved
        assert ("archive" in captured.err) == expect_warning


def test_error_diagnostics_are_sanitized_s8(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The unknown id is echoed verbatim into the RecordNotFoundError message; a
    # CSI sequence, C0 (BEL/NUL), C1 (NEL), and a bare ESC in it must be stripped
    # before the diagnostic reaches stderr (S8), not emitted raw.
    malicious_id = "pd-\x1b[31m\x07\x00\x85\x1bevil"
    assert cli.main(["get", *_store(tmp_path), malicious_id]) == 1
    err = capsys.readouterr().err
    for control in ("\x1b", "\x07", "\x00", "\x85", "\x9b"):
        assert control not in err
    assert "error:" in err  # existing wording preserved
    assert "evil" in err  # benign text survives — only controls are stripped


# --- verify / render --------------------------------------------------------------------


def test_verify_clean_report_is_ok(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _files(tmp_path)
    assert cli.main(_verify(tmp_path)) == 0
    assert json.loads(capsys.readouterr().out) == []


def test_verify_detects_invariant_violation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = _report()
    bad["findings"][0]["evidence"][0]["quote"] = "not a substring of the prompt at all"
    _files(tmp_path, report=bad)
    assert cli.main(_verify(tmp_path)) == 1
    violations = json.loads(capsys.readouterr().out)
    assert any(v["invariant"] == "RPT-1" for v in violations)


def test_verify_schema_invalid_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = _report()
    del bad["knowledge"]
    _files(tmp_path, report=bad)
    assert cli.main(_verify(tmp_path)) == 1
    assert "schema_errors" in json.loads(capsys.readouterr().out)


def test_render_outputs_markdown_projection(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _files(tmp_path)
    assert cli.main(["render", "--report", str(tmp_path / "report.json")]) == 0
    assert "# Prompt analysis report" in capsys.readouterr().out


def test_render_is_deterministic(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _files(tmp_path)
    args = ["render", "--report", str(tmp_path / "report.json")]
    assert cli.main(args) == 0
    first = capsys.readouterr().out
    assert cli.main(args) == 0
    assert capsys.readouterr().out == first


# --- fail-closed edges ------------------------------------------------------------------


def test_report_not_an_object_fails_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "report.json").write_text("[]", encoding="utf-8")
    assert cli.main(["render", "--report", str(tmp_path / "report.json")]) == 1
    assert "not a JSON object" in capsys.readouterr().err


def test_unknown_command_is_usage_error() -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["bogus"])
    assert exc.value.code == 2


def test_no_command_is_usage_error() -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main([])
    assert exc.value.code == 2


def test_parser_diagnostics_are_sanitized_s8(capsys: pytest.CaptureFixture[str]) -> None:
    # argparse's "unrecognized arguments" error formats the stray token with %s
    # (not %r), so control bytes in it would reach stderr raw — before main's
    # exception boundary. The sanitizing parser must strip CSI / C0 / C1 while
    # preserving usage formatting, the argument text, and exit code 2.
    stray = "strayarg-\x1b[31m\x9b31m\x85\x07-END"
    with pytest.raises(SystemExit) as exc:
        cli.main(["list", stray])
    assert exc.value.code == 2  # parser semantics unchanged
    err = capsys.readouterr().err
    for control in ("\x1b", "\x07", "\x85", "\x9b"):
        assert control not in err
    assert "strayarg" in err and "END" in err  # sanitized argument text preserved
    assert "usage:" in err  # usage formatting preserved
