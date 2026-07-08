#!/usr/bin/env python3
"""Vendor repo-root core/ into the Claude Code adapter (ADR-0008).

A Claude Code plugin is installed as a self-contained directory and cannot reach the
repository root, so it vendors a copy of core/ (contracts + knowledge). This script
regenerates that copy. The repo-root core/ is always the single source of truth;
tools/check_plugin_sync.py fails CI if the vendored copy drifts.

Usage: python tools/sync_plugin.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "core"
VENDOR = REPO / "adapters" / "claude-code" / "core"

STAMP = "GENERATED — do not edit. Synced from repo-root core/ by tools/sync_plugin.py.\n"


def sync() -> None:
    if VENDOR.exists():
        shutil.rmtree(VENDOR)
    shutil.copytree(SOURCE, VENDOR)
    (VENDOR / "VENDORED.txt").write_text(STAMP, encoding="utf-8")


def main() -> int:
    if not SOURCE.is_dir():
        print(f"source core/ not found at {SOURCE}", file=sys.stderr)
        return 1
    sync()
    print(f"Vendored core/ -> {VENDOR.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
