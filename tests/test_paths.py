"""The path-resolution module locates core/ correctly (M0 library smoke test)."""

from __future__ import annotations

from pathlib import Path

from prompt_debugger import CONTRACT_VERSIONS, __version__
from prompt_debugger.paths import contracts_dir, core_dir, knowledge_dir, repo_root


def test_repo_root_contains_core() -> None:
    assert (repo_root() / "core" / "contracts").is_dir()


def test_core_subdirs_resolve() -> None:
    assert core_dir().is_dir()
    assert contracts_dir().is_dir()
    assert knowledge_dir().is_dir()
    assert (knowledge_dir() / "manifest.json").is_file()


def test_version_is_a_string() -> None:
    assert isinstance(__version__, str) and __version__


def test_contract_versions_are_positive_ints() -> None:
    assert CONTRACT_VERSIONS
    for name, ver in CONTRACT_VERSIONS.items():
        assert isinstance(ver, int) and ver >= 1, name


def test_repo_root_is_a_path() -> None:
    assert isinstance(repo_root(), Path)
