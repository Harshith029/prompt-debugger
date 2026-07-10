#!/usr/bin/env python3
"""Verify that every version-bearing file in the repository agrees (stdlib only).

Runs on every PR (not only at release) so version drift is caught early. It checks two
version families and their correspondence:

  Manifest family (release-tag spelling, e.g. "0.1.0-alpha"):
    - adapters/claude-code/.claude-plugin/plugin.json         -> version
    - adapters/claude-code/.claude-plugin/marketplace.json    -> plugins[].version
    - adapters/claude-code/adapter-manifest.json              -> adapter_version

  Python family (PEP 440 spelling, e.g. "0.1.0a0"):
    - pyproject.toml                                          -> version
    - src/prompt_debugger/__init__.py                        -> __version__

All manifest-family values must be identical. The two Python-family values must be
identical. The two families must correspond (same base release and same pre-release
kind). The CHANGELOG must carry a section heading for the manifest version.

Exit 0 on success, 1 on any mismatch.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent

_PEP440_RE = re.compile(r"^(?P<base>\d+\.\d+\.\d+)(?:(?P<kind>a|b|rc)(?P<num>\d+))?$")
_SEMVER_RE = re.compile(r"^(?P<base>\d+\.\d+\.\d+)(?:-(?P<pre>[0-9A-Za-z.-]+))?$")
_PRE_KIND = {"a": "alpha", "b": "beta", "rc": "rc"}


def _load_json(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _pyproject_version() -> str:
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    if not m:
        raise ValueError("could not find version in pyproject.toml")
    return m.group(1)


def _init_version() -> str:
    text = (REPO / "src" / "prompt_debugger" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not m:
        raise ValueError("could not find __version__ in __init__.py")
    return m.group(1)


def _normalize_pep440(v: str) -> tuple[str, str]:
    m = _PEP440_RE.match(v)
    if not m:
        raise ValueError(f"'{v}' is not a supported PEP 440 version")
    kind = m.group("kind")
    return m.group("base"), (_PRE_KIND[kind] if kind else "")


def _normalize_semver(v: str) -> tuple[str, str]:
    m = _SEMVER_RE.match(v)
    if not m:
        raise ValueError(f"'{v}' is not a supported semver version")
    pre = m.group("pre") or ""
    # Reduce a pre-release like "alpha" / "alpha.1" to its kind word.
    kind = pre.split(".")[0].split("-")[0] if pre else ""
    return m.group("base"), kind


def main() -> int:
    errors: list[str] = []

    plugin = _load_json(REPO / "adapters/claude-code/.claude-plugin/plugin.json")["version"]
    market_doc = _load_json(REPO / "adapters/claude-code/.claude-plugin/marketplace.json")
    market_versions = [p["version"] for p in market_doc["plugins"]]
    adapter = _load_json(REPO / "adapters/claude-code/adapter-manifest.json")["adapter_version"]

    manifest_values = {"plugin.json": plugin, "adapter-manifest.json": adapter}
    for i, mv in enumerate(market_versions):
        manifest_values[f"marketplace.json[{i}]"] = mv

    canonical = plugin
    for name, value in manifest_values.items():
        if value != canonical:
            errors.append(f"manifest version mismatch: {name}='{value}' != plugin='{canonical}'")

    py_proj = _pyproject_version()
    py_init = _init_version()
    if py_proj != py_init:
        errors.append(f"python version mismatch: pyproject='{py_proj}' != __init__='{py_init}'")

    # Cross-family correspondence.
    try:
        semver_base, semver_kind = _normalize_semver(canonical)
        pep_base, pep_kind = _normalize_pep440(py_proj)
        if semver_base != pep_base:
            errors.append(f"base version mismatch: manifest='{semver_base}' != python='{pep_base}'")
        if semver_kind != pep_kind:
            errors.append(
                f"pre-release kind mismatch: manifest='{semver_kind or 'final'}' "
                f"!= python='{pep_kind or 'final'}'"
            )
    except ValueError as exc:
        errors.append(str(exc))

    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## [{canonical}]" not in changelog:
        errors.append(f"CHANGELOG.md has no section heading '## [{canonical}]'")

    if errors:
        print("Version consistency check FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"Version consistency check passed (manifest={canonical}, python={py_proj}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
