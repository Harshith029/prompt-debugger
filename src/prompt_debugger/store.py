"""Storage layer (M2 FR-5).

Implements the Storage contract (``core/contracts/storage/CONTRACT.md``): the
on-disk layout, schema-validated config, and the operation set, composing the
frozen M2 modules — ``schema`` (FR-1) validates shapes, ``verify`` (FR-2)
enforces invariants, ``redact`` (FR-3) scrubs content, ``sanitize`` (FR-4)
cleans everything read back (records are untrusted input, threat S10).

Write path (``append``): verify invariants against the raw prompt → redact the
whole record unless the raw opt-in applies (invariant PR-1) → re-verify the
redaction-sensitive invariants against the redacted text (PR-1 must hold after
redaction, fail-closed) → build the envelope (PR-2 id, PR-3 fingerprints) →
composite schema validation (CV-2) → one serialized line written with a single
``os.write`` on an ``O_APPEND`` descriptor under the per-store advisory lock
(PR-4), verified complete by byte count. Path containment and symlink checks run
immediately before every filesystem write (PR-5), not only at open. Every
failure refuses the save with a specific error and never reports success.

Recorded implementation decisions (spec open choices):

- **O2 — project-key derivation:** ``project-key = <slug>-<hmac8>`` where the
  HMAC-SHA256 key is a user-level 32-byte ``user_salt`` file created at first
  use in the storage home (0600 where supported). The per-store ``salt`` cannot
  serve — it does not exist until the store does.
- **O3 — lock contention:** bounded wait (default 10 s, injectable), polling the
  advisory lock; on timeout :class:`StoreLockedError` is raised and nothing is
  written.
- **O4 — output shapes:** ``compare`` returns a ``difflib.unified_diff`` of the
  two records' ``prompt_redacted`` labeled with the record ids — nothing else
  (the spec's explicit scope decision: no score, no substitute aggregate).
  ``trends`` returns id-ordered ``{id, created_at, counts}`` with per-dimension
  finding counts.
- **Config interactions (fail-closed):** ``storage_scope: project`` without
  ``project_local_acknowledged: true`` is an error, never a silent fallback
  (ADR-0004). ``redaction_enabled: false`` refuses ``raw: false`` saves — a
  record marked redacted but containing unredacted content would violate PR-1 —
  while the per-save raw confirmation is never bypassed.
- **Exports:** redacted and fingerprint-free by default — fingerprints are
  stripped, ``prompt_raw`` omitted, and a raw record's content is passed through
  redaction so the PRIVACY.md default ("exports are redacted") holds for every
  record. ``include_raw=True`` (explicit flag) emits verbatim content and prints
  a warning to stderr. Formats are the storage contract's ``json``/``markdown``/
  ``csv``, formatted with provenance headers by the ``render`` module (FR-6);
  this layer prepares what may be exported, ``render`` only formats it. Any
  other format raises :class:`UnsupportedExportFormatError`.
"""

from __future__ import annotations

import difflib
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import time
import uuid
from collections.abc import Collection, Iterator
from contextlib import contextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import contracts_dir
from .redact import redact_report, redact_text
from .render import render_export
from .sanitize import sanitize_text
from .schema import validate, validate_history_record
from .verify import verify_ir, verify_report

_RECORD_ID = re.compile(r"^pd-[0-9]{10,17}-[0-9a-f]{8}$")
_SHIPPED_RECORD_VERSIONS = frozenset({1})

_PROJECT_LOCAL_README = (
    "# prompt-debugger store\n\n"
    "This directory holds saved prompt-analysis history for this project.\n"
    "It may contain redacted prompt text. It is self-ignoring (.gitignore with *)\n"
    "so it cannot be committed; do not remove that file. Manage contents with the\n"
    "history commands or delete this directory to destroy the data.\n"
)


class StoreError(Exception):
    """Base class for storage failures. Every failure is specific and fail-closed."""


class StoreValidationError(StoreError):
    """The payload failed schema validation or invariant verification; nothing was written."""

    def __init__(self, message: str, problems: list[str]) -> None:
        self.problems = problems
        super().__init__(message + ": " + "; ".join(problems))


class RawConfirmationRequiredError(StoreError):
    """A raw: true save was attempted without explicit per-save confirmation."""


class RawSavesDisabledError(StoreError):
    """Config allow_raw_saves=false refuses raw saves outright."""


class StoreLockedError(StoreError):
    """The per-store advisory lock could not be acquired within the timeout."""


