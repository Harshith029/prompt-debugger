#!/usr/bin/env python3
"""Launcher shim for the history skill.

Locates the prompt-debugger core library and dispatches to its CLI. The library
lives under the plugin's vendored `core/`-adjacent source at install time, or under
the repo `src/` in a development checkout. This shim keeps the skill launcher-agnostic
(python3 / python / py -3 are all pre-approved in the skill frontmatter).

Milestone M0: the shim resolves the library path and reports that the CLI is not yet
implemented. The storage CLI (prompt_debugger.cli) lands in Milestone M2; at that
point this shim simply forwards argv to it.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _candidate_src_dirs() -> list[Path]:
    here = Path(__file__).resolve()
    candidates: list[Path] = []
    # Development checkout: adapters/claude-code/skills/history/scripts/run.py
    # -> repo root is five parents up; src/ holds the library.
    for parent in here.parents:
        src = parent / "src"
        if (src / "prompt_debugger" / "__init__.py").is_file():
            candidates.append(src)
        # Vendored layout: a sibling `lib/` or bundled package may be added in M2.
    return candidates


def main(argv: list[str]) -> int:
    for src in _candidate_src_dirs():
        sys.path.insert(0, str(src))
    try:
        import prompt_debugger  # noqa: F401
    except ImportError:
        sys.stderr.write(
            "prompt-debugger core library not found on path. "
            "In a development checkout, run from the repository so `src/` is discoverable.\n"
        )
        return 2

    # M2: replace this block with `from prompt_debugger.cli import main as cli_main;
    # return cli_main(argv)`.
    sys.stderr.write(
        f"history CLI is not implemented yet (arrives in Milestone M2). Received args: {argv!r}\n"
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
