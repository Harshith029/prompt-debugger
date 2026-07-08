#!/usr/bin/env python3
"""Enforce the runtime import policy for src/prompt_debugger/ (ADR-0006).

The shipped library must be standard-library only and must never perform runtime
network I/O. This AST check walks every module under src/prompt_debugger/ and fails
if it imports anything outside the standard library or on the network/dynamic-exec
denylist. Test and tooling code is intentionally out of scope.

No third-party dependency: the allowlist is the set of top-level stdlib module names
for the supported Python versions, plus first-party 'prompt_debugger'.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src" / "prompt_debugger"

# Modules that must never appear in shipped runtime code.
DENYLIST: frozenset[str] = frozenset(
    {
        "socket",
        "ssl",
        "http",
        "urllib",
        "urllib2",
        "ftplib",
        "smtplib",
        "telnetlib",
        "asyncio",
        "requests",
        "httpx",
        "aiohttp",
        "subprocess",
        "ctypes",
    }
)

# First-party and a conservative allowlist of stdlib top-level modules the library
# is expected to use. Anything not here and not obviously stdlib fails closed.
FIRST_PARTY: frozenset[str] = frozenset({"prompt_debugger"})

STDLIB_ALLOW: frozenset[str] = frozenset(
    {
        "__future__",
        "argparse",
        "base64",
        "collections",
        "contextlib",
        "dataclasses",
        "datetime",
        "difflib",
        "enum",
        "errno",
        "fnmatch",
        "functools",
        "hashlib",
        "hmac",
        "io",
        "itertools",
        "json",
        "logging",
        "math",
        "os",
        "pathlib",
        "re",
        "secrets",
        "shutil",
        "stat",
        "string",
        "sys",
        "tempfile",
        "textwrap",
        "time",
        "typing",
        "unicodedata",
        "uuid",
        "csv",
    }
)

# Platform-locking modules used by the storage layer; allowed but never both imported
# unconditionally (M2 storage guards them behind sys.platform).
PLATFORM_ALLOW: frozenset[str] = frozenset({"fcntl", "msvcrt"})


def _top(name: str) -> str:
    return name.split(".", 1)[0]


def check_module(path: Path) -> list[str]:
    errors: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [_top(alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative first-party import
            if node.module:
                names = [_top(node.module)]
        for name in names:
            if name in DENYLIST:
                errors.append(f"{path.relative_to(REPO)}: denylisted import '{name}'")
            elif name in FIRST_PARTY or name in STDLIB_ALLOW or name in PLATFORM_ALLOW:
                continue
            else:
                errors.append(
                    f"{path.relative_to(REPO)}: import '{name}' not in the stdlib allowlist "
                    f"(runtime is stdlib-only; add to STDLIB_ALLOW if it is genuinely stdlib)"
                )
    return errors


def main() -> int:
    if not SRC.exists():
        print(f"source dir not found: {SRC}", file=sys.stderr)
        return 1
    errors: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        errors.extend(check_module(path))
    if errors:
        print("Import policy check FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("Import policy check passed (stdlib-only, no runtime network/exec modules).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
