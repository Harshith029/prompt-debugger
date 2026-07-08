#!/usr/bin/env python3
"""Check that relative markdown links resolve to real files (stdlib only).

Scans markdown under docs/, core/, adapters/, benchmarks/, tools/, and the repo root.
Only relative links are checked; external (http/https/mailto) and pure in-page anchors
are ignored. A link with an #anchor is validated on the file part only.

Exit 0 if all relative links resolve, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCAN_DIRS = ["docs", "core", "adapters", "benchmarks", "tools"]
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
# Generated/vendored trees are marked with VENDORED.txt; we lint the source, not the copy.
VENDOR_MARKER = "VENDORED.txt"


def _is_vendored(path: Path) -> bool:
    for parent in path.parents:
        if (parent / VENDOR_MARKER).is_file():
            return True
        if parent == REPO:
            break
    return False


def _iter_markdown() -> list[Path]:
    files = list(REPO.glob("*.md"))
    for d in SCAN_DIRS:
        files.extend((REPO / d).rglob("*.md"))
    return sorted(p for p in files if not _is_vendored(p))


def _is_external(target: str) -> bool:
    return target.startswith(("http://", "https://", "mailto:", "#"))


def check_file(md: Path) -> list[str]:
    errors: list[str] = []
    text = md.read_text(encoding="utf-8")
    for match in LINK_RE.finditer(text):
        target = match.group(1).strip()
        if _is_external(target):
            continue
        file_part = target.split("#", 1)[0]
        if not file_part:
            continue  # pure anchor
        resolved = (md.parent / file_part).resolve()
        if not resolved.exists():
            errors.append(f"{md.relative_to(REPO)}: broken link -> {target}")
    return errors


def main() -> int:
    errors: list[str] = []
    for md in _iter_markdown():
        errors.extend(check_file(md))
    if errors:
        print("Link check FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("Link check passed (all relative markdown links resolve).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
