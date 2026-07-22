"""Storage-layer tests (M2 FR-5).

Covers the storage contract's operations and the PR-1..PR-6 invariants against
the real write path: append pipeline (validate → redact → fingerprint → atomic
append under lock), raw gating, read-path sanitization (S10), partial-tail
tolerance (PR-4), symlink refusal (PR-5), doctor quarantine, migrate-with-backup
(PR-6), archive, delete/purge, strip-raw, compare (diff only), trends, and
config semantics (ADR-0004 project-local opt-in; fail-closed gates).

Review-fix regressions: PR-1 enforced post-redaction (partial-secret quotes),
short-write detection, write-time symlink races, fail-closed read paths,
corrupt-history migration refusal, and concurrent writers under the lock.
"""

from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any

import pytest

from prompt_debugger import store as pdstore

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

PROMPT = "Explain how our caching layer works."
LEAKY_PROMPT = "deploy with key sk-ABCDEFGHIJKLMNOP1234 and email alice@example.com today"


def _taxonomy_ids() -> set[str]:
    entries = json.loads(
        (REPO / "core" / "knowledge" / "packs" / "anthropic" / "events.json").read_text("utf-8")
    )["entries"]
    return {e["id"] for e in entries}


TAXONOMY = _taxonomy_ids()


def _report() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / "report-full.json").read_text("utf-8"))
    return data


def _secret_report() -> dict[str, Any]:
    """A schema-valid report whose content quotes LEAKY_PROMPT verbatim."""
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


def _open(tmp_path: Path) -> pdstore.Store:
    return pdstore.Store.open(tmp_path / "project", home=tmp_path / "home")


