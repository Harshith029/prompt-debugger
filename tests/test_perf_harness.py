"""Perf-harness tests (M2 FR-11).

The timing harness itself is not a pass/fail gate (timings are machine-
dependent), but its generator and its ``validate`` smoke must be correct: the
synthetic records it produces are genuinely valid (they pass the real store's
schema + PR-1 checks via ``doctor``), and the store reads them back faithfully.
These tests lock that in; they use small stores so they stay fast.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from prompt_debugger import store as pdstore

REPO = Path(__file__).resolve().parent.parent
PERF = REPO / "benchmarks" / "perf" / "harness.py"


def _load_perf() -> Any:
    # The perf harness lives outside the package (benchmarks/), so it is loaded
    # from its file path; typed Any because it is a dynamically loaded module.
    spec = importlib.util.spec_from_file_location("perf_run", PERF)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


perf = _load_perf()


def test_generator_produces_valid_records(tmp_path: Path) -> None:
    store = perf.generate_store(tmp_path / "home", tmp_path / "project", 50)
    # The real store reads them back — list validates every record (S10 path).
    summaries = store.list_records()
    assert len(summaries) == 50
    assert all(s["raw"] is False for s in summaries)
    # doctor is the strict per-line schema + PR-1 check: nothing is quarantined.
    report = store.doctor()
    assert report["valid"] == 50 and report["quarantined"] == []


def test_generated_ids_are_unique_and_ordered(tmp_path: Path) -> None:
    store = perf.generate_store(tmp_path / "home", tmp_path / "project", 100)
    ids = [s["id"] for s in store.list_records()]
    assert len(set(ids)) == 100  # unique
    assert ids == sorted(ids, key=lambda r: (int(r.split("-")[1]), r))  # id order


def test_generated_records_are_fully_redacted(tmp_path: Path) -> None:
    # PR-1: a generated record must carry no raw prompt and be a fixed point of
    # redaction (the harness generates only benign, secret-free content).
    store = perf.generate_store(tmp_path / "home", tmp_path / "project", 10)
    record = store.get(store.list_records()[0]["id"])
    assert record["prompt_raw"] is None
    assert "sk-" not in str(record)  # no secret shapes in the synthetic content


def test_validate_smoke_passes() -> None:
    assert perf.validate() == 0


def test_measure_runs_on_small_sizes(capsys: pytest.CaptureFixture[str]) -> None:
    assert perf.measure([100, 200], repeats=1) == 0
    out = capsys.readouterr().out
    assert "records" in out and "list_ms" in out


def test_config_default_matches_measured_threshold() -> None:
    # FR-11 set the size-warning threshold from measurement; the runtime default
    # and the config schema default must agree on that measured value.
    schema = json.loads(
        (REPO / "core" / "contracts" / "storage" / "config.schema.json").read_text("utf-8")
    )
    schema_default = schema["properties"]["size_warn_records"]["default"]
    assert pdstore._CONFIG_DEFAULTS["size_warn_records"] == schema_default
