"""Command-line entry point (M2 FR-10).

An ``argparse`` entry point that wraps the frozen library modules — it is the
dispatch target the M4 ``history`` skill shim (``run.py``) will call
(ARCHITECTURE §4). This module adds no behavior of its own: it parses
arguments, reads inputs, dispatches to ``store`` (FR-5), ``verify`` (FR-2),
``render`` (FR-6), ``schema`` (FR-1), and ``knowledge`` (FR-7), and prints their
results. All validation, redaction, sanitization, privacy gating, and
fail-closed semantics live in those modules and are unchanged here.

Recorded implementation decision (spec open choice O10 — CLI command/flag
naming): subcommands are the **storage-contract operation names** exactly
(``append``, ``list``, ``get``, ``compare``, ``trends``, ``export``, ``delete``,
``purge``, ``strip-raw``, ``doctor``, ``migrate``, ``archive``), plus ``verify``
and ``render`` "where user-invocable" (FR-10). The ``history`` skill's own
user-facing verb ``save`` (ARCHITECTURE §4.1) is an M4 skill-level alias for the
contract's ``append`` and is not this layer's concern. Store commands take
``--home`` (default ``~/.prompt-debugger``, ADR-0004) and ``--project``
(default the working directory); ``append``/``verify`` take a report file and a
``--prompt-file`` (the reference prompt the report quotes), and load the
event-taxonomy id set (EV-2) from the report's declared provider via the FR-7
accessors.

Output shapes (also O10): structured results print as sanitized ``json.dumps``
(every dynamic string value passes through ``sanitize_text`` first, since
``ensure_ascii=False`` would otherwise emit C1 controls raw — S8); the CLI-owned
scalar lines (record ids, the archive path, status messages) are sanitized too;
the text-producing commands (``compare``, ``export``, ``render``) print the
frozen modules' already-sanitized output verbatim. Determinism: no wall-clock or
environment dependence in any output beyond values the data already carries.

Exit codes (fail-closed): ``0`` success; ``1`` any operation error (a specific
message on stderr) or a ``verify`` run that found violations; ``2`` argparse
usage errors. No network, no ``eval``/``exec``, stdlib only (ADR-0006).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .knowledge import KnowledgeError, load_pack
from .render import RenderError, render_report_markdown
from .sanitize import sanitize_text
from .schema import validate_report
from .store import Store, StoreError
from .verify import verify_report


class CliError(Exception):
    """A CLI-level input error (bad file content, undeterminable provider). Fail-closed."""


def _default_home() -> Path:
    # ADR-0004: default storage is user-local at ~/.prompt-debugger/.
    return Path.home() / ".prompt-debugger"


# --- input helpers ---------------------------------------------------------------------


def _read_report(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise CliError(f"report file {path} is not a JSON object")
    return data


def _taxonomy_ids(provider: str) -> set[str]:
    """The event-taxonomy id set for EV-2, from the report's declared provider
    (FR-7 accessor). Fail-closed: an unknown provider raises."""
    pack = load_pack(provider)
    return {entry["id"] for entry in pack["events"]["entries"]}


def _provider_of(report: dict[str, Any]) -> str:
    knowledge = report.get("knowledge")
    provider = knowledge.get("provider") if isinstance(knowledge, dict) else None
    if not isinstance(provider, str) or not provider:
        raise CliError("report has no knowledge.provider; cannot load its event taxonomy")
    return provider


def _open(args: argparse.Namespace) -> Store:
    home: Path = args.home
    project: Path = args.project
    return Store.open(project, home=home)


def _sanitize_json(value: Any) -> Any:
    """Apply sanitize_text (S8) to every string in a JSON-shaped value, preserving
    structure, key names, value types, and ordering. ``json.dumps(ensure_ascii=
    False)`` escapes only C0 controls (U+0000-U+001F); C1 controls (U+0080-U+009F,
    e.g. the 8-bit CSI introducer 0x9B) would otherwise reach stdout raw. This
    strips them from dynamic string values before emission — idempotent on content
    the frozen modules already sanitized (list/get/trends), so that is unchanged."""
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_json(item) for key, item in value.items()}
    return value


def _print_json(value: Any) -> None:
    print(json.dumps(_sanitize_json(value), ensure_ascii=False, indent=2))


def _print_error(exc: Exception) -> None:
    # Exception messages can echo dynamic content (a record id, a path, a file's
    # bytes). S8: any content the scripts print passes through the sanitizer, so
    # terminal control sequences cannot reach the terminal via a diagnostic.
    print(f"error: {sanitize_text(str(exc))}", file=sys.stderr)


def _print_line(text: str) -> None:
    # S8: CLI-owned scalar stdout the CLI formats itself — record ids, the
    # archive path (built from --home/--project), and constructed status
    # messages — passes through the sanitizer before printing. (Structured JSON
    # output is sanitized in _print_json; the frozen modules' own display output —
    # compare/export/render — is already sanitized and is not re-wrapped.)
    # sanitize_text is idempotent and preserves printable content, so valid
    # output is unchanged.
    print(sanitize_text(text))


def _warn(message: str) -> None:
    # Warnings/notes go to stderr so the command's stdout stays its data (e.g.
    # the JSON list); like every diagnostic they pass through the sanitizer (S8).
    print(sanitize_text(message), file=sys.stderr)


# --- command handlers ------------------------------------------------------------------


def _cmd_append(args: argparse.Namespace) -> int:
    report = _read_report(args.report)
    prompt = args.prompt_file.read_text(encoding="utf-8")
    taxonomy_ids = _taxonomy_ids(_provider_of(report))
    store = _open(args)
    record = store.append(
        prompt=prompt,
        report=report,
        taxonomy_ids=taxonomy_ids,
        parent_id=args.parent_id,
        raw=args.raw,
        confirm_raw=args.confirm_raw,
    )
    _print_line(record["id"])
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    store = _open(args)
    records = store.list_records()
    _print_json(records)
    # Documented max-size behavior (config size_warn_records; ARCHITECTURE §9):
    # on the full-history read, at or above the configured threshold, suggest
    # `archive`. To stderr, so the stdout JSON is unchanged; emitted once.
    threshold = int(store.config["size_warn_records"])
    if len(records) >= threshold:
        _warn(
            f"note: this store holds {len(records)} records, at or above the "
            f"size_warn_records threshold ({threshold}); run 'archive' to rotate "
            "older history out of the active file."
        )
    return 0


def _cmd_get(args: argparse.Namespace) -> int:
    _print_json(_open(args).get(args.id))
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    print(_open(args).compare(args.id_a, args.id_b), end="")
    return 0


def _cmd_trends(args: argparse.Namespace) -> int:
    _print_json(_open(args).trends())
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    print(_open(args).export(args.format, include_raw=args.include_raw), end="")
    return 0


def _cmd_delete(args: argparse.Namespace) -> int:
    _open(args).delete(args.id)
    _print_line(f"deleted {args.id}")
    return 0


def _cmd_purge(args: argparse.Namespace) -> int:
    count = _open(args).purge()
    _print_line(f"purged {count}")
    return 0


def _cmd_strip_raw(args: argparse.Namespace) -> int:
    record = _open(args).strip_raw(args.id)
    _print_line(record["id"])
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    _print_json(_open(args).doctor())
    return 0


def _cmd_migrate(args: argparse.Namespace) -> int:
    _print_json(_open(args).migrate())
    return 0


def _cmd_archive(args: argparse.Namespace) -> int:
    _print_line(str(_open(args).archive()))
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    report = _read_report(args.report)
    # Schema first (FR-1): verify assumes schema-valid input; a schema-invalid
    # report is reported and nothing is verified.
    schema_errors = validate_report(report)
    if schema_errors:
        _print_json({"schema_errors": schema_errors})
        return 1
    prompt = args.prompt_file.read_text(encoding="utf-8")
    taxonomy_ids = _taxonomy_ids(_provider_of(report))
    violations = verify_report(report, prompt, taxonomy_ids=taxonomy_ids)
    _print_json(
        [{"invariant": v.invariant, "path": v.path, "message": v.message} for v in violations]
    )
    return 1 if violations else 0


def _cmd_render(args: argparse.Namespace) -> int:
    print(render_report_markdown(_read_report(args.report)), end="")
    return 0


_HANDLERS = {
    "append": _cmd_append,
    "list": _cmd_list,
    "get": _cmd_get,
    "compare": _cmd_compare,
    "trends": _cmd_trends,
    "export": _cmd_export,
    "delete": _cmd_delete,
    "purge": _cmd_purge,
    "strip-raw": _cmd_strip_raw,
    "doctor": _cmd_doctor,
    "migrate": _cmd_migrate,
    "archive": _cmd_archive,
    "verify": _cmd_verify,
    "render": _cmd_render,
}


# --- parser ----------------------------------------------------------------------------


class _SanitizingParser(argparse.ArgumentParser):
    """S8 boundary for argparse's own diagnostics. argparse writes usage, help,
    and error text straight to a stream — before the CLI's runtime-exception
    boundary in ``main`` — so an unrecognized argument's control bytes would
    otherwise reach the terminal raw (the ``unrecognized arguments`` error
    formats the offending token with ``%s``, not ``%r``). Every message argparse
    emits passes through the one output chokepoint, ``_print_message``;
    sanitizing there covers usage, errors, and help on this parser and, via
    argparse's ``parser_class`` inheritance, its subparsers — preserving
    argparse's formatting, wording, and exit codes (only the bytes change)."""

    def _print_message(self, message: str, file: Any = None) -> None:
        # ``file`` is typed Any to avoid narrowing argparse's SupportsWrite[str]
        # (from _typeshed, not importable at runtime); it is passed through
        # unchanged. Only the message bytes are sanitized.
        super()._print_message(sanitize_text(message), file)