class StoreIntegrityError(StoreError):
    """Symlinked/misplaced store paths, unreadable salt, or invalid stored records."""


class UnsupportedExportFormatError(StoreError):
    """The requested format is not one of the storage contract's export formats
    (csv/json/markdown)."""


class RecordNotFoundError(StoreError):
    """No record with the requested id exists in this store."""


# --- config ----------------------------------------------------------------------------

_CONFIG_DEFAULTS: dict[str, Any] = {
    "storage_scope": "user",
    "project_local_acknowledged": False,
    "allow_raw_saves": True,
    "redaction_enabled": True,
    # Measured in M2 FR-11 (was a guessed 50000); kept consistent with the config
    # schema default. See benchmarks/perf/RESULTS.md.
    "size_warn_records": 1000,
}


def load_config(home: Path, project_path: Path | None = None) -> dict[str, Any]:
    """Load and schema-validate ``config.json`` from the storage home, then apply
    the optional per-project override (``<project>/.prompt-debugger/config.json``).
    Missing files mean defaults; invalid files are a fail-closed error."""
    config: dict[str, Any] = {"config_version": 1, **_CONFIG_DEFAULTS}
    layers = [home / "config.json"]
    if project_path is not None:
        layers.append(project_path / ".prompt-debugger" / "config.json")
    schema = _config_schema()
    for layer in layers:
        if not layer.is_file():
            continue
        try:
            loaded = json.loads(layer.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise StoreIntegrityError(f"invalid config JSON at {layer}: {exc}") from exc
        errors = validate(loaded, schema)
        if errors:
            raise StoreValidationError(f"invalid config at {layer}", errors)
        config.update(loaded)
    return config


def _config_schema() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (contracts_dir() / "storage" / "config.schema.json").read_text(encoding="utf-8")
    )
    return data


# --- store opening ---------------------------------------------------------------------


def project_key(project_path: Path, user_salt: bytes) -> str:
    """``<slug>-<hmac8>``: stable per project, collision-safe, path not exposed."""
    resolved = str(project_path.resolve())
    slug = re.sub(r"[^a-z0-9]+", "-", project_path.name.lower()).strip("-") or "project"
    digest = hmac.new(user_salt, resolved.encode("utf-8"), hashlib.sha256).hexdigest()[:8]
    return f"{slug}-{digest}"


def _read_or_create_salt(path: Path, *, root: Path) -> bytes:
    if path.exists():
        if path.is_symlink():
            raise StoreIntegrityError(f"salt file must not be a symlink: {path}")
        salt = path.read_bytes()
        if len(salt) != 32:
            raise StoreIntegrityError(f"salt file corrupt (expected 32 bytes): {path}")
        return salt
    salt = secrets.token_bytes(32)
    _guard_write(root, path.parent)  # PR-5/S4: before the mkdir mutation
    path.parent.mkdir(parents=True, exist_ok=True)
    _guard_write(root, path)
    path.write_bytes(salt)
    with suppress(OSError):  # 0600 where supported; no-op semantics elsewhere
        path.chmod(0o600)
    return salt


