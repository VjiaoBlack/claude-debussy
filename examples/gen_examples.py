"""Generate example MusicXML fixtures used by docs and tests.

Run:
    python examples/gen_examples.py

This writes:
    examples/twinkle.musicxml        — 2-part nursery-rhyme smoke test
    examples/autumn_leaves.musicxml  — 3-instrument jazz A-section
    examples/barbershop.musicxml     — 4-voice SATB with lyrics on all parts
"""

from pathlib import Path

from music21 import (
    chord,
    clef,
    duration,
    instrument,
    key,
    metadata,
    meter,
    note,
    stream,
    tempo,
)


# ---------------------------------------------------------------------------
# Twinkle — kept as the minimal 2-part smoke test
# ---------------------------------------------------------------------------


def twinkle() -> stream.Score:
    s = stream.Score()
    s.metadata = metadata.Metadata()
    s.metadata.title = "Twinkle Twinkle Little Star"
    s.metadata.composer = "trad."

    mel = stream.Part()
    mel.partName = "Melody"
    mel.insert(0, instrument.Piano())
    mel.append(clef.TrebleClef())
    mel.append(key.Key("C"))
    mel.append(meter.TimeSignature("4/4"))
    mel.append(tempo.MetronomeMark(number=100))
    for name, ql in [
        ("C4", 1), ("C4", 1), ("G4", 1), ("G4", 1),
        ("A4", 1), ("A4", 1), ("G4", 2),
        ("F4", 1), ("F4", 1), ("E4", 1), ("E4", 1),
        ("D4", 1), ("D4", 1), ("C4", 2),
    ]:
        mel.append(note.Note(name, quarterLength=ql))

    bass = stream.Part()
    bass.partName = "Bass"
    bass.insert(0, instrument.Piano())
    bass.append(clef.BassClef())
    bass.append(key.Key("C"))
    bass.append(meter.TimeSignature("4/4"))
    for name, ql in [
        ("C3", 4),
        ("F3", 2), ("C3", 2),
        ("F3", 2), ("C3", 2),
        ("G3", 2), ("C3", 2),
    ]:
        bass.append(note.Note(name, quarterLength=ql))

    s.insert(0, mel)
    s.insert(0, bass)
    s.makeMeasures(inPlace=True)
    return s


# ---------------------------------------------------------------------------
# Autumn Leaves — jazz A section in E minor (Real Book key).
#
# 8 bars, chords:
#   | Am7  | D7   | Gmaj7 | Cmaj7 |
#   | F#m7b5 | B7 | Em    | Em    |
#
# Three parts:
#   1. Flute — the iconic stepwise melody on downbeats
#   2. Piano — block chord comping on beats 1 and 3
#   3. Bass  — walking quarter-note bass line
# ---------------------------------------------------------------------------


_AUTUMN_MELODY = [
    # (pitches_or_rest, ql, beat-offset) — but we just append in order
    # m.1  Am7:  "the falling leaves"
    ("rest", 1), ("E4", 1), ("F4", 1), ("G4", 1),
    # m.2  D7:   "drift by the window"
    ("A4", 2), ("A4", 1), ("A4", 1),
    # m.3  Gmaj7: "the autumn leaves"
    ("rest", 1), ("D4", 1), ("E4", 1), ("F#4", 1),
    # m.4  Cmaj7: "of red and gold"
    ("G4", 2), ("G4", 2),
    # m.5  F#m7b5: "I see your lips"
    ("rest", 1), ("C4", 1), ("D4", 1), ("E4", 1),
    # m.6  B7:     "the summer kisses"
    ("F#4", 2), ("F#4", 1), ("F#4", 1),
    # m.7  Em:     "the sunburned hands"
    ("rest", 1), ("B3", 1), ("C4", 1), ("D4", 1),
    # m.8  Em:     "I used to hold"
    ("E4", 2), ("E4", 2),
]


_AUTUMN_CHORDS = [
    # Piano comps: each tuple is one measure's worth of (chord, ql) pairs.
    # Chord tones chosen for clean voicings in the piano's middle register.
    [(("A3", "C4", "E4", "G4"), 2), (("A3", "C4", "E4", "G4"), 2)],
    [(("D3", "F#3", "A3", "C4"), 2), (("D3", "F#3", "A3", "C4"), 2)],
    [(("G3", "B3", "D4", "F#4"), 2), (("G3", "B3", "D4", "F#4"), 2)],
    [(("C3", "E3", "G3", "B3"), 2), (("C3", "E3", "G3", "B3"), 2)],
    [(("F#3", "A3", "C4", "E4"), 2), (("F#3", "A3", "C4", "E4"), 2)],
    [(("B2", "D#3", "F#3", "A3"), 2), (("B2", "D#3", "F#3", "A3"), 2)],
    [(("E3", "G3", "B3"), 2), (("E3", "G3", "B3"), 2)],
    [(("E3", "G3", "B3"), 2), (("E3", "G3", "B3"), 2)],
]

_AUTUMN_BASS = [
    # Walking quarters — root, approach, root, chromatic leading tone
    ["A2", "E3", "A2", "C3"],   # Am7
    ["D2", "A2", "D3", "F#3"],  # D7
    ["G2", "D3", "G3", "B3"],   # Gmaj7
    ["C3", "G3", "C4", "B3"],   # Cmaj7
    ["F#2", "A2", "C3", "E3"],  # F#m7b5
    ["B2", "F#3", "B3", "A3"],  # B7
    ["E2", "B2", "G3", "B3"],   # Em
    ["E2", "D3", "C3", "B2"],   # Em (descending)
]


