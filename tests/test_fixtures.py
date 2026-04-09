"""Tests for the extended fixture set: Bach chorale, Chopin prelude,
polyrhythm, pop ballad.

Each fixture targets a specific corner of the codebase:
  - Bach chorale: real PD corpus, SATB voice leading, Picardy third cadence
  - Chopin prelude: dense dynamics + text expressions baked into metadata
  - Polyrhythm: tuplet handling in digest + score_io.fmt_duration
  - Pop ballad: multi-part w/ lyrics on just one voice, four-chord progression
"""

from __future__ import annotations

from pathlib import Path

from music21 import dynamics as m21dyn
from music21 import chord, expressions, note, stream

from debussy import analyze, render, views
from debussy.score_io import load


# ---------------------------------------------------------------------------
# Bach chorale (real BWV 66.6 from music21 corpus)
# ---------------------------------------------------------------------------


class TestBachChorale:
    def test_metadata_matches_bach(self, bach: str) -> None:
        out = views.info(bach)
        assert "Bach" in out
        assert "F# minor" in out

    def test_four_satb_parts(self, bach: str) -> None:
        out = views.info(bach)
        for part_name in ("Soprano", "Alto", "Tenor", "Bass"):
            assert part_name in out, f"{part_name} missing from info output"

    def test_key_detection_very_confident(self, bach: str) -> None:
        # Real Bach should give near-certain key detection
        out = analyze.analyze_key(bach)
        for line in out.splitlines():
            if "best:" in line and "F# minor" in line:
                corr = float(line.split("corr=")[1].rstrip(")"))
                assert corr > 0.90, f"F# minor corr too low: {corr}"
                return
        raise AssertionError("F# minor not the best key interpretation")

    def test_picardy_third_final_cadence(self, bach: str) -> None:
        """BWV 66.6 ends with a Picardy third: an F# major chord closing a
        piece in F# minor. Verify the last measure's chord contains A# (the
        raised third) rather than A natural."""
        s = load(bach)
        chordified = s.chordify()
        measures = list(chordified.getElementsByClass(stream.Measure))
        last = measures[-1]
        last_chord = None
        for c in last.getElementsByClass(chord.Chord):
            last_chord = c
        assert last_chord is not None, "last measure has no chord"
        pitch_names = {p.name for p in last_chord.pitches}
        # A# (raised third of F# minor → F# major) proves Picardy third
        assert "A#" in pitch_names, (
            f"expected Picardy third (A# in final chord), got {pitch_names}"
        )

    def test_bach_renders_pdf(self, bach: str, tmp_path: Path) -> None:
        out = tmp_path / "bach.pdf"
        render.render(bach, fmt="pdf", out=str(out))
        assert out.read_bytes().startswith(b"%PDF")


# ---------------------------------------------------------------------------
# Chopin prelude (original, dense dynamics + text expressions)
# ---------------------------------------------------------------------------


class TestChopinPrelude:
    def test_two_two_time_signature(self, chopin: str) -> None:
        out = views.info(chopin)
        assert "2/2" in out

    def test_e_minor_detected(self, chopin: str) -> None:
        out = views.info(chopin)
        assert "E minor" in out

    def test_dense_dynamics_persist(self, chopin: str) -> None:
        s = load(chopin)
        values = {
            d.value for d in s.recurse().getElementsByClass(m21dyn.Dynamic)
        }
        assert {"p", "mf", "pp"} <= values

    def test_expressive_text_markings_persist(self, chopin: str) -> None:
        s = load(chopin)
        texts = [
            te.content
            for te in s.recurse().getElementsByClass(expressions.TextExpression)
        ]
        combined = " ".join(texts).lower()
        assert "dolente" in combined
        assert "cresc" in combined
        assert "morendo" in combined

    def test_chopin_renders_pdf(self, chopin: str, tmp_path: Path) -> None:
        out = tmp_path / "chopin.pdf"
        render.render(chopin, fmt="pdf", out=str(out))
        assert out.read_bytes().startswith(b"%PDF")


# ---------------------------------------------------------------------------
# Polyrhythm (3-against-4 tuplets)
# ---------------------------------------------------------------------------