class Store:
    """One project's history store. Open via :meth:`Store.open`."""

    def __init__(self, store_dir: Path, config: dict[str, Any], salt: bytes) -> None:
        self.store_dir = store_dir
        self.config = config
        self._salt = salt
        self.history_path = store_dir / "history.jsonl"
        self.rejects_path = store_dir / "history.rejects.jsonl"
        self.archive_dir = store_dir / "archive"
        self._lock_path = store_dir / ".lock"

    @classmethod
    def open(cls, project_path: Path, *, home: Path) -> Store:
        """Resolve config and store location, create the layout, and run the
        PR-5 path checks. Project-local scope requires the acknowledgement flag
        (ADR-0004) and creates the store self-ignoring."""
        config = load_config(home, project_path)
        if config["storage_scope"] == "project":
            if not config["project_local_acknowledged"]:
                raise StoreError(
                    "storage_scope=project requires project_local_acknowledged=true "
                    "(explicit opt-in, ADR-0004); refusing to guess"
                )
            store_dir = project_path / ".prompt-debugger"
            _check_paths(store_dir, project_path)  # PR-5/S4: before the mkdir mutation
            store_dir.mkdir(parents=True, exist_ok=True)
            gitignore = store_dir / ".gitignore"
            if not gitignore.exists():
                _guard_write(store_dir, gitignore)
                gitignore.write_text("*\n", encoding="utf-8")
            readme = store_dir / "README.md"
            if not readme.exists():
                _guard_write(store_dir, readme)
                readme.write_text(_PROJECT_LOCAL_README, encoding="utf-8")
            root = project_path
        else:
            user_salt = _read_or_create_salt(home / "user_salt", root=home)
            store_dir = home / "stores" / project_key(project_path, user_salt)
            _check_paths(store_dir, home)  # PR-5/S4: before the mkdir mutation
            store_dir.mkdir(parents=True, exist_ok=True)
            root = home
        _check_paths(store_dir, root)
        salt = _read_or_create_salt(store_dir / "salt", root=store_dir)
        return cls(store_dir, config, salt)

    # --- write path (PR-1..PR-4) -------------------------------------------------------

    def append(
        self,
        *,
        prompt: str,
        report: dict[str, Any],
        taxonomy_ids: Collection[str],
        parent_id: str | None = None,
        raw: bool = False,
        confirm_raw: bool = False,
        lock_timeout: float = 10.0,
    ) -> dict[str, Any]:
        """Validate → redact → fingerprint → atomically append one record.

        Refuses unvalidated payloads (schema or invariant failures), refuses
        ``raw=True`` without explicit per-save confirmation, and honors the
        config gates. On any refusal nothing is written.
        """
        if raw:
            if not self.config["allow_raw_saves"]:
                raise RawSavesDisabledError(
                    "raw saves are disabled by config (allow_raw_saves=false)"
                )
            if not confirm_raw:
                raise RawConfirmationRequiredError(
                    "raw=True requires explicit per-save confirmation (confirm_raw=True); "
                    "confirmation is never a persisted default"
                )
        elif not self.config["redaction_enabled"]:
            raise StoreError(
                "redaction_enabled=false cannot produce a raw:false record without "
                "violating PR-1; save raw with per-save confirmation or re-enable redaction"
            )

        violations = verify_report(report, prompt, taxonomy_ids=taxonomy_ids)
        if violations:
            raise StoreValidationError(
                "payload failed invariant verification",
                [f"{v.invariant} at {v.path}: {v.message}" for v in violations],
            )

        if raw:
            stored_prompt_redacted = redact_text(prompt)
            stored_report = report
            prompt_raw: str | None = prompt
            fingerprint_source = prompt
        else:
            stored_prompt_redacted = redact_text(prompt)
            stored_report = redact_report(report)
            prompt_raw = None
            fingerprint_source = stored_prompt_redacted
            # PR-1 must hold AFTER redaction too: quotes and segment text must be
            # verbatim substrings of prompt_redacted. Independent redaction can
            # break this (e.g. a quote that is a bare fragment of a secret matches
            # no pattern while the prompt's full secret is replaced). Fail closed.
            pr1 = _pr1_violations(stored_report, stored_prompt_redacted)
            if pr1:
                raise StoreValidationError(
                    "PR-1 cannot be preserved: content is not consistently redactable",
                    pr1,
                )

        rewrite_text = _rewrite_text(stored_report)
        record: dict[str, Any] = {
            "record_version": 1,
            "id": _new_record_id(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "raw": raw,
            "fingerprints": {
                "alg": "hmac-sha256",
                "prompt": self._fingerprint(fingerprint_source),
                "rewrite": self._fingerprint(rewrite_text) if rewrite_text else None,
            },
            "prompt_redacted": stored_prompt_redacted,
            "prompt_raw": prompt_raw,
            "parent_id": parent_id,
            "report": stored_report,
        }

        errors = validate_history_record(record)
        if errors:
            raise StoreValidationError("record failed composite schema validation", errors)

        data = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )
        with self._lock(lock_timeout):
            _guard_write(self.store_dir, self.history_path)
            fd = os.open(self.history_path, os.O_APPEND | os.O_CREAT | os.O_WRONLY)
            try:
                written = os.write(fd, data)  # PR-4: one write, O_APPEND
            finally:
                os.close(fd)
            if written != len(data):
                # The record was NOT saved; a torn partial line may remain on
                # disk. Never report success — doctor quarantines the tail.
                raise StoreIntegrityError(
                    f"incomplete write to history.jsonl ({written} of {len(data)} bytes); "
                    "the record was not saved — run doctor to quarantine the torn line"
                )
        return record

    def _fingerprint(self, text: str) -> str:
        return hmac.new(self._salt, text.encode("utf-8"), hashlib.sha256).hexdigest()

    # --- read paths (S10: validate + sanitize; tolerate partial tail) ------------------

    def list_records(self) -> list[dict[str, Any]]:
        """The storage contract's `list` operation: record summaries in id
        order; raw records visibly flagged. (Named list_records so the method
        does not shadow the builtin `list` in annotations.)"""
        records, _ = self._read_records()
        return [
            {
                "id": r["id"],
                "created_at": sanitize_text(str(r.get("created_at", ""))),
                "raw": bool(r.get("raw", False)),
                "parent_id": r.get("parent_id"),
            }
            for r in records
        ]

    def get(self, record_id: str) -> dict[str, Any]:
        """One record, schema-validated and sanitized before display."""
        record = self._find(record_id)
        errors = validate_history_record(record)
        if errors:
            raise StoreIntegrityError(
                f"stored record {record_id} is invalid (run doctor): " + "; ".join(errors)
            )
        sanitized: dict[str, Any] = _sanitize_tree(record)
        return sanitized

    def compare(self, id_a: str, id_b: str) -> str:
        """Unified diff of the two records' redacted prompts — nothing else
        (spec scope decision: no score, no substitute aggregate)."""
        a, b = self._find(id_a), self._find(id_b)
        diff = difflib.unified_diff(
            sanitize_text(a["prompt_redacted"]).splitlines(keepends=True),
            sanitize_text(b["prompt_redacted"]).splitlines(keepends=True),
            fromfile=id_a,
            tofile=id_b,
        )
        return "".join(diff)

    def trends(self) -> list[dict[str, Any]]:
        """Per-dimension finding counts over time, in id order."""
        records, _ = self._read_records()
        out: list[dict[str, Any]] = []
        for r in records:
            counts: dict[str, int] = {}
            for finding in r.get("report", {}).get("findings", []):
                dimension = finding.get("dimension")
                if isinstance(dimension, str):
                    counts[dimension] = counts.get(dimension, 0) + 1
            out.append(
                {
                    "id": r["id"],
                    "created_at": sanitize_text(str(r.get("created_at", ""))),
                    "counts": dict(sorted(counts.items())),
                }
            )
        return out

    def export(self, fmt: str = "json", *, include_raw: bool = False) -> str:
        """Redacted and fingerprint-free by default; raw content only with the
        explicit flag, which prints a warning. Formats per the storage contract
        (json/markdown/csv), rendered with provenance headers by render (FR-6);
        this layer stays the only preparer of what may be exported."""
        if fmt not in ("csv", "json", "markdown"):
            raise UnsupportedExportFormatError(
                f"export format '{fmt}' is not supported; available: csv, json, markdown"
            )
        if include_raw:
            print(
                "WARNING: export includes raw (unredacted) content.",
                file=sys.stderr,
            )
        records, _ = self._read_records()
        exported: list[dict[str, Any]] = []
        for r in records:
            entry = dict(r)
            entry.pop("fingerprints", None)  # PR-3: excluded from default exports
            if not include_raw:
                entry["prompt_raw"] = None
                if entry.get("raw"):
                    # A raw record's content is unredacted; the default export
                    # re-redacts so "exports are redacted by default" holds.
                    entry["prompt_redacted"] = redact_text(entry["prompt_redacted"])
                    entry["report"] = redact_report(entry["report"])
            exported.append(_sanitize_tree(entry))
        return render_export(fmt, exported, include_raw=include_raw)

    # --- lifecycle operations ----------------------------------------------------------

    def delete(self, record_id: str, *, lock_timeout: float = 10.0) -> None:
        self._find(record_id)  # RecordNotFoundError if absent
        with self._lock(lock_timeout):
            records, _ = self._read_records()
            self._rewrite([r for r in records if r["id"] != record_id])

    def purge(self, *, lock_timeout: float = 10.0) -> int:
        """Destroy all records. Deliberately does not require valid content:
        user-owned data must be destroyable even when the history is corrupt."""
        with self._lock(lock_timeout):
            count = sum(1 for _, _, complete in self._read_lines() if complete)
            self._rewrite([])
        return count

    def strip_raw(self, record_id: str, *, lock_timeout: float = 10.0) -> dict[str, Any]:
        """Convert a raw record to redacted in place (reversibility of the raw opt-in)."""
        with self._lock(lock_timeout):
            records, _ = self._read_records()
            updated: dict[str, Any] | None = None
            for r in records:
                if r["id"] == record_id:
                    r["raw"] = False
                    r["prompt_raw"] = None
                    r["prompt_redacted"] = redact_text(r["prompt_redacted"])
                    r["report"] = redact_report(r["report"])
                    # PR-1 must hold after re-redaction; if the raw content cannot
                    # be consistently redacted, fail closed and leave the record
                    # unchanged rather than persist a PR-1-violating one.
                    pr1 = _pr1_violations(r["report"], r["prompt_redacted"])
                    if pr1:
                        raise StoreValidationError(
                            f"strip-raw of {record_id} would violate PR-1", pr1
                        )
                    r["fingerprints"]["prompt"] = self._fingerprint(r["prompt_redacted"])
                    rewrite_text = _rewrite_text(r["report"])
                    r["fingerprints"]["rewrite"] = (
                        self._fingerprint(rewrite_text) if rewrite_text else None
                    )
                    updated = r
            if updated is None:
                raise RecordNotFoundError(f"no record '{record_id}' in this store")
            self._rewrite(records)
        return updated

    def doctor(self, *, lock_timeout: float = 10.0) -> dict[str, Any]:
        """Validate every line; quarantine invalid/corrupt lines (including a
        trailing partial line) to history.rejects.jsonl with reasons. A
        schema-valid ``raw: false`` record that violates PR-1 post-redaction is
        invalid content and is quarantined, never rewritten back into history."""
        with self._lock(lock_timeout):
            raw_lines = self._read_lines()
            kept: list[dict[str, Any]] = []
            quarantined: list[dict[str, Any]] = []
            for line_no, line, complete in raw_lines:
                reason: str | None = None
                record: dict[str, Any] | None = None
                if not complete:
                    reason = "trailing partial line (incomplete write)"
                else:
                    try:
                        parsed = json.loads(line)
                        record = parsed if isinstance(parsed, dict) else None
                        if record is None:
                            reason = "line is not a JSON object"
                    except json.JSONDecodeError as exc:
                        reason = f"invalid JSON: {exc}"
                if record is not None and reason is None:
                    errors = validate_history_record(record)
                    if errors:
                        reason = "schema validation failed: " + "; ".join(errors[:3])
                if record is not None and reason is None and not record["raw"]:
                    pr1 = _pr1_violations(record["report"], record["prompt_redacted"])
                    pr1 += _pr1_unredacted_fields(record)
                    if pr1:
                        reason = "PR-1 violation (raw:false record): " + "; ".join(pr1[:3])
                if reason is None and record is not None:
                    kept.append(record)
                else:
                    quarantined.append({"line": line_no, "reason": reason, "content": line})
            if quarantined:
                _guard_write(self.store_dir, self.rejects_path)
                with self.rejects_path.open("a", encoding="utf-8") as fh:
                    for q in quarantined:
                        fh.write(json.dumps(q, ensure_ascii=False) + "\n")
                self._rewrite(kept)
        return {
            "valid": len(kept),
            "quarantined": [{"line": q["line"], "reason": q["reason"]} for q in quarantined],
        }

    def migrate(self, *, lock_timeout: float = 10.0) -> dict[str, Any]:
        """Upgrade records to the current record_version; timestamped backup first.
        PR-6: every version ever shipped ({1}) is accepted; an unknown version is
        a fail-closed error. Corrupt history is never migrated: torn,
        unparseable, or schema-invalid lines abort — before any backup is
        written — with direction to run doctor first."""
        with self._lock(lock_timeout):
            records: list[dict[str, Any]] = []
            for line_no, line, complete in self._read_lines():
                if not complete:
                    raise StoreIntegrityError(
                        f"history line {line_no} is a torn partial line; "
                        "run doctor before migrating"
                    )
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise StoreIntegrityError(
                        f"history line {line_no} is corrupt ({exc}); run doctor before migrating"
                    ) from exc
                if not isinstance(parsed, dict):
                    raise StoreIntegrityError(
                        f"history line {line_no} is not a JSON object; run doctor before migrating"
                    )
                records.append(parsed)
            for r in records:
                version = r.get("record_version")
                if version not in _SHIPPED_RECORD_VERSIONS:
                    raise StoreIntegrityError(
                        f"record {r.get('id')} has unknown record_version {version!r}; "
                        f"shipped versions: {sorted(_SHIPPED_RECORD_VERSIONS)}"
                    )
                errors = validate_history_record(r)
                if errors:
                    raise StoreIntegrityError(
                        f"record {r.get('id')} fails schema validation ("
                        + "; ".join(errors[:3])
                        + "); run doctor before migrating"
                    )
            backup: Path | None = None
            if self.history_path.exists():
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
                backup = self.store_dir / f"history.backup-{stamp}.jsonl"
                _guard_write(self.store_dir, backup)
                backup.write_bytes(self.history_path.read_bytes())
            # record_version 1 is current; no transformation is required.
        return {"backup": str(backup) if backup else None, "records": len(records)}

    def archive(self, *, lock_timeout: float = 10.0) -> Path:
        """Rotate history.jsonl into archive/history-<date>.jsonl."""
        with self._lock(lock_timeout):
            _guard_write(self.store_dir, self.archive_dir)
            self.archive_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
            target = self.archive_dir / f"history-{stamp}.jsonl"
            counter = 1
            while target.exists():
                counter += 1
                target = self.archive_dir / f"history-{stamp}-{counter}.jsonl"
            _guard_write(self.store_dir, target)
            if self.history_path.exists():
                self.history_path.replace(target)
            else:
                target.write_text("", encoding="utf-8")
        return target

    # --- internals ---------------------------------------------------------------------

    def _find(self, record_id: str) -> dict[str, Any]:
        records, _ = self._read_records()
        for r in records:
            if r.get("id") == record_id:
                return r
        raise RecordNotFoundError(f"no record '{record_id}' in this store")

    def _read_lines(self) -> list[tuple[int, str, bool]]:
        """(line_no, text, complete) triples; the final segment is incomplete when
        the file does not end with a newline (PR-4: tolerate and report)."""
        if not self.history_path.exists():
            return []
        if self.history_path.is_symlink():
            raise StoreIntegrityError(
                f"history.jsonl must not be a symlink (PR-5): {self.history_path}"
            )
        data = self.history_path.read_text(encoding="utf-8")
        if data == "":
            return []
        complete_all = data.endswith("\n")
        segments = data.split("\n")
        if segments and segments[-1] == "":
            segments.pop()
        out: list[tuple[int, str, bool]] = []
        for i, segment in enumerate(segments):
            is_last = i == len(segments) - 1
            out.append((i + 1, segment, complete_all or not is_last))
        return out

    def _read_records(self) -> tuple[list[dict[str, Any]], list[str]]:
        """Fail-closed read (S10): every complete line must parse and pass
        composite schema validation before records are exposed to any read path;
        a trailing partial line is tolerated and reported (PR-4). Recovery is
        doctor's job, not the readers' — invalid content is a hard error."""
        records: list[dict[str, Any]] = []
        issues: list[str] = []
        for line_no, line, complete in self._read_lines():
            if not complete:
                issues.append(f"line {line_no}: trailing partial line (tolerated)")
                continue
            problem: str | None = None
            parsed: Any = None
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                problem = "invalid JSON"
            if problem is None and not isinstance(parsed, dict):
                problem = "not a JSON object"
            if problem is None:
                errors = validate_history_record(parsed)
                if errors:
                    problem = "schema validation failed: " + "; ".join(errors[:3])
            if problem is not None:
                raise StoreIntegrityError(
                    f"history line {line_no} is invalid ({problem}); run doctor to quarantine it"
                )
            records.append(parsed)
        records.sort(key=_record_order)
        return records, issues

    def _rewrite(self, records: list[dict[str, Any]]) -> None:
        """Atomic full-file rewrite: temp file in the store dir, then os.replace."""
        tmp = self.store_dir / "history.jsonl.tmp"
        _guard_write(self.store_dir, tmp)
        with tmp.open("w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
        _guard_write(self.store_dir, self.history_path)
        tmp.replace(self.history_path)

    @contextmanager
    def _lock(self, timeout: float) -> Iterator[None]:
        _guard_write(self.store_dir, self._lock_path)
        fd = os.open(self._lock_path, os.O_CREAT | os.O_RDWR)
        deadline = time.monotonic() + timeout
        try:
            while True:
                try:
                    _try_lock(fd)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise StoreLockedError(
                            f"could not acquire the store lock within {timeout} s"
                        ) from None
                    time.sleep(0.05)
            try:
                yield
            finally:
                _try_unlock(fd)
        finally:
            os.close(fd)


def _try_lock(fd: int) -> None:
    # Advisory lock shim per the storage contract; the two platform modules are
    # never both imported (guarded by sys.platform — import-policy requirement).
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _try_unlock(fd: int) -> None:
    if sys.platform == "win32":
        import msvcrt

        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)


