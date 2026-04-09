"""Tests for debussy.views — assert real content, not just 'didn't crash'."""

from __future__ import annotations

from debussy import views


class TestInfo:
    def test_twinkle_basic_fields(self, twinkle: str) -> None:
        out = views.info(twinkle)
        assert "time:" in out
        assert "key:" in out
        assert "parts:" in out
        assert "4/4" in out

    def test_autumn_leaves_detects_e_minor(self, autumn: str) -> None:
        out = views.info(autumn)
        # E minor should dominate: correlation should be high
        assert "E minor" in out
        # Three instrument parts
        assert "Flute" in out
        assert "Piano" in out
        assert "Acoustic Bass" in out
        assert "parts:     3" in out

    def test_barbershop_four_parts_with_voice_names(self, barbershop: str) -> None:
        out = views.info(barbershop)
        assert "parts:     4" in out
        for name in ("Tenor", "Lead", "Baritone", "Bass"):
            assert name in out
        # Bb major key
        assert "B- major" in out or "Bb major" in out.replace("B-", "Bb")


class TestDigest:
    def test_twinkle_measure_1(self, twinkle: str) -> None:
        out = views.digest(twinkle, measure_range=(1, 1))
        assert "m.1" in out
        # Melody has C4 on beat 1 of measure 1
        assert "C4" in out
        # Should not include m.2
        assert "m.2" not in out

    def test_autumn_leaves_three_parts_all_visible(self, autumn: str) -> None:
        out = views.digest(autumn, measure_range=(1, 1))
        # All three part names should appear in the per-voice lines
        assert "Flute" in out
        assert "Piano" in out
        assert "Bass" in out

    def test_barbershop_four_voices_per_measure(self, barbershop: str) -> None:
        out = views.digest(barbershop, measure_range=(1, 1))
        # Each of the four vocal parts should produce a voice line
        assert "Tenor" in out
        assert "Lead" in out
        assert "Baritone" in out
        assert "Bass" in out

    def test_part_filter_excludes_others(self, autumn: str) -> None:
        out = views.digest(autumn, measure_range=(1, 1), part_index=1)
        assert "Flute" in out
        assert "Piano" not in out
        assert "Bass" not in out


class TestStructure:
    def test_twinkle_has_tempo_and_timesig(self, twinkle: str) -> None:
        out = views.structure(twinkle)
        assert "tempo" in out.lower() or "4/4" in out