class TestPolyrhythm:
    def test_digest_contains_half_triplet_token(self, polyrhythm: str) -> None:
        out = views.digest(polyrhythm)
        # score_io.fmt_duration renders half-note triplets as "h3"
        assert "h3" in out, f"no h3 (half triplet) in digest:\n{out}"

    def test_digest_contains_eighth_triplet_token(self, polyrhythm: str) -> None:
        out = views.digest(polyrhythm)
        assert "e3" in out, f"no e3 (eighth triplet) in digest:\n{out}"

    def test_measure_3_has_twelve_eighth_triplets_in_rh(
        self, polyrhythm: str
    ) -> None:
        s = load(polyrhythm)
        rh_m3 = list(s.parts)[0].measure(3)
        notes = [
            n for n in rh_m3.recurse().notes if isinstance(n, note.Note)
        ]
        assert len(notes) == 12

    def test_measure_1_has_three_half_triplets_in_lh(
        self, polyrhythm: str
    ) -> None:
        s = load(polyrhythm)
        lh_m1 = list(s.parts)[1].measure(1)
        notes = [
            n for n in lh_m1.recurse().notes if isinstance(n, note.Note)
        ]
        assert len(notes) == 3
        # Each should be a half-note triplet = 4/3 quarter lengths
        for n in notes:
            assert abs(float(n.duration.quarterLength) - 4 / 3) < 1e-6

    def test_measure_lengths_sum_to_four_quarters(self, polyrhythm: str) -> None:
        """Sanity: every measure in every part totals one 4/4 bar."""
        s = load(polyrhythm)
        for part in s.parts:
            for m in part.getElementsByClass(stream.Measure):
                total = sum(float(e.duration.quarterLength) for e in m.notesAndRests)
                assert abs(total - 4.0) < 1e-6, (
                    f"{part.partName} m{m.number} sums to {total}, not 4.0"
                )

    def test_polyrhythm_renders_pdf(self, polyrhythm: str, tmp_path: Path) -> None:
        out = tmp_path / "poly.pdf"
        render.render(polyrhythm, fmt="pdf", out=str(out))
        assert out.read_bytes().startswith(b"%PDF")


# ---------------------------------------------------------------------------
# Pop ballad (piano + vocal + lyrics)
# ---------------------------------------------------------------------------


class TestPopBallad:
    def test_three_parts_vocal_and_piano(self, pop: str) -> None:
        out = views.info(pop)
        assert "Vocal" in out
        assert "Piano RH" in out
        assert "Piano LH" in out
        assert "parts:     3" in out

    def test_four_chord_progression(self, pop: str) -> None:
        out = analyze.analyze_progression(pop)
        # I-V-vi-IV should each appear in the progression line
        for numeral in ("I", "V", "vi", "IV"):
            assert f":{numeral}" in out, (
                f"{numeral} missing from progression:\n{out}"
            )

    def test_every_vocal_note_has_a_lyric(self, pop: str) -> None:
        s = load(pop)
        vocal = list(s.parts)[0]
        note_count = 0
        with_lyric = 0
        for n in vocal.recurse().notes:
            if isinstance(n, note.Note):
                note_count += 1
                if n.lyrics:
                    with_lyric += 1
        assert note_count == 32  # 8 bars x 4 quarters
        # The fixture hand-matches 32 syllables to 32 notes
        assert with_lyric == 32

    def test_piano_parts_have_no_lyrics(self, pop: str) -> None:
        s = load(pop)
        for part in list(s.parts)[1:]:
            for n in part.recurse().notes:
                if isinstance(n, note.Note):
                    assert not n.lyrics, (
                        f"piano note at {n.offset} has lyrics — should be vocal only"
                    )

    def test_pop_renders_pdf(self, pop: str, tmp_path: Path) -> None:
        out = tmp_path / "pop.pdf"
        render.render(pop, fmt="pdf", out=str(out))
        assert out.read_bytes().startswith(b"%PDF")


# ---------------------------------------------------------------------------
# Multi-voice-per-staff (two explicit stream.Voice objects per measure)
# ---------------------------------------------------------------------------