def _check_paths(store_dir: Path, root: Path) -> None:
    """PR-5 / S4: no symlinked store paths; containment within the store root."""
    if store_dir.is_symlink():
        raise StoreIntegrityError(f"store directory must not be a symlink: {store_dir}")
    history = store_dir / "history.jsonl"
    if history.is_symlink():
        raise StoreIntegrityError(f"history.jsonl must not be a symlink: {history}")
    resolved = store_dir.resolve()
    root_resolved = root.resolve()
    if root_resolved not in resolved.parents and resolved != root_resolved:
        raise StoreIntegrityError(f"store directory {resolved} escapes its root {root_resolved}")


def _guard_write(store_dir: Path, target: Path) -> None:
    """PR-5 / S4, immediately before every filesystem write: neither the store
    directory nor the write target may be a symlink, and the resolved target must
    stay inside the resolved store directory. The checks at open() do not protect
    against paths swapped for symlinks after the store was opened."""
    if store_dir.is_symlink():
        raise StoreIntegrityError(f"store directory must not be a symlink: {store_dir}")
    if target.is_symlink():
        raise StoreIntegrityError(f"write target must not be a symlink (PR-5): {target}")
    resolved = target.resolve()
    root = store_dir.resolve()
    if resolved != root and root not in resolved.parents:
        raise StoreIntegrityError(f"write target {resolved} escapes the store {root}")