def autumn_leaves() -> stream.Score:
    s = stream.Score()
    s.metadata = metadata.Metadata()
    s.metadata.title = "Autumn Leaves (A section)"
    s.metadata.composer = "Joseph Kosma"
    s.metadata.lyricist = "Jacques Prévert / Johnny Mercer"

    # --- Flute melody ---
    flute = stream.Part()
    flute.partName = "Flute"
    flute.insert(0, instrument.Flute())
    flute.append(clef.TrebleClef())
    flute.append(key.Key("e"))  # E minor
    flute.append(meter.TimeSignature("4/4"))
    flute.append(tempo.MetronomeMark(number=96, text="Andante"))
    for tok, ql in _AUTUMN_MELODY:
        if tok == "rest":
            flute.append(note.Rest(quarterLength=ql))
        else:
            flute.append(note.Note(tok, quarterLength=ql))

    # --- Piano comping ---
    piano = stream.Part()
    piano.partName = "Piano"
    piano.insert(0, instrument.Piano())
    piano.append(clef.TrebleClef())
    piano.append(key.Key("e"))
    piano.append(meter.TimeSignature("4/4"))
    for measure in _AUTUMN_CHORDS:
        for pitches, ql in measure:
            c = chord.Chord(list(pitches))
            c.duration = duration.Duration(ql)
            piano.append(c)

    # --- Walking bass ---
    bass = stream.Part()
    bass.partName = "Bass"
    bass.insert(0, instrument.AcousticBass())
    bass.append(clef.BassClef())
    bass.append(key.Key("e"))
    bass.append(meter.TimeSignature("4/4"))
    for measure_bass in _AUTUMN_BASS:
        for pitch_name in measure_bass:
            bass.append(note.Note(pitch_name, quarterLength=1))

    s.insert(0, flute)
    s.insert(0, piano)
    s.insert(0, bass)
    s.makeMeasures(inPlace=True)
    return s


# ---------------------------------------------------------------------------
# Barbershop quartet — 4-part close harmony with lyrics on every voice.
#
# 4 bars of a simple homophonic "Good night, ladies" style cadence in Bb.
# Voicing order from top: Tenor (above lead), Lead (melody), Baritone, Bass.
# All four voices sing the same syllables simultaneously.
# ---------------------------------------------------------------------------


# Each tuple is (tenor, lead, baritone, bass) for one half-note beat.
# 4 bars, 8 half notes, shaping a I - IV - V7 - I cadence with barbershop
# seventh-chord tendencies in bar 3.
_BARBERSHOP_VOICINGS = [
    # m.1 "Good night" — Bb major
    ("F5", "D5", "Bb4", "Bb3"),
    ("F5", "D5", "Bb4", "Bb3"),
    # m.2 "la-dies" — Eb major (IV)
    ("G5", "Eb5", "Bb4", "Eb3"),
    ("G5", "Eb5", "Bb4", "Eb3"),
    # m.3 "we're going to" — F7 (V7)
    ("Eb5", "C5", "A4", "F3"),
    ("Eb5", "C5", "A4", "F3"),
    # m.4 "leave you now" — Bb major (I)
    ("F5", "D5", "Bb4", "Bb3"),
    ("F5", "D5", "Bb4", "Bb3"),
]

_BARBERSHOP_LYRICS_SYLLABLES = [
    # one lyric token per half-note beat (so 8 in total for 4 bars)
    "Good", "night",
    "la-", "dies",
    "we're", "go-",
    "ing", "now",
]


def _append_voice_from_voicings(
    part: stream.Part, voice_index: int, lyric_syllables: list[str]
) -> None:
    """Append a single voice line: half notes from _BARBERSHOP_VOICINGS."""
    for (voicing, syl) in zip(_BARBERSHOP_VOICINGS, lyric_syllables):
        pitch_name = voicing[voice_index]
        n = note.Note(pitch_name, quarterLength=2)
        # Lyric syllabic: "-x" → middle, "x-" → begin, "x" → single, "-x-" → middle
        txt = syl.strip("-")
        if syl.startswith("-") and syl.endswith("-"):
            syllabic = "middle"
        elif syl.startswith("-"):
            syllabic = "end"
        elif syl.endswith("-"):
            syllabic = "begin"
        else:
            syllabic = "single"
        n.lyrics.append(note.Lyric(text=txt, number=1, syllabic=syllabic))
        part.append(n)


def barbershop() -> stream.Score:
    s = stream.Score()
    s.metadata = metadata.Metadata()
    s.metadata.title = "Good Night Ladies (barbershop tag)"
    s.metadata.composer = "trad. (arr. for test fixture)"

    voice_specs = [
        ("Tenor", instrument.Vocalist(), clef.TrebleClef(), 0),
        ("Lead", instrument.Vocalist(), clef.TrebleClef(), 1),
        ("Baritone", instrument.Vocalist(), clef.Treble8vbClef(), 2),
        ("Bass", instrument.Vocalist(), clef.BassClef(), 3),
    ]

    for name, instr, cl, voice_idx in voice_specs:
        p = stream.Part()
        p.partName = name
        p.insert(0, instr)
        p.append(cl)
        p.append(key.Key("Bb"))
        p.append(meter.TimeSignature("4/4"))
        if name == "Tenor":  # only need the tempo on the top part
            p.append(tempo.MetronomeMark(number=72, text="Slowly"))
        _append_voice_from_voicings(p, voice_idx, _BARBERSHOP_LYRICS_SYLLABLES)
        s.insert(0, p)

    s.makeMeasures(inPlace=True)
    return s


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    here = Path(__file__).parent
    for name, builder in [
        ("twinkle", twinkle),
        ("autumn_leaves", autumn_leaves),
        ("barbershop", barbershop),
    ]:
        s = builder()
        out = here / f"{name}.musicxml"
        s.write("musicxml", fp=str(out))
        print(f"wrote {out}")
