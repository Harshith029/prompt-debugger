"""The M0 tooling runs green on the repository as committed.

These call the tool entry points in-process so CI failures point at the specific tool.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import check_imports  # noqa: E402
import check_links  # noqa: E402
import check_plugin_sync  # noqa: E402
import validate_schemas  # noqa: E402


def test_import_policy_passes() -> None:
    assert check_imports.main() == 0


def test_links_resolve() -> None:
    assert check_links.main() == 0


def test_schema_subset_and_instances_valid() -> None:
    # jsonschema is a dev dependency and present in CI; require it here.
    assert validate_schemas.main(["--require-jsonschema"]) == 0


def test_plugin_vendor_in_sync() -> None:
    assert check_plugin_sync.main() == 0
