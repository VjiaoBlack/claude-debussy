"""Centralised MusicXML load/save + shared formatting helpers.

music21 is noisy on import; we silence the unrelated warnings.
"""

from __future__ import annotations

import os
import warnings
from fractions import Fraction
from pathlib import Path
from typing import Iterable

warnings.filterwarnings("ignore", category=DeprecationWarning)

from music21 import converter, stream  # noqa: E402


def load(path: str | os.PathLike) -> stream.Score:
    """Parse a MusicXML (.xml/.musicxml/.mxl) file into a music21 Score."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Score not found: {p}")
    parsed = converter.parse(str(p), forceSource=True)
    if not isinstance(parsed, stream.Score):
        # Wrap bare Parts / Streams so downstream code can assume a Score.
        s = stream.Score()
        s.append(parsed)
        return s
    return parsed


def save(score: stream.Score, path: str | os.PathLike) -> None:
    """Write a Score back to disk as MusicXML."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    score.write("musicxml", fp=str(p))


# ---------------------------------------------------------------------------
# Formatting helpers — keep digest output compact and Claude-friendly.
# ---------------------------------------------------------------------------

# Map quarterLength → single-letter duration token.
# Dots and tuplets are appended.
_DUR_TOKENS = {
    Fraction(4): "w",
    Fraction(2): "h",
    Fraction(1): "q",
    Fraction(1, 2): "e",
    Fraction(1, 4): "s",
    Fraction(1, 8): "t",   # 32nd
    Fraction(1, 16): "x",  # 64th
}


def fmt_duration(ql: float | Fraction) -> str:
    """Render a music21 quarterLength as a short token like q, h., e3."""
    if ql == 0:
        return "gr"  # grace / zero-length
    f = Fraction(ql).limit_denominator(64)

    # Try plain, dotted, double-dotted
    for base_ql, tok in _DUR_TOKENS.items():
        if f == base_ql:
            return tok
        if f == base_ql * Fraction(3, 2):
            return tok + "."
        if f == base_ql * Fraction(7, 4):
            return tok + ".."

    # Tuplet: find closest power-of-two base
    for base_ql, tok in _DUR_TOKENS.items():
        ratio = f / base_ql
        # triplet: 2/3, quintuplet: 4/5, septuplet: 4/7
        if ratio == Fraction(2, 3):
            return tok + "3"
        if ratio == Fraction(4, 5):
            return tok + "5"
        if ratio == Fraction(4, 7):
            return tok + "7"

    return f"[{f}]"


def fmt_pitch(pitch_str: str) -> str:
    """Normalise a music21 pitch name: C#4 → C#4, B-3 → Bb3."""
    return pitch_str.replace("-", "b")


def fmt_beat(beat: float | Fraction) -> str:
    """Render a beat position as @1, @1.5, @2.25 etc."""
    f = Fraction(beat).limit_denominator(16)
    if f.denominator == 1:
        return f"@{f.numerator}"
    return f"@{float(f):g}"


def parse_pitch(p: str) -> str:
    """Accept user pitches in C#4 / Cs4 / Db4 form → music21 canonical."""
    return p.replace("b", "-").replace("s", "#")


def chunks(seq: Iterable, n: int):
    buf: list = []
    for x in seq:
        buf.append(x)
        if len(buf) == n:
            yield buf
            buf = []
    if buf:
        yield buf
