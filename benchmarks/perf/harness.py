#!/usr/bin/env python3
"""Storage performance harness (M2 FR-11).

Synthetic-store generators (10k / 100k records) and a timing harness for the
storage layer's O(n) JSONL scans. It provides the empirical basis for the
size-warning threshold (config ``size_warn_records``; open choice O6) so that
value is **measured, not guessed** (ARCHITECTURE §9). Stdlib only; it generates
synthetic records only, touches no real user store (everything runs under a
temporary directory), and performs no network I/O (ADR-0006).

Subcommands:
  validate   Smoke check for the CI matrix: generate a small store, run
             list/get/doctor, and assert they return correct results. No timing
             assertions, so it is deterministic across machines.
  measure    Generate stores at the given sizes and time the read-scan
             operations (list/get/trends — all share the ``_read_records`` O(n)
             validate-and-parse scan). Prints a results table; used to produce
             the recorded measurements in ``RESULTS.md`` and to derive the
             threshold. Not a pass/fail gate — timings are machine-dependent.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import statistics
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO / "src"))  # make the core library importable without install

from prompt_debugger.store import Store  # noqa: E402  (import follows the sys.path bootstrap)

_PROMPT = "Explain how our caching layer works."

# A minimal, composite-schema-valid, secret-free report that quotes _PROMPT, so a
# generated record is schema-valid and satisfies PR-1 (nothing to redact; the
# segment text and evidence quote are substrings of prompt_redacted == _PROMPT).
_REPORT: dict[str, Any] = {
    "report_version": 1,
    "created_at": "2026-07-07T12:00:00Z",
    "knowledge": {
        "knowledge_version": "2026.07-m2",
        "provider": "anthropic",
        "rubric_version": "2026.07-m2",
        "policy_version": "2026.07-m2",
    },
    "ir": {
        "ir_version": 1,
        "segments": [{"id": "s1", "kind": "task", "text": _PROMPT, "note": None}],
        "unsegmented_remainder": True,
    },
    "findings": [
        {
            "id": "f1",
            "dimension": "R2",
            "severity": "medium",
            "evidence": [{"segment": "s1", "quote": _PROMPT}],
            "explanation": "The task names no audience or purpose.",
            "fix": "Name who the explanation is for.",
        }
    ],
}


def _fingerprint(salt: bytes, text: str) -> str:
    return hmac.new(salt, text.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_store(home: Path, project: Path, n: int) -> Store:
    """Create a store holding ``n`` synthetic, schema- and PR-1-valid records.

    Records share one valid report and prompt (the scan cost is per-record
    regardless of content); ids are unique, pattern-valid, and time-ordered.
    History is written directly (not via ``append``) so 100k-record stores
    generate quickly; every record still passes ``doctor``."""
    store = Store.open(project, home=home)
    salt = (store.store_dir / "salt").read_bytes()
    fingerprint = _fingerprint(salt, _PROMPT)
    base = int(time.time() * 1000)
    lines = [
        json.dumps(
            {
                "record_version": 1,
                "id": f"pd-{base + i}-{i:08x}",
                "created_at": "2026-07-07T12:00:00+00:00",
                "raw": False,
                "fingerprints": {"alg": "hmac-sha256", "prompt": fingerprint, "rewrite": None},
                "prompt_redacted": _PROMPT,
                "prompt_raw": None,
                "parent_id": None,
                "report": _REPORT,
            },
            separators=(",", ":"),
        )
        for i in range(n)
    ]
    store.history_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return store


def _median_ms(fn: Callable[[], object], repeats: int) -> float:
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return round(statistics.median(samples), 3)


def _measure_size(n: int, repeats: int) -> dict[str, float]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        store = generate_store(root / "home", root / "project", n)
        summaries = store.list_records()  # setup (untimed): pick a real middle id
        mid_id = summaries[n // 2]["id"]
        return {
            "records": float(n),
            "list_ms": _median_ms(store.list_records, repeats),
            "get_ms": _median_ms(lambda: store.get(mid_id), repeats),
            "trends_ms": _median_ms(store.trends, repeats),
        }


def measure(sizes: list[int], repeats: int) -> int:
    print(f"{'records':>10}  {'list_ms':>10}  {'get_ms':>10}  {'trends_ms':>10}")
    for n in sizes:
        row = _measure_size(n, repeats)
        print(
            f"{int(row['records']):>10}  {row['list_ms']:>10}  "
            f"{row['get_ms']:>10}  {row['trends_ms']:>10}"
        )
    return 0


def validate() -> int:
    """CI-matrix smoke: the generator produces valid records the store reads back
    correctly. Correctness only — no timing bars (machine-independent)."""
    errors: list[str] = []
    n = 500
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        store = generate_store(root / "home", root / "project", n)
        summaries = store.list_records()
        if len(summaries) != n:
            errors.append(f"list returned {len(summaries)} records, expected {n}")
        if summaries:
            sample = summaries[n // 2]["id"]
            if store.get(sample)["id"] != sample:
                errors.append("get did not return the requested record")
        report = store.doctor()
        if report["valid"] != n or report["quarantined"]:
            errors.append(f"doctor found {report['valid']} valid, {report['quarantined']}")
    if errors:
        print("Perf harness validation FAILED:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"Perf harness validation passed (generated + scanned {n} records).")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Storage performance harness (M2 FR-11).")
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")
    sub.add_parser("validate", help="CI smoke: generate a small store and scan it")
    measure_p = sub.add_parser("measure", help="time read-scans at the given sizes")
    measure_p.add_argument("--sizes", default="10000,100000", help="comma-separated record counts")
    measure_p.add_argument("--repeats", type=int, default=5, help="timed repeats per operation")
    args = parser.parse_args(argv)
    if args.command == "validate":
        return validate()
    sizes = [int(s) for s in args.sizes.split(",") if s]
    return measure(sizes, args.repeats)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