def _pr1_violations(report: dict[str, Any], prompt_redacted: str) -> list[str]:
    """The redaction-sensitive slice of PR-1: after redaction, IR segment text
    (IR-1) and evidence quotes (RPT-1) must still be verbatim substrings of
    ``prompt_redacted``. Structural invariants (ids, gates, taxonomy references)
    are unaffected by text redaction and were verified pre-redaction."""
    ir = report.get("ir")
    problems = [
        f"{v.invariant} at $.ir{v.path[1:]}: {v.message} after redaction"
        for v in verify_ir(ir if isinstance(ir, dict) else {}, prompt_redacted)
        if v.invariant == "IR-1"
    ]
    for i, finding in enumerate(report.get("findings", [])):
        for j, evidence in enumerate(finding.get("evidence", [])):
            quote = evidence.get("quote")
            if isinstance(quote, str) and quote not in prompt_redacted:
                problems.append(
                    f"RPT-1 at $.findings[{i}].evidence[{j}].quote: evidence quote "
                    "is not a verbatim substring of the redacted prompt"
                )
    return problems


def _pr1_unredacted_fields(record: dict[str, Any]) -> list[str]:
    """PR-1's pattern clause for a stored ``raw: false`` record: ``prompt_raw``
    is null and no recognized secret/PII pattern survives in any field,
    including every content-bearing field of the embedded report. The committed
    redactor (FR-3) is idempotent, so a valid record's content is a fixed point
    of it — if redacting would change a field, a recognized pattern survived
    there (e.g. a secret in a finding explanation, which no substring invariant
    governs)."""
    problems: list[str] = []
    if record["prompt_raw"] is not None:
        problems.append("$.prompt_raw must be null in a raw:false record")
    if redact_text(record["prompt_redacted"]) != record["prompt_redacted"]:
        problems.append("$.prompt_redacted retains a recognized secret/PII pattern")
    if redact_report(record["report"]) != record["report"]:
        problems.append(
            "$.report retains a recognized secret/PII pattern in a content-bearing field"
        )
    return problems


def _new_record_id() -> str:
    return f"pd-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"


def _record_order(record: dict[str, Any]) -> tuple[int, str]:
    rid = str(record.get("id", ""))
    if _RECORD_ID.match(rid):
        _, epoch, suffix = rid.split("-")
        return (int(epoch), suffix)
    return (0, rid)


def _rewrite_text(report: dict[str, Any]) -> str | None:
    rewrite = report.get("rewrite")
    if isinstance(rewrite, dict):
        text = rewrite.get("text")
        if isinstance(text, str):
            return text
    return None


def _sanitize_tree(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [_sanitize_tree(v) for v in value]
    if isinstance(value, dict):
        return {k: _sanitize_tree(v) for k, v in value.items()}
    return value
