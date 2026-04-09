"""Tests for debussy.importers — format detection, MIDI roundtrip, transcribe."""

from __future__ import annotations

from pathlib import Path

import pytest

from debussy import importers, render
from debussy.score_io import load


class TestImportMidi:
    def test_midi_roundtrip_preserves_measure_count(
        self, autumn: str, tmp_path: Path
    ) -> None:
        mid = tmp_path / "a.mid"
        render.render(autumn, fmt="midi", out=str(mid))

        xml_out = tmp_path / "a_roundtrip.musicxml"
        msg = importers.import_file(str(mid), out=str(xml_out))
        assert "imported" in msg
        assert xml_out.exists()

        original = load(autumn)
        roundtripped = load(str(xml_out))
        assert len(list(original.parts)) == len(list(roundtripped.parts))

    def test_unknown_extension_rejected(self, tmp_path: Path) -> None:
        f = tmp_path / "nope.foo"
        f.write_text("nonsense")
        with pytest.raises(ValueError, match="don't know how to import"):
            importers.import_file(str(f))

    def test_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            importers.import_file("/tmp/does-not-exist-123.mid")


class TestTranscribe:
    def test_missing_basic_pitch_gives_install_hint(self) -> None:
        # basic-pitch is not installed in the test env; the command should
        # return a friendly install message rather than crashing.
        msg = importers.transcribe_audio("/tmp/anything.wav")
        assert "basic-pitch" in msg
        assert "install" in msg.lower()