def _append(s: pdstore.Store, **kwargs: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {"prompt": PROMPT, "report": _report(), "taxonomy_ids": TAXONOMY}
    defaults.update(kwargs)
    result: dict[str, Any] = s.append(**defaults)
    return result


# --- layout and opening ----------------------------------------------------------------


def test_open_creates_layout_salt_and_stable_key(tmp_path: Path) -> None:
    s = _open(tmp_path)
    assert s.store_dir.is_dir()
    assert (s.store_dir / "salt").read_bytes() != b"" and len(
        (s.store_dir / "salt").read_bytes()
    ) == 32
    assert (tmp_path / "home" / "user_salt").exists()
    again = _open(tmp_path)
    assert again.store_dir == s.store_dir  # project key stable across opens


def test_project_local_opt_in_is_self_ignoring(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / "config.json").write_text(
        json.dumps(
            {"config_version": 1, "storage_scope": "project", "project_local_acknowledged": True}
        ),
        encoding="utf-8",
    )
    s = pdstore.Store.open(tmp_path / "project", home=home)
    assert s.store_dir == tmp_path / "project" / ".prompt-debugger"
    assert (s.store_dir / ".gitignore").read_text(encoding="utf-8") == "*\n"
    assert (s.store_dir / "README.md").exists()


def test_project_scope_without_acknowledgement_fails_closed(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / "config.json").write_text(
        json.dumps({"config_version": 1, "storage_scope": "project"}), encoding="utf-8"
    )
    with pytest.raises(pdstore.StoreError, match="project_local_acknowledged"):
        pdstore.Store.open(tmp_path / "project", home=home)


def test_invalid_config_fails_closed(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / "config.json").write_text(
        json.dumps({"config_version": 1, "unknown_option": True}), encoding="utf-8"
    )
    with pytest.raises(pdstore.StoreValidationError):
        pdstore.Store.open(tmp_path / "project", home=home)


def test_symlinked_store_dir_is_refused(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "home" / "stores"
    link.parent.mkdir(parents=True)
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks not supported in this environment")
    # Opening resolves under home/stores/<key>; the parent symlink makes the
    # resolved store escape the home root -> PR-5 containment refusal.
    with pytest.raises(pdstore.StoreIntegrityError):
        pdstore.Store.open(tmp_path / "project", home=tmp_path / "home")


# --- append: pipeline, PR-1, PR-2, PR-3, refusals ---------------------------------------


def test_append_writes_one_valid_line(tmp_path: Path) -> None:
    s = _open(tmp_path)
    record = _append(s)
    lines = s.history_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == record
    assert re.match(r"^pd-[0-9]{10,17}-[0-9a-f]{8}$", record["id"])  # PR-2
    assert re.match(r"^[0-9a-f]{64}$", record["fingerprints"]["prompt"])  # PR-3
    assert record["raw"] is False and record["prompt_raw"] is None


def test_pr1_leak_payload_is_redacted_everywhere_via_real_write_path(tmp_path: Path) -> None:
    s = _open(tmp_path)
    record = s.append(prompt=LEAKY_PROMPT, report=_secret_report(), taxonomy_ids=TAXONOMY)
    blob = json.dumps(record)
    assert "sk-ABCDEFGHIJKLMNOP1234" not in blob
    assert "alice@example.com" not in blob
    assert record["prompt_raw"] is None
    # PR-1 substring consistency: redacted quote/segment remain substrings of
    # the redacted prompt.
    quote = record["report"]["findings"][0]["evidence"][0]["quote"]
    segment_text = record["report"]["ir"]["segments"][0]["text"]
    assert quote in record["prompt_redacted"]
    assert segment_text in record["prompt_redacted"]


def test_append_refuses_schema_invalid_report(tmp_path: Path) -> None:
    s = _open(tmp_path)
    bad = _report()
    del bad["knowledge"]
    with pytest.raises(pdstore.StoreValidationError):
        s.append(prompt=PROMPT, report=bad, taxonomy_ids=TAXONOMY)
    assert not s.history_path.exists()


def test_append_refuses_invariant_violating_report(tmp_path: Path) -> None:
    s = _open(tmp_path)
    bad = _report()
    bad["findings"][0]["evidence"][0]["quote"] = "not a substring of the prompt"
    with pytest.raises(pdstore.StoreValidationError, match="RPT-1"):
        s.append(prompt=PROMPT, report=bad, taxonomy_ids=TAXONOMY)
    assert not s.history_path.exists()


def test_raw_without_confirmation_is_rejected_and_writes_nothing(tmp_path: Path) -> None:
    s = _open(tmp_path)
    with pytest.raises(pdstore.RawConfirmationRequiredError):
        _append(s, raw=True)
    assert not s.history_path.exists()


def test_raw_with_confirmation_is_flagged_and_strip_raw_reverts(tmp_path: Path) -> None:
    s = _open(tmp_path)
    record = s.append(
        prompt=LEAKY_PROMPT,
        report=_secret_report(),
        taxonomy_ids=TAXONOMY,
        raw=True,
        confirm_raw=True,
    )
    assert record["raw"] is True and record["prompt_raw"] == LEAKY_PROMPT
    assert s.list_records()[0]["raw"] is True  # visibly flagged
    stripped = s.strip_raw(record["id"])
    assert stripped["raw"] is False and stripped["prompt_raw"] is None
    assert "sk-ABCDEFGHIJKLMNOP1234" not in json.dumps(stripped)
    # fingerprint recomputed over the redacted prompt
    assert stripped["fingerprints"]["prompt"] != record["fingerprints"]["prompt"]


def test_allow_raw_saves_false_refuses_outright(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / "config.json").write_text(
        json.dumps({"config_version": 1, "allow_raw_saves": False}), encoding="utf-8"
    )
    s = pdstore.Store.open(tmp_path / "project", home=home)
    with pytest.raises(pdstore.RawSavesDisabledError):
        _append(s, raw=True, confirm_raw=True)


def test_redaction_disabled_refuses_non_raw_saves(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / "config.json").write_text(
        json.dumps({"config_version": 1, "redaction_enabled": False}), encoding="utf-8"
    )
    s = pdstore.Store.open(tmp_path / "project", home=home)
    with pytest.raises(pdstore.StoreError, match="PR-1"):
        _append(s)
    # raw saves with per-save confirmation remain possible
    record = _append(s, raw=True, confirm_raw=True)
    assert record["raw"] is True


# --- ordering, locking, partial tail ----------------------------------------------------


def test_records_list_in_id_order(tmp_path: Path) -> None:
    s = _open(tmp_path)
    first = _append(s)
    second = _append(s)
    listed = [r["id"] for r in s.list_records()]
    assert listed == sorted(
        [first["id"], second["id"]], key=lambda rid: (int(rid.split("-")[1]), rid)
    )


def test_lock_contention_times_out_fail_closed(tmp_path: Path) -> None:
    s = _open(tmp_path)
    with s._lock(1.0), pytest.raises(pdstore.StoreLockedError):
        _append(s, lock_timeout=0.15)
    _append(s)  # lock released -> append succeeds
    assert len(s.list_records()) == 1


def test_partial_trailing_line_is_tolerated_and_doctor_reports_it(tmp_path: Path) -> None:
    s = _open(tmp_path)
    record = _append(s)
    with s.history_path.open("a", encoding="utf-8") as fh:
        fh.write('{"record_version": 1, "id": "pd-truncat')  # no newline: torn write
    assert [r["id"] for r in s.list_records()] == [record["id"]]  # tolerated (PR-4)
    result = s.doctor()
    assert result["valid"] == 1
    assert any("partial" in q["reason"] for q in result["quarantined"])
    assert s.rejects_path.exists()


def test_doctor_quarantines_invalid_lines_with_reasons(tmp_path: Path) -> None:
    s = _open(tmp_path)
    record = _append(s)
    with s.history_path.open("a", encoding="utf-8") as fh:
        fh.write("not-json at all\n")
        fh.write(json.dumps({"record_version": 1, "id": "pd-bad"}) + "\n")
    result = s.doctor()
    assert result["valid"] == 1
    reasons = " | ".join(q["reason"] for q in result["quarantined"])
    assert "invalid JSON" in reasons and "schema validation failed" in reasons
    # the file now holds only the valid record; a second doctor run is a no-op
    assert [r["id"] for r in s.list_records()] == [record["id"]]
    assert s.doctor()["quarantined"] == []


# --- migrate, archive, delete, purge ----------------------------------------------------


def test_migrate_backs_up_first_and_accepts_shipped_versions(tmp_path: Path) -> None:
    s = _open(tmp_path)
    _append(s)
    result = s.migrate()
    assert result["records"] == 1
    backup = Path(result["backup"])
    assert backup.exists()
    assert backup.read_bytes() == s.history_path.read_bytes()


def test_migrate_refuses_unknown_record_version(tmp_path: Path) -> None:
    s = _open(tmp_path)
    record = _append(s)
    mutated = dict(record)
    mutated["record_version"] = 99
    s.history_path.write_text(json.dumps(mutated) + "\n", encoding="utf-8")
    with pytest.raises(pdstore.StoreIntegrityError, match="record_version"):
        s.migrate()


def test_archive_rotates_history(tmp_path: Path) -> None:
    s = _open(tmp_path)
    _append(s)
    target = s.archive()
    assert target.parent == s.archive_dir and target.exists()
    assert s.list_records() == []


def test_delete_and_purge(tmp_path: Path) -> None:
    s = _open(tmp_path)
    a = _append(s)
    b = _append(s)
    s.delete(a["id"])
    assert [r["id"] for r in s.list_records()] == [b["id"]]
    with pytest.raises(pdstore.RecordNotFoundError):
        s.delete(a["id"])
    assert s.purge() == 1
    assert s.list_records() == []


# --- read paths: get/sanitize, compare, trends, export ----------------------------------


def test_get_sanitizes_on_read(tmp_path: Path) -> None:
    s = _open(tmp_path)
    record = _append(s)
    tampered = dict(record)
    tampered["prompt_redacted"] = record["prompt_redacted"] + "\x1b[31mred\x07"
    s.history_path.write_text(json.dumps(tampered, ensure_ascii=False) + "\n", encoding="utf-8")
    fetched = s.get(record["id"])
    assert "\x1b" not in fetched["prompt_redacted"] and "\x07" not in fetched["prompt_redacted"]


def test_get_unknown_id_raises(tmp_path: Path) -> None:
    s = _open(tmp_path)
    with pytest.raises(pdstore.RecordNotFoundError):
        s.get("pd-0000000000-00000000")


def test_compare_is_unified_diff_of_redacted_prompts_only(tmp_path: Path) -> None:
    s = _open(tmp_path)
    a = _append(s)
    report_b = _report()
    prompt_b = PROMPT + " Focus on invalidation."
    report_b["ir"]["segments"][0]["text"] = PROMPT
    report_b["findings"][0]["evidence"][0]["quote"] = PROMPT
    b = s.append(prompt=prompt_b, report=report_b, taxonomy_ids=TAXONOMY)
    diff = s.compare(a["id"], b["id"])
    assert f"--- {a['id']}" in diff and f"+++ {b['id']}" in diff
    assert "Focus on invalidation." in diff
    assert "score" not in diff.lower()  # no score, no substitute aggregate


def test_trends_counts_findings_per_dimension_in_order(tmp_path: Path) -> None:
    s = _open(tmp_path)
    first = _append(s)
    second = _append(s)
    trends = s.trends()
    assert [t["id"] for t in trends] == [r["id"] for r in s.list_records()]
    assert all(t["counts"] == {"R2": 1} for t in trends)
    assert {first["id"], second["id"]} == {t["id"] for t in trends}


def test_export_default_is_redacted_and_fingerprint_free(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = _open(tmp_path)
    s.append(
        prompt=LEAKY_PROMPT,
        report=_secret_report(),
        taxonomy_ids=TAXONOMY,
        raw=True,
        confirm_raw=True,
    )
    data = json.loads(s.export("json"))
    blob = json.dumps(data)
    assert "fingerprints" not in blob  # PR-3: excluded from default exports
    assert "sk-ABCDEFGHIJKLMNOP1234" not in blob  # raw content re-redacted by default
    assert data["records"][0]["prompt_raw"] is None
    assert data["provenance"]["records"] == 1  # FR-6: provenance header
    assert capsys.readouterr().err == ""  # no warning without the flag


def test_export_include_raw_requires_flag_and_warns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    s = _open(tmp_path)
    s.append(
        prompt=LEAKY_PROMPT,
        report=_secret_report(),
        taxonomy_ids=TAXONOMY,
        raw=True,
        confirm_raw=True,
    )
    exported = json.loads(s.export("json", include_raw=True))
    assert exported["records"][0]["prompt_raw"] == LEAKY_PROMPT
    assert "WARNING" in capsys.readouterr().err


def test_export_unsupported_format_is_refused(tmp_path: Path) -> None:
    s = _open(tmp_path)
    with pytest.raises(pdstore.UnsupportedExportFormatError, match="not supported"):
        s.export("html")


# --- review-fix regressions -------------------------------------------------------------


def _fragment_report() -> dict[str, Any]:
    """Schema- and invariant-valid against LEAKY_PROMPT, but the quote is a bare
    fragment of the secret (no ``sk-`` prefix): redaction replaces the prompt's
    full key while the fragment matches no pattern, so the quote is no longer a
    substring of the redacted prompt — PR-1 cannot survive redaction."""
    report = _report()
    report["ir"]["segments"] = [
        {"id": "s1", "kind": "task", "text": "deploy with key", "note": None}
    ]
    report["findings"][0]["evidence"] = [{"segment": "s1", "quote": "ABCDEFGHIJKLMNOP1234"}]
    report["findings"][0]["explanation"] = "quotes a bare fragment of the key"
    return report


def test_pr1_partial_secret_quote_fails_closed_post_redaction(tmp_path: Path) -> None:
    s = _open(tmp_path)
    with pytest.raises(pdstore.StoreValidationError, match="PR-1"):
        s.append(prompt=LEAKY_PROMPT, report=_fragment_report(), taxonomy_ids=TAXONOMY)
    assert not s.history_path.exists()  # fail closed: nothing written


def test_strip_raw_fails_closed_when_pr1_cannot_be_preserved(tmp_path: Path) -> None:
    s = _open(tmp_path)
    record = s.append(
        prompt=LEAKY_PROMPT,
        report=_fragment_report(),
        taxonomy_ids=TAXONOMY,
        raw=True,
        confirm_raw=True,
    )
    with pytest.raises(pdstore.StoreValidationError, match="PR-1"):
        s.strip_raw(record["id"])
    assert s.get(record["id"])["raw"] is True  # record left unchanged, still raw


def test_short_write_is_an_error_never_silent_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    s = _open(tmp_path)
    real_write = os.write

    def short_write(fd: int, data: bytes) -> int:
        return real_write(fd, data[: len(data) // 2])

    # store.py resolves os.write at call time on the shared module object, so
    # patching the os module intercepts the store's own append write.
    with monkeypatch.context() as m:
        m.setattr(os, "write", short_write)
        with pytest.raises(pdstore.StoreIntegrityError, match="doctor"):
            _append(s)
    # the torn half-line is on disk; doctor quarantines it and the store recovers
    result = s.doctor()
    assert result["valid"] == 0
    assert len(result["quarantined"]) == 1
    _append(s)
    assert len(s.list_records()) == 1


def test_append_refuses_symlinked_history_at_write_time(tmp_path: Path) -> None:
    s = _open(tmp_path)
    _append(s)
    outside = tmp_path / "outside.jsonl"
    outside.write_text("", encoding="utf-8")
    s.history_path.unlink()
    try:
        s.history_path.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks not supported in this environment")
    with pytest.raises(pdstore.StoreIntegrityError, match="symlink"):
        _append(s)
    assert outside.read_text(encoding="utf-8") == ""  # nothing escaped the store


def test_migrate_fails_closed_on_corrupt_history(tmp_path: Path) -> None:
    s = _open(tmp_path)
    _append(s)
    with s.history_path.open("a", encoding="utf-8") as fh:
        fh.write("corrupt {not json\n")
    with pytest.raises(pdstore.StoreIntegrityError, match="doctor"):
        s.migrate()
    assert not list(s.store_dir.glob("history.backup-*.jsonl"))  # no backup was made
    s.doctor()
    result = s.migrate()  # after quarantine, migration proceeds
    assert result["records"] == 1
    assert result["backup"] is not None and Path(result["backup"]).exists()


def test_read_paths_fail_closed_on_invalid_records(tmp_path: Path) -> None:
    s = _open(tmp_path)
    record = _append(s)
    with s.history_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"record_version": 1, "id": "pd-not-a-record"}) + "\n")
    for read in (
        s.list_records,
        s.trends,
        lambda: s.export("json"),
        lambda: s.get(record["id"]),
        lambda: s.compare(record["id"], record["id"]),
    ):
        with pytest.raises(pdstore.StoreIntegrityError, match="doctor"):
            read()
    s.doctor()
    assert [r["id"] for r in s.list_records()] == [record["id"]]


def test_doctor_quarantines_pr1_violating_redacted_records(tmp_path: Path) -> None:
    """A schema-valid raw:false record whose quotes break the post-redaction
    PR-1 substring relation is invalid content: doctor must quarantine it and
    never rewrite it back. PR-1 binds raw:false only — the raw record stays."""
    s = _open(tmp_path)
    raw_record = s.append(
        prompt=LEAKY_PROMPT,
        report=_fragment_report(),
        taxonomy_ids=TAXONOMY,
        raw=True,
        confirm_raw=True,
    )
    leaky = json.loads(s.history_path.read_text(encoding="utf-8").splitlines()[0])
    leaky["id"] = leaky["id"][:-8] + "deadbeef"  # distinct id, still schema-valid
    leaky["raw"] = False
    leaky["prompt_raw"] = None  # schema-valid raw:false shape, PR-1-violating content
    with s.history_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(leaky, ensure_ascii=False) + "\n")
    result = s.doctor()
    assert result["valid"] == 1  # the raw:true record is kept
    assert len(result["quarantined"]) == 1
    assert "PR-1" in result["quarantined"][0]["reason"]
    assert [r["id"] for r in s.list_records()] == [raw_record["id"]]
    assert leaky["id"] not in s.history_path.read_text(encoding="utf-8")


def test_doctor_quarantines_secret_surviving_outside_substring_fields(tmp_path: Path) -> None:
    """PR-1's pattern clause: the substring invariants can all hold while a
    recognized secret survives in a content-bearing field they do not govern
    (a finding explanation). A retained raw:false record must be a fixed point
    of the committed redactor; doctor quarantines it otherwise."""
    s = _open(tmp_path)
    record = _append(s)
    leaky = json.loads(s.history_path.read_text(encoding="utf-8").splitlines()[0])
    leaky["id"] = leaky["id"][:-8] + "deadbeef"  # distinct id, still schema-valid
    leaky["report"]["findings"][0]["explanation"] = "uses key sk-ABCDEFGHIJKLMNOP1234"
    with s.history_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(leaky, ensure_ascii=False) + "\n")
    result = s.doctor()
    assert result["valid"] == 1  # the properly redacted record is kept
    assert len(result["quarantined"]) == 1
    assert "PR-1" in result["quarantined"][0]["reason"]
    assert [r["id"] for r in s.list_records()] == [record["id"]]
    assert "sk-ABCDEFGHIJKLMNOP1234" not in s.history_path.read_text(encoding="utf-8")


def test_containment_is_validated_before_directory_creation(tmp_path: Path) -> None:
    """S4 symlink race: the escaping store path must be refused BEFORE mkdir —
    nothing may be created outside the store root."""
    outside = tmp_path / "outside"
    outside.mkdir()
    stores = tmp_path / "home" / "stores"
    stores.parent.mkdir(parents=True)
    try:
        stores.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks not supported in this environment")
    with pytest.raises(pdstore.StoreIntegrityError):
        pdstore.Store.open(tmp_path / "project", home=tmp_path / "home")
    assert list(outside.iterdir()) == []  # the mkdir never ran outside the root


def test_migrate_aborts_on_schema_invalid_records_before_backup(tmp_path: Path) -> None:
    s = _open(tmp_path)
    _append(s)
    with s.history_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"record_version": 1, "id": "pd-not-a-record"}) + "\n")
    with pytest.raises(pdstore.StoreIntegrityError, match="doctor"):
        s.migrate()
    assert not list(s.store_dir.glob("history.backup-*.jsonl"))  # no backup was made
    s.doctor()
    result = s.migrate()
    assert result["records"] == 1
    assert result["backup"] is not None and Path(result["backup"]).exists()


def test_concurrent_append_writers_serialize_under_the_lock(tmp_path: Path) -> None:
    """M2 test strategy: two writers under the lock; every line lands intact."""
    s = _open(tmp_path)

    def writer() -> None:
        w = pdstore.Store.open(tmp_path / "project", home=tmp_path / "home")
        for _ in range(5):
            w.append(prompt=PROMPT, report=_report(), taxonomy_ids=TAXONOMY, lock_timeout=30.0)

    threads = [threading.Thread(target=writer) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    records = s.list_records()  # validated read: every line parses and is schema-valid
    assert len(records) == 10
    assert len({r["id"] for r in records}) == 10
    assert s.doctor()["quarantined"] == []
