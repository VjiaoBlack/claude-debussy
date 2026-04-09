"""Tests for lyrics ops — syllable counting, hyphen grammar, multi-part."""

from __future__ import annotations

from music21 import chord, note

from debussy import ops
from debussy.score_io import load


def _notes_in(path: str, part: int = 1) -> list[note.Note | chord.Chord]:
    s = load(path)
    out = []
    for el in list(s.parts)[part - 1].recurse().notesAndRests:
        if isinstance(el, (note.Note, chord.Chord)):
            out.append(el)
    return out


class TestSplitLyric:
    def test_simple_words(self) -> None:
        out = ops._split_lyric("Twinkle twinkle little star")
        assert out == [
            ("Twinkle", "single"),
            ("twinkle", "single"),
            ("little", "single"),
            ("star", "single"),
        ]

    def test_hyphenated_word_produces_begin_middle_end(self) -> None:
        out = ops._split_lyric("Hal-le-lu-jah")
        syllables = [s for s, _ in out]
        syllabic = [k for _, k in out]
        assert syllables == ["Hal", "le", "lu", "jah"]
        assert syllabic == ["begin", "middle", "middle", "end"]


class TestSetLyrics:
    def test_twinkle_attaches_to_every_note(self, twinkle: str) -> None:
        text = "Twin-kle twin-kle lit-tle star how I won-der what you are"
        msg = ops.set_lyrics(twinkle, (1, 4), text, part=1, voice=1, verse=1)
        # Twinkle melody has 14 notes in m.1-4; all should get a syllable
        assert "14 syllables" in msg
        notes = _notes_in(twinkle, part=1)
        with_lyrics = [n for n in notes if n.lyrics]
        assert len(with_lyrics) == 14
        # First four syllables check out
        assert with_lyrics[0].lyrics[0].text == "Twin"
        assert with_lyrics[1].lyrics[0].text == "kle"
        assert with_lyrics[2].lyrics[0].text == "twin"
        assert with_lyrics[3].lyrics[0].text == "kle"

    def test_multiple_verses_coexist(self, twinkle: str) -> None:
        ops.set_lyrics(twinkle, (1, 4),
                       "When the bla-zing sun is gone when he no-thing shines up-on",
                       part=1, voice=1, verse=1)
        ops.set_lyrics(twinkle, (1, 4),
                       "Then you show your lit-tle light twin-kle twin-kle all the night",
                       part=1, voice=1, verse=2)
        notes = _notes_in(twinkle, part=1)
        with_two = [n for n in notes if len(n.lyrics) >= 2]
        assert len(with_two) >= 10  # most notes have both verses

    def test_barbershop_lyrics_on_each_part(self, barbershop: str) -> None:
        # The barbershop fixture already has verse-1 lyrics from the generator.
        # Verify all 4 parts carry lyrics.
        for part_idx in (1, 2, 3, 4):
            notes = _notes_in(barbershop, part=part_idx)
            with_lyrics = [n for n in notes if n.lyrics]
            assert len(with_lyrics) >= 4, f"part {part_idx} has no lyrics"

    def test_extra_syllables_reported(self, twinkle: str) -> None:
        # Only 2 notes in m.1 beats 1-2, but we give 10 syllables
        msg = ops.set_lyrics(
            twinkle, (1, 1),
            "one two three four five six seven eight nine ten",
            part=1, voice=1,
        )
        assert "extra syllables dropped" in msg


class TestClearLyrics:
    def test_clear_all(self, barbershop: str) -> None:
        ops.clear_lyrics(barbershop, (1, 4), part=1, voice=1)
        notes = _notes_in(barbershop, part=1)
        assert all(not n.lyrics for n in notes)

    def test_clear_specific_verse_preserves_others(self, twinkle: str) -> None:
        ops.set_lyrics(twinkle, (1, 4),
                       "Twin-kle twin-kle lit-tle star how I won-der what you are",
                       part=1, voice=1, verse=1)
        ops.set_lyrics(twinkle, (1, 4),
                       "Up a-bove the world so high like a dia-mond in the sky",
                       part=1, voice=1, verse=2)
        ops.clear_lyrics(twinkle, (1, 4), part=1, voice=1, verse=1)
        notes = _notes_in(twinkle, part=1)
        for n in notes:
            verses = {ly.number for ly in n.lyrics}
            assert 1 not in verses