class TestMultiVoice:
    def test_two_staves_each_with_two_voices(self, multi_voice: str) -> None:
        s = load(multi_voice)
        assert len(list(s.parts)) == 2
        for p in s.parts:
            for m in p.getElementsByClass(stream.Measure):
                voices = list(m.getElementsByClass(stream.Voice))
                assert len(voices) == 2, (
                    f"{p.partName} m{m.number} has {len(voices)} voices, "
                    f"expected 2"
                )

    def test_digest_shows_all_four_voice_lines(self, multi_voice: str) -> None:
        out = views.digest(multi_voice, measure_range=(1, 1))
        # Each measure should produce 4 voice lines: v1/v2 × 2 staves
        voice_lines = [ln for ln in out.splitlines() if ln.strip().startswith("v")]
        assert len(voice_lines) == 4
        # Staff names appear with their voice indices
        assert any("v1 (Treble)" in ln for ln in voice_lines)
        assert any("v2 (Treble)" in ln for ln in voice_lines)
        assert any("v1 (Bass)" in ln for ln in voice_lines)
        assert any("v2 (Bass)" in ln for ln in voice_lines)

    def test_set_note_voice_2_targets_alto_not_soprano(
        self, multi_voice: str
    ) -> None:
        """The critical multi-voice test: --voice 2 must NOT hit the soprano.

        m.1 starts with Soprano=E5 (v1), Alto=C5 (v2). Changing voice 2 to A4
        should leave the E5 alone and replace the C5.
        """
        from debussy import ops
        ops.set_note(
            multi_voice,
            measure=1,
            beat=1,
            new_pitch="A4",
            part=1,
            voice=2,
        )
        s = load(multi_voice)
        treble_m1 = list(s.parts)[0].measure(1)
        voices = list(treble_m1.getElementsByClass(stream.Voice))
        v1_first = next(
            n for n in voices[0].notesAndRests if isinstance(n, note.Note)
        )
        v2_first = next(
            n for n in voices[1].notesAndRests if isinstance(n, note.Note)
        )
        assert v1_first.pitch.nameWithOctave == "E5", "soprano should be untouched"
        assert v2_first.pitch.nameWithOctave == "A4", "alto should be the new pitch"

    def test_multi_voice_renders_pdf(
        self, multi_voice: str, tmp_path: Path
    ) -> None:
        out = tmp_path / "mv.pdf"
        render.render(multi_voice, fmt="pdf", out=str(out))
        assert out.read_bytes().startswith(b"%PDF")


# ---------------------------------------------------------------------------
# Structure demo (rehearsal marks, repeats, endings, D.S./Coda/Fine, key/time
# changes)
# ---------------------------------------------------------------------------


class TestStructureDemo:
    def test_all_three_rehearsal_marks_reported(
        self, structure_demo: str
    ) -> None:
        out = views.structure(structure_demo)
        assert "m.1: A" in out
        assert "m.6: B" in out
        assert "m.9: C" in out

    def test_repeat_start_and_end_reported(self, structure_demo: str) -> None:
        out = views.structure(structure_demo)
        assert "m.1: start" in out
        # The end repeat is at m.4 with times=2
        assert "m.4: end" in out

    def test_first_and_second_endings_reported(
        self, structure_demo: str
    ) -> None:
        out = views.structure(structure_demo)
        assert "endings:" in out
        assert "[1.]" in out
        assert "[2.]" in out

    def test_segno_coda_ds_fine_all_reported(
        self, structure_demo: str
    ) -> None:
        out = views.structure(structure_demo)
        for marker in ("Segno", "Coda", "D.S.", "Fine"):
            assert marker in out, f"{marker} missing from structure view"

    def test_key_change_mid_piece(self, structure_demo: str) -> None:
        out = views.structure(structure_demo)
        assert "m.1: +0 sharps" in out  # start in C
        assert "m.6: +1 sharps" in out  # modulate to G at m.6

    def test_time_change_mid_piece(self, structure_demo: str) -> None:
        out = views.structure(structure_demo)
        assert "m.1: 4/4" in out
        assert "m.9: 3/4" in out

    def test_tempo_change_mid_piece(self, structure_demo: str) -> None:
        out = views.structure(structure_demo)
        assert "tempo changes:" in out
        assert "132" in out  # Allegro ♩=132 at m.6

    def test_structure_renders_pdf(
        self, structure_demo: str, tmp_path: Path
    ) -> None:
        out = tmp_path / "structure.pdf"
        render.render(structure_demo, fmt="pdf", out=str(out))
        assert out.read_bytes().startswith(b"%PDF")
