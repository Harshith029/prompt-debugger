#!/usr/bin/env python3
"""Fail if the vendored adapter core/ has drifted from repo-root core/ (ADR-0008).

Compares the file trees (excluding the generated VENDORED.txt stamp) by relative path
and content. Any missing, extra, or differing file is a failure; run
`python tools/sync_plugin.py` to regenerate.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "core"
VENDOR = REPO / "adapters" / "claude-code" / "core"
IGNORE = {"VENDORED.txt"}


def _rel_files(root: Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    if not root.is_dir():
        return out
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name not in IGNORE:
            out[str(path.relative_to(root)).replace("\\", "/")] = path.read_bytes()
    return out


def main() -> int:
    src = _rel_files(SOURCE)
    ven = _rel_files(VENDOR)
    errors: list[str] = []

    if not VENDOR.exists():
        errors.append("vendored core/ is missing; run: python tools/sync_plugin.py")
    else:
        for rel in sorted(set(src) - set(ven)):
            errors.append(f"missing in vendored copy: {rel}")
        for rel in sorted(set(ven) - set(src)):
            errors.append(f"unexpected extra file in vendored copy: {rel}")
        for rel in sorted(set(src) & set(ven)):
            if src[rel] != ven[rel]:
                errors.append(f"content drift: {rel}")

    if errors:
        print("Plugin sync check FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print("Fix: python tools/sync_plugin.py", file=sys.stderr)
        return 1
    print("Plugin sync check passed (vendored core/ matches repo-root core/).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
