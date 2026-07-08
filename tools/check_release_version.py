#!/usr/bin/env python3
"""Verify that a release tag matches the versions declared in the repository.

Checks the git tag (e.g. v0.1.0) against:
  - the plugin manifest version (adapters/claude-code/.claude-plugin/plugin.json)
  - the marketplace manifest version

pyproject uses PEP 440 versions (e.g. 0.1.0a0 for the 0.1.0-alpha tag), which differ in
spelling from the git tag, so pyproject is not compared here. The plugin and marketplace
manifests must match the tag exactly. Fails (exit 1) on any mismatch so a tag can never
ship inconsistent version metadata.

Usage: python tools/check_release_version.py v0.1.0
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "adapters" / "claude-code" / ".claude-plugin" / "plugin.json"
MARKET = REPO / "adapters" / "claude-code" / ".claude-plugin" / "marketplace.json"


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: check_release_version.py <tag>", file=sys.stderr)
        return 2
    tag = argv[0].lstrip("v").strip()

    errors: list[str] = []

    plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))
    plugin_ver = str(plugin.get("version", "")).lstrip("v")
    if plugin_ver != tag:
        errors.append(f"plugin.json version '{plugin_ver}' != tag '{tag}'")

    market = json.loads(MARKET.read_text(encoding="utf-8"))
    for entry in market.get("plugins", []):
        entry_ver = str(entry.get("version", "")).lstrip("v")
        if entry_ver != tag:
            name = entry.get("name")
            errors.append(f"marketplace plugin '{name}' version '{entry_ver}' != tag '{tag}'")

    if errors:
        print("Release version check FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"Release version check passed for tag '{tag}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
