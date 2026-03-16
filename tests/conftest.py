from __future__ import annotations

import pytest

from ghosttpy import Ghostty


class ScriptRecorder:
    """Transport that records scripts and returns pre-queued responses."""

    def __init__(self) -> None:
        self.scripts: list[str] = []
        self._responses: list[str] = []

    def respond(self, *responses: str) -> None:
        self._responses.extend(responses)

    def __call__(self, source: str) -> str:
        self.scripts.append(source)
        return self._responses.pop(0) if self._responses else ""

    @property
    def last(self) -> str:
        return self.scripts[-1]


@pytest.fixture
def rec() -> ScriptRecorder:
    return ScriptRecorder()


@pytest.fixture
def g(rec: ScriptRecorder) -> Ghostty:
    return Ghostty(transport=rec)
