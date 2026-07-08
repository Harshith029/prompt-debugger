"""Shared test fixtures and the runtime network-block harness (ADR-0006, review F12).

An autouse, session-scoped fixture replaces socket.socket with a stub that raises for
the entire test run. This enforces the "no runtime network I/O" policy behaviorally:
if any shipped-code path ever tries to open a socket during tests, the suite fails
loudly rather than silently reaching the network. jsonschema and stdlib JSON do not
open sockets, so legitimate tests are unaffected.
"""

from __future__ import annotations

import socket
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parent.parent
# Make the core library importable without installation.
sys.path.insert(0, str(REPO / "src"))


class _BlockedSocket:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError(
            "Network access is blocked in tests: shipped code must perform no runtime "
            "network I/O (ADR-0006). If a test genuinely needs a socket, it does not "
            "belong in this suite."
        )


@pytest.fixture(scope="session", autouse=True)
def _block_network() -> Iterator[None]:
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(socket, "socket", _BlockedSocket)
    try:
        yield
    finally:
        monkeypatch.undo()


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO
