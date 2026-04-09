"""Shared pytest fixtures: copies of the example scores into a temp dir.

Every test gets a fresh copy so ops that mutate in place don't leak between
tests.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

_EXAMPLES = Path(__file__).parent.parent / "examples"


def _copy(name: str, tmp_path: Path) -> str:
    src = _EXAMPLES / name
    dst = tmp_path / name
    shutil.copy(src, dst)
    return str(dst)


@pytest.fixture
def twinkle(tmp_path: Path) -> str:
    return _copy("twinkle.musicxml", tmp_path)


@pytest.fixture
def autumn(tmp_path: Path) -> str:
    return _copy("autumn_leaves.musicxml", tmp_path)


@pytest.fixture
def barbershop(tmp_path: Path) -> str:
    return _copy("barbershop.musicxml", tmp_path)


@pytest.fixture
def bach(tmp_path: Path) -> str:
    return _copy("bach_chorale.musicxml", tmp_path)


@pytest.fixture
def chopin(tmp_path: Path) -> str:
    return _copy("chopin_prelude.musicxml", tmp_path)


@pytest.fixture
def polyrhythm(tmp_path: Path) -> str:
    return _copy("polyrhythm.musicxml", tmp_path)


@pytest.fixture
def pop(tmp_path: Path) -> str:
    return _copy("pop_ballad.musicxml", tmp_path)
