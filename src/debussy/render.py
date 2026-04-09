"""Render a score to MIDI, MusicXML, or PDF (via LilyPond/MuseScore if present)."""

from __future__ import annotations

import shutil
from pathlib import Path

from debussy.score_io import load


_FORMAT_EXT = {
    "midi": "mid",
    "musicxml": "musicxml",
    "lily": "ly",
    "pdf": "pdf",
    "png": "png",
}


def render(path: str, fmt: str = "midi", out: str | None = None) -> str:
    """Write the score in the requested format.

    PDF/PNG require LilyPond or MuseScore to be installed; music21 will pick
    whichever it can find. If neither is available we fall back to .ly source
    (LilyPond text), which the user can render later.
    """
    fmt = fmt.lower()
    if fmt not in _FORMAT_EXT:
        raise ValueError(f"unknown format {fmt!r}; choose from {sorted(_FORMAT_EXT)}")

    score = load(path)
    out_path = Path(out) if out else Path(path).with_suffix("." + _FORMAT_EXT[fmt])

    if fmt == "midi":
        score.write("midi", fp=str(out_path))
    elif fmt == "musicxml":
        score.write("musicxml", fp=str(out_path))
    elif fmt == "lily":
        score.write("lily", fp=str(out_path))
    elif fmt in ("pdf", "png"):
        have_lily = shutil.which("lilypond") is not None
        have_muse = any(
            shutil.which(b) for b in ("musescore", "musescore4", "mscore", "MuseScore4")
        )
        if have_lily:
            score.write(f"lily.{fmt}", fp=str(out_path))
        elif have_muse:
            score.write(f"musicxml.{fmt}", fp=str(out_path))
        else:
            return (
                f"no {fmt.upper()} backend found — install `lilypond` or "
                f"`musescore` (apt install lilypond / brew install lilypond) "
                f"to render {fmt.upper()} directly.\n"
                f"Alternative: run `debussy preview {path}` for a live "
                f"in-browser render (no install needed)."
            )

    return f"wrote {out_path}"
