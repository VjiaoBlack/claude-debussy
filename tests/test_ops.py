"""Tests for note-level edit ops — round-trip every change through disk."""

from __future__ import annotations

from music21 import chord, note, stream

from debussy import ops
from debussy.score_io import load


def _first_note_in_measure(path: str, measure: int, part: int = 1):
    s = load(path)
    m = list(s.parts)[part - 1].measure(measure)
    for el in m.recurse().notesAndRests:
        if isinstance(el, (note.Note, chord.Chord, note.Rest)):
            return el
    return None


def _count_measures(path: str, part: int = 1) -> int:
    s = load(path)
    return len(list(s.parts)[part - 1].getElementsByClass(stream.Measure))


class TestSetNote:
    def test_pitch_changes_persist(self, twinkle: str) -> None:
        ops.set_note(twinkle, measure=1, beat=1, new_pitch="F#4", part=1)
        el = _first_note_in_measure(twinkle, 1, 1)
        assert isinstance(el, note.Note)
        assert el.pitch.nameWithOctave == "F#4"

    def test_flat_pitch_syntax_accepted(self, twinkle: str) -> None:
        # "Bb4" must be normalised to music21's "B-4"
        ops.set_note(twinkle, measure=1, beat=1, new_pitch="Bb4", part=1)
        el = _first_note_in_measure(twinkle, 1, 1)
        assert el.pitch.name == "B-"

    def test_beat_2_targets_second_note(self, twinkle: str) -> None:
        # The melody starts C4 C4, so changing beat 2 shouldn't affect beat 1
        ops.set_note(twinkle, measure=1, beat=2, new_pitch="E4", part=1)
        s = load(twinkle)
        mel = list(s.parts)[0].measure(1)
        notes_only = [n for n in mel.notesAndRests if isinstance(n, note.Note)]
        assert notes_only[0].pitch.nameWithOctave == "C4"
        assert notes_only[1].pitch.nameWithOctave == "E4"


class TestSetRest:
    def test_note_becomes_rest(self, twinkle: str) -> None:
        ops.set_rest(twinkle, measure=1, beat=1, part=1)
        el = _first_note_in_measure(twinkle, 1, 1)
        assert isinstance(el, note.Rest)


class TestTranspose:
    def test_whole_score_up_major_third(self, twinkle: str) -> None:
        # Melody opens on C4 — after +M3 it should be E4
        ops.transpose(twinkle, "M3")
        el = _first_note_in_measure(twinkle, 1, 1)
        assert isinstance(el, note.Note)
        assert el.pitch.nameWithOctave == "E4"

    def test_range_only_preserves_outside(self, autumn: str) -> None:
        # Transpose only the bass, only m.1-2, and make sure m.3 is untouched
        s_before = load(autumn)
        before_m3_bass = next(
            n for n in list(s_before.parts)[2].measure(3).recurse().notes
            if isinstance(n, note.Note)
        )
        ops.transpose(autumn, "P5", measure_range=(1, 2), part=3)
        s_after = load(autumn)
        after_m3_bass = next(
            n for n in list(s_after.parts)[2].measure(3).recurse().notes
            if isinstance(n, note.Note)
        )
        assert before_m3_bass.pitch.nameWithOctave == after_m3_bass.pitch.nameWithOctave


class TestReplaceMeasure:
    def test_rewrites_content(self, twinkle: str) -> None:
        ops.replace_measure(
            twinkle,
            measure=1,
            spec="C4/q E4/q G4/q C5/q",
            part=1,
            voice=1,
        )
        s = load(twinkle)
        m = list(s.parts)[0].measure(1)
        names = [
            n.pitch.nameWithOctave
            for n in m.recurse().notes
            if isinstance(n, note.Note)
        ]
        assert names == ["C4", "E4", "G4", "C5"]

    def test_chord_token(self, twinkle: str) -> None:
        ops.replace_measure(
            twinkle,
            measure=1,
            spec="[C4,E4,G4]/h [D4,F4,A4]/h",
            part=1,
            voice=1,
        )
        s = load(twinkle)
        m = list(s.parts)[0].measure(1)
        chords = [el for el in m.recurse().notes if isinstance(el, chord.Chord)]
        assert len(chords) == 2
        assert len(chords[0].pitches) == 3


class TestInsertDeleteMeasures:
    def test_insert_adds_one_measure(self, twinkle: str) -> None:
        before = _count_measures(twinkle, part=1)
        ops.insert_measure(twinkle, after=2)
        after = _count_measures(twinkle, part=1)
        assert after == before + 1

    def test_delete_removes_range(self, twinkle: str) -> None:
        before = _count_measures(twinkle, part=1)
        ops.delete_measures(twinkle, (3, 4))
        after = _count_measures(twinkle, part=1)
        assert after == before - 2


class TestApplyScript:
    def test_octave_bump(self, twinkle: str, tmp_path) -> None:
        script = tmp_path / "bump.py"
        script.write_text(
            "from music21 import note\n"
            "for n in list(score.parts)[0].recurse().notes:\n"
            "    if isinstance(n, note.Note):\n"
            "        n.pitch.octave += 1\n"
        )
        ops.apply_script(twinkle, str(script))
        el = _first_note_in_measure(twinkle, 1, 1)
        assert isinstance(el, note.Note)
        assert el.pitch.octave == 5  # was 4
