"""Repository path resolution — the one place that knows the layout.

Host-neutral: no adapter, no OS assumptions beyond pathlib. Locates the
versioned `core/` tree (contracts + knowledge) relative to the installed
package so tools, tests, and future library code find contracts the same way.

At M0 this is deliberately the only executable logic in the package: it lets
CI and tests resolve `core/` without hardcoding absolute paths, and it is
covered by tests/test_paths.py.
"""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Return the repository root (the directory containing `core/`).

    Resolution walks upward from this file until a directory containing a
    `core/contracts` subtree is found. Falls back to the three-levels-up layout
    (src/prompt_debugger/paths.py -> repo root) if the marker is absent, which
    is the normal source checkout.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "core" / "contracts").is_dir():
            return parent
    # Source-checkout fallback: src/prompt_debugger/paths.py -> repo root.
    return here.parents[2]


def core_dir() -> Path:
    return repo_root() / "core"


def contracts_dir() -> Path:
    return core_dir() / "contracts"


def knowledge_dir() -> Path:
    return core_dir() / "knowledge"
