"""Tests for debussy.analyze — key detection and chord/Roman analysis."""

from __future__ import annotations

from debussy import analyze


class TestKey:
    def test_autumn_leaves_is_e_minor(self, autumn: str) -> None:
        out = analyze.analyze_key(autumn)
        assert "E minor" in out
        # E minor correlation should be high (>0.85) — a solid detection
        for line in out.splitlines():
            if "best:" in line and "E minor" in line:
                # Parse "corr=0.93"
                corr = float(line.split("corr=")[1].rstrip(")"))
                assert corr > 0.85, f"E minor correlation too low: {corr}"
                return
        raise AssertionError("no E minor best-match line")

    def test_barbershop_is_bb_major(self, barbershop: str) -> None:
        out = analyze.analyze_key(barbershop)
        # music21 prints Bb as B-
        assert "B- major" in out or "Bb major" in out

    def test_alternatives_listed(self, autumn: str) -> None:
        out = analyze.analyze_key(autumn)
        assert "alternatives:" in out


class TestChords:
    def test_autumn_leaves_progression_length(self, autumn: str) -> None:
        out = analyze.analyze_progression(autumn)
        # Expect 8 measures in the progression line(s)
        measure_tokens = [tok for tok in out.split() if tok.startswith("m") and ":" in tok]
        assert len(measure_tokens) == 8, f"expected 8, got {len(measure_tokens)}"

    def test_autumn_leaves_first_chord_is_minor_seventh(self, autumn: str) -> None:
        out = analyze.analyze_chords(autumn, measure_range=(1, 1))
        # m.1 is an Am7 — should be labelled as a minor seventh chord
        assert "m.1" in out
        assert "minor seventh" in out.lower() or "iv7" in out or "i7" in out

    def test_autumn_leaves_dominant_chord_identified(self, autumn: str) -> None:
        # m.6 is B7 — the V7 of E minor; should be a dominant seventh
        out = analyze.analyze_chords(autumn, measure_range=(6, 6))
        assert "m.6" in out
        assert "dominant seventh" in out.lower() or "V" in out

    def test_per_measure_gives_one_line_per_bar(self, autumn: str) -> None:
        out = analyze.analyze_chords(autumn, beat_resolution=0.0)
        lines_with_m = [ln for ln in out.splitlines() if ln.startswith("m.")]
        assert len(lines_with_m) == 8