def _build_parser() -> argparse.ArgumentParser:
    parser = _SanitizingParser(
        prog="prompt-debugger",
        description="Prompt Debugger library CLI (M2). Wraps the storage, verify, and "
        "render operations; the M4 history skill dispatches to it.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")

    store_opts = _SanitizingParser(add_help=False)
    store_opts.add_argument(
        "--home",
        type=Path,
        default=_default_home(),
        help="storage home (default ~/.prompt-debugger)",
    )
    store_opts.add_argument(
        "--project", type=Path, default=Path.cwd(), help="project path (default: working dir)"
    )

    append_p = sub.add_parser("append", parents=[store_opts], help="validate, redact, and save")
    append_p.add_argument("--report", type=Path, required=True, help="Report JSON file")
    append_p.add_argument("--prompt-file", type=Path, required=True, help="reference prompt file")
    append_p.add_argument("--parent-id", default=None, help="previous revision's record id")
    append_p.add_argument(
        "--raw", action="store_true", help="store unredacted (needs --confirm-raw)"
    )
    append_p.add_argument(
        "--confirm-raw", action="store_true", help="explicit per-save confirmation for --raw"
    )

    sub.add_parser("list", parents=[store_opts], help="record summaries in id order")

    get_p = sub.add_parser("get", parents=[store_opts], help="one record")
    get_p.add_argument("id", help="record id")

    compare_p = sub.add_parser("compare", parents=[store_opts], help="unified diff of two records")
    compare_p.add_argument("id_a", help="first record id")
    compare_p.add_argument("id_b", help="second record id")

    sub.add_parser("trends", parents=[store_opts], help="per-dimension finding counts over time")

    export_p = sub.add_parser("export", parents=[store_opts], help="export records with provenance")
    export_p.add_argument("format", choices=("json", "markdown", "csv"), help="export format")
    export_p.add_argument(
        "--include-raw", action="store_true", help="include raw content (prints a warning)"
    )

    delete_p = sub.add_parser("delete", parents=[store_opts], help="delete one record")
    delete_p.add_argument("id", help="record id")

    sub.add_parser("purge", parents=[store_opts], help="destroy all records")

    strip_p = sub.add_parser("strip-raw", parents=[store_opts], help="make a raw record redacted")
    strip_p.add_argument("id", help="record id")

    sub.add_parser("doctor", parents=[store_opts], help="quarantine invalid/corrupt lines")
    sub.add_parser("migrate", parents=[store_opts], help="upgrade records (backup first)")
    sub.add_parser("archive", parents=[store_opts], help="rotate history into archive/")

    verify_p = sub.add_parser("verify", help="check a report's invariants against a prompt")
    verify_p.add_argument("--report", type=Path, required=True, help="Report JSON file")
    verify_p.add_argument("--prompt-file", type=Path, required=True, help="reference prompt file")

    render_p = sub.add_parser("render", help="render a Report JSON to Markdown")
    render_p.add_argument("--report", type=Path, required=True, help="Report JSON file")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = _HANDLERS[args.command]
    try:
        return handler(args)
    except (StoreError, RenderError, KnowledgeError, CliError) as exc:
        _print_error(exc)
        return 1
    except (OSError, json.JSONDecodeError) as exc:
        _print_error(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
