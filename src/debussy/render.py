"""Render scores to MIDI, MusicXML, PDF, SVG, PNG.

Backends, in order of preference:
  * Verovio (Python binding) — always available; produces SVG, MIDI, and
    stitched multi-page PDF (via cairosvg + pypdf). No external tools.
  * LilyPond / MuseScore — only used for `lily` format, if installed.
"""

from __future__ import annotations

import base64
import io
import shutil
from pathlib import Path

from debussy.score_io import load


_FORMAT_EXT = {
    "midi": "mid",
    "musicxml": "musicxml",
    "svg": "svg",
    "pdf": "pdf",
    "png": "png",
    "lily": "ly",
}


def render(path: str, fmt: str = "midi", out: str | None = None) -> str:
    """Write the score in the requested format."""
    fmt = fmt.lower()
    if fmt not in _FORMAT_EXT:
        raise ValueError(f"unknown format {fmt!r}; choose from {sorted(_FORMAT_EXT)}")

    src = Path(path)
    out_path = Path(out) if out else src.with_suffix("." + _FORMAT_EXT[fmt])

    if fmt == "midi":
        return _render_midi(src, out_path)
    if fmt == "musicxml":
        return _render_musicxml(src, out_path)
    if fmt == "svg":
        return _render_svg(src, out_path)
    if fmt == "pdf":
        return _render_pdf(src, out_path)
    if fmt == "png":
        return _render_png(src, out_path)
    if fmt == "lily":
        return _render_lily(src, out_path)
    raise AssertionError("unreachable")


# ---------------------------------------------------------------------------
# music21 paths
# ---------------------------------------------------------------------------


def _render_musicxml(src: Path, out: Path) -> str:
    score = load(src)
    score.write("musicxml", fp=str(out))
    return f"wrote {out}"


def _render_lily(src: Path, out: Path) -> str:
    if not shutil.which("lilypond"):
        return (
            "LilyPond is not installed — `lily` format needs the `lilypond` "
            "binary on PATH. Try `--format pdf` (uses Verovio, no install) "
            "or `apt install lilypond` / `brew install lilypond`."
        )
    score = load(src)
    score.write("lily", fp=str(out))
    return f"wrote {out}"


# ---------------------------------------------------------------------------
# verovio paths
# ---------------------------------------------------------------------------


def _verovio_toolkit(src: Path):
    import verovio

    tk = verovio.toolkit()
    tk.setOptions(
        {
            "pageWidth": 2100,   # ~ letter width at 100 dpi
            "pageHeight": 2970,
            "scale": 40,
            "adjustPageHeight": False,
            "breaks": "auto",
            "footer": "none",
            "header": "auto",
        }
    )
    tk.loadFile(str(src))
    return tk


def _render_midi(src: Path, out: Path) -> str:
    """Verovio gives us a MIDI base64 string."""
    tk = _verovio_toolkit(src)
    b64 = tk.renderToMIDI()
    out.write_bytes(base64.b64decode(b64))
    return f"wrote {out}  ({out.stat().st_size} bytes)"


def _render_svg(src: Path, out: Path) -> str:
    """Render all pages into a single standalone SVG file (page 1) or a
    directory of per-page SVGs if the score has multiple pages.
    """
    tk = _verovio_toolkit(src)
    n = tk.getPageCount()
    if n <= 1:
        out.write_text(tk.renderToSVG(1), encoding="utf-8")
        return f"wrote {out}"

    out_dir = out.with_suffix("")
    out_dir.mkdir(exist_ok=True)
    for i in range(1, n + 1):
        (out_dir / f"page-{i:02d}.svg").write_text(
            tk.renderToSVG(i), encoding="utf-8"
        )
    return f"wrote {n} pages into {out_dir}/"


def _render_pdf(src: Path, out: Path) -> str:
    """Verovio SVG pages → cairosvg → per-page PDFs → pypdf merge."""
    import cairosvg
    from pypdf import PdfWriter, PdfReader

    tk = _verovio_toolkit(src)
    n = tk.getPageCount()
    writer = PdfWriter()
    for i in range(1, n + 1):
        svg = tk.renderToSVG(i)
        pdf_bytes = io.BytesIO()
        cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=pdf_bytes)
        pdf_bytes.seek(0)
        reader = PdfReader(pdf_bytes)
        for page in reader.pages:
            writer.add_page(page)
    with out.open("wb") as f:
        writer.write(f)
    return f"wrote {out}  ({n} page{'s' if n != 1 else ''}, {out.stat().st_size} bytes)"


def _render_png(src: Path, out: Path) -> str:
    import cairosvg

    tk = _verovio_toolkit(src)
    n = tk.getPageCount()
    if n == 1:
        cairosvg.svg2png(
            bytestring=tk.renderToSVG(1).encode("utf-8"),
            write_to=str(out),
            output_width=1200,
        )
        return f"wrote {out}"

    out_dir = out.with_suffix("")
    out_dir.mkdir(exist_ok=True)
    for i in range(1, n + 1):
        cairosvg.svg2png(
            bytestring=tk.renderToSVG(i).encode("utf-8"),
            write_to=str(out_dir / f"page-{i:02d}.png"),
            output_width=1200,
        )
    return f"wrote {n} pages into {out_dir}/"
