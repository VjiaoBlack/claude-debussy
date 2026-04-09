"""Tests for vibe edits: dynamics, articulations, tempo, text, slur, hairpin."""

from __future__ import annotations

import pytest
from music21 import (
    articulations,
    chord,
    dynamics,
    expressions,
    note,
    spanner,
    tempo as m21tempo,
)

from debussy import ops
from debussy.score_io import load


def _all(score, cls):
    return list(score.recurse().getElementsByClass(cls))


class TestDynamics:
    def test_dynamic_appears_in_measure(self, twinkle: str) -> None:
        ops.add_dynamic(twinkle, measure=1, beat=1, marking="p", part=1)
        s = load(twinkle)
        dyns = _all(s, dynamics.Dynamic)
        assert any(d.value == "p" for d in dyns)

    def test_two_dynamics_can_coexist(self, twinkle: str) -> None:
        ops.add_dynamic(twinkle, measure=1, beat=1, marking="p", part=1)
        ops.add_dynamic(twinkle, measure=3, beat=1, marking="f", part=1)
        s = load(twinkle)
        values = {d.value for d in _all(s, dynamics.Dynamic)}
        assert {"p", "f"} <= values

    def test_invalid_dynamic_rejected(self, twinkle: str) -> None:
        with pytest.raises(ValueError):
            ops.add_dynamic(twinkle, measure=1, beat=1, marking="wat", part=1)


class TestArticulations:
    def test_staccato_attaches_to_note(self, twinkle: str) -> None:
        ops.add_articulation(
            twinkle, measure=1, beat=1, kind="staccato", part=1, voice=1
        )
        s = load(twinkle)
        # Find m.1 beat 1 in the melody
        first = next(
            n for n in list(s.parts)[0].measure(1).recurse().notes
            if isinstance(n, (note.Note, chord.Chord))
        )
        assert any(
            isinstance(a, articulations.Staccato) for a in first.articulations
        )

    def test_fermata_goes_into_expressions(self, twinkle: str) -> None:
        ops.add_articulation(
            twinkle, measure=4, beat=3, kind="fermata", part=1, voice=1
        )
        s = load(twinkle)
        m = list(s.parts)[0].measure(4)
        # Last note at beat 3 (after two quarters)
        target = None
        for el in m.recurse().notesAndRests:
            if float(el.offset) == 2.0 and isinstance(el, (note.Note, chord.Chord)):
                target = el
                break
        assert target is not None
        assert any(isinstance(e, expressions.Fermata) for e in target.expressions)


class TestTempoMark:
    def test_adds_metronome_mark(self, twinkle: str) -> None:
        ops.add_tempo_mark(twinkle, measure=1, bpm=76, text="Andante")
        s = load(twinkle)
        marks = _all(s, m21tempo.MetronomeMark)
        # At least one should now match 76 bpm
        assert any(m.number == 76 for m in marks)

    def test_requires_bpm_or_text(self, twinkle: str) -> None:
        with pytest.raises(ValueError):
            ops.add_tempo_mark(twinkle, measure=1)


class TestTextExpression:
    def test_text_inserted(self, twinkle: str) -> None:
        ops.add_text_expression(twinkle, measure=3, beat=3, text="rit.", part=1)
        s = load(twinkle)
        texts = [te.content for te in _all(s, expressions.TextExpression)]
        assert "rit." in texts


class TestSlur:
    def test_slur_spans_two_notes(self, twinkle: str) -> None:
        ops.add_slur(
            twinkle,
            from_measure=1, from_beat=1,
            to_measure=1, to_beat=4,
            part=1, voice=1,
        )
        s = load(twinkle)
        slurs = _all(s, spanner.Slur)
        assert len(slurs) >= 1


class TestHairpin:
    def test_crescendo_inserted(self, twinkle: str) -> None:
        ops.add_hairpin(
            twinkle, "cresc",
            from_measure=1, from_beat=1,
            to_measure=2, to_beat=3,
            part=1, voice=1,
        )
        s = load(twinkle)
        cresc = _all(s, dynamics.Crescendo)
        assert len(cresc) == 1

    def test_diminuendo_inserted(self, twinkle: str) -> None:
        ops.add_hairpin(
            twinkle, "dim",
            from_measure=3, from_beat=1,
            to_measure=4, to_beat=3,
            part=1, voice=1,
        )
        s = load(twinkle)
        dim = _all(s, dynamics.Diminuendo)
        assert len(dim) == 1

    def test_invalid_kind_rejected(self, twinkle: str) -> None:
        with pytest.raises(ValueError):
            ops.add_hairpin(
                twinkle, "nope",
                from_measure=1, from_beat=1,
                to_measure=2, to_beat=1,
            )
