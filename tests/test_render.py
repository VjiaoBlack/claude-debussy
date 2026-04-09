"""Tests for debussy.render — assert real output magic bytes where possible."""

from __future__ import annotations

from pathlib import Path

from debussy import render


class TestMidi:
    def test_twinkle_midi_has_mthd_header(self, twinkle: str, tmp_path: Path) -> None:
        out = tmp_path / "out.mid"
        render.render(twinkle, fmt="midi", out=str(out))
        assert out.exists()
        assert out.read_bytes().startswith(b"MThd")

    def test_autumn_leaves_midi_roundtrips(self, autumn: str, tmp_path: Path) -> None:
        out = tmp_path / "a.mid"
        render.render(autumn, fmt="midi", out=str(out))
        assert out.stat().st_size > 100  # should carry all 8 bars x 3 parts


class TestMusicxml:
    def test_roundtrip(self, twinkle: str, tmp_path: Path) -> None:
        out = tmp_path / "out.musicxml"
        render.render(twinkle, fmt="musicxml", out=str(out))
        text = out.read_text(encoding="utf-8")
        assert "<score-partwise" in text or "<score-timewise" in text


class TestPdf:
    def test_twinkle_pdf_header(self, twinkle: str, tmp_path: Path) -> None:
        out = tmp_path / "out.pdf"
        render.render(twinkle, fmt="pdf", out=str(out))
        assert out.exists()
        assert out.read_bytes().startswith(b"%PDF")

    def test_autumn_leaves_multi_instrument_pdf(self, autumn: str, tmp_path: Path) -> None:
        out = tmp_path / "a.pdf"
        render.render(autumn, fmt="pdf", out=str(out))
        assert out.read_bytes().startswith(b"%PDF")
        assert out.stat().st_size > 5_000  # non-trivial size

    def test_barbershop_four_part_pdf(self, barbershop: str, tmp_path: Path) -> None:
        out = tmp_path / "bs.pdf"
        render.render(barbershop, fmt="pdf", out=str(out))
        assert out.read_bytes().startswith(b"%PDF")


class TestSvg:
    def test_svg_contains_svg_element(self, twinkle: str, tmp_path: Path) -> None:
        out = tmp_path / "out.svg"
        render.render(twinkle, fmt="svg", out=str(out))
        text = out.read_text(encoding="utf-8")
        assert text.lstrip().startswith("<svg") or "<svg " in text[:500]


class TestPng:
    def test_png_magic_bytes(self, twinkle: str, tmp_path: Path) -> None:
        out = tmp_path / "out.png"
        render.render(twinkle, fmt="png", out=str(out))
        assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
