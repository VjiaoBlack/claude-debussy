"""Generate example MusicXML fixtures used by docs and tests.

Run:
    python examples/gen_examples.py

This writes:
    examples/twinkle.musicxml         — 2-part nursery-rhyme smoke test
    examples/autumn_leaves.musicxml   — 3-instrument jazz A-section (original)
    examples/barbershop.musicxml      — 4-voice SATB with lyrics on all parts
    examples/bach_chorale.musicxml    — real Bach BWV 66.6 from music21 corpus
    examples/chopin_prelude.musicxml  — original short prelude, dense dynamics
    examples/polyrhythm.musicxml      — 3-against-4 tuplets for duration tests
    examples/pop_ballad.musicxml      — original piano + vocal with lyrics
    examples/multi_voice.musicxml     — 2 staves × 2 voices (keyboard SATB)
    examples/structure_demo.musicxml  — AABA form with rehearsal marks,
                                        repeats, 1st/2nd endings, Segno,
                                        Coda, D.C., Fine, key/time changes
"""

from fractions import Fraction
from pathlib import Path

from music21 import (
    bar,
    chord,
    clef,
    corpus,
    duration,
    dynamics,
    expressions,
    instrument,
    key,
    metadata,
    meter,
    note,
    repeat,
    spanner,
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
# Bach chorale — real BWV 66.6 pulled straight from music21's corpus.
#
# Bach died in 1750 so everything is squarely public domain. Using a real
# chorale gives the test suite authentic SATB voice leading, figured-bass
# style cadences, and music21's rich metadata — all things synthetic
# fixtures don't really exercise.
# ---------------------------------------------------------------------------


def bach_chorale() -> stream.Score:
    s = corpus.parse("bach/bwv66.6")
    # Normalise metadata for the test suite to assert against.
    if s.metadata is None:
        s.metadata = metadata.Metadata()
    s.metadata.title = "Chorale BWV 66.6 (Christ unser Herr zum Jordan kam)"
    s.metadata.composer = "J. S. Bach"
    return s


# ---------------------------------------------------------------------------
# Chopin-style prelude — original 8-bar E-minor piece in the *style* of
# Op.28 No.4. Dense dynamics and articulation so the vibe-edit tests have
# something realistic to render. Not a copy of the Chopin; original
# material so there's no copyright anywhere in this repo.
# ---------------------------------------------------------------------------


def chopin_prelude() -> stream.Score:
    s = stream.Score()
    s.metadata = metadata.Metadata()
    s.metadata.title = "Prélude (in the style of Op.28 No.4)"
    s.metadata.composer = "original, for test fixture"

    # --- Right hand: sustained melody in whole and half notes ---
    rh = stream.Part()
    rh.partName = "Piano RH"
    rh.insert(0, instrument.Piano())
    rh.append(clef.TrebleClef())
    rh.append(key.Key("e"))
    rh.append(meter.TimeSignature("2/2"))
    rh.append(tempo.MetronomeMark(number=54, text="Largo"))

    rh_notes = [
        # m.1–2: sustained B4 — the lament
        ("B4", 4),
        ("B4", 4),
        # m.3: B4 → C5 sigh
        ("B4", 2), ("C5", 2),
        # m.4: B4 half → A4 half (descending)
        ("B4", 2), ("A4", 2),
        # m.5: A4 sustained whole
        ("A4", 4),
        # m.6: A4 → G4
        ("A4", 2), ("G4", 2),
        # m.7: F#4 → E4 resolution
        ("F#4", 2), ("E4", 2),
        # m.8: E4 final whole
        ("E4", 4),
    ]
    for name, ql in rh_notes:
        rh.append(note.Note(name, quarterLength=ql))

    # --- Left hand: repeating eighth-note chords, chromatic descent ---
    lh = stream.Part()
    lh.partName = "Piano LH"
    lh.insert(0, instrument.Piano())
    lh.append(clef.BassClef())
    lh.append(key.Key("e"))
    lh.append(meter.TimeSignature("2/2"))

    # Each bar is 4 quarters = 8 eighths. We use four repeated chord hits
    # per bar (quarter notes) for simplicity but one moves chromatically.
    chords_per_bar = [
        ("E3", "G3", "B3"),     # m.1  Em
        ("E3", "G3", "B3"),     # m.2  Em
        ("E3", "G3", "Bb3"),    # m.3  Em(b5)
        ("E3", "F#3", "A3"),    # m.4  passing
        ("D3", "F#3", "A3"),    # m.5  D  (V/V?)
        ("D3", "F3", "A3"),     # m.6  Dm (passing)
        ("C3", "E3", "G3"),     # m.7  C  (VI)
        ("B2", "E3", "G3"),     # m.8  B (V)
    ]
    for voicing in chords_per_bar:
        for _ in range(4):
            c = chord.Chord(list(voicing))
            c.duration = duration.Duration(1)  # quarter
            lh.append(c)

    s.insert(0, rh)
    s.insert(0, lh)
    s.makeMeasures(inPlace=True)

    # Sprinkle dynamics and expressive text to exercise vibe-edit tests.
    first_rh_measure = rh.getElementsByClass(stream.Measure).first()
    if first_rh_measure is not None:
        first_rh_measure.insert(0, dynamics.Dynamic("p"))
        first_rh_measure.insert(0, expressions.TextExpression("dolente"))
    mid_rh_measure = rh.getElementsByClass(stream.Measure)[3]
    mid_rh_measure.insert(0, dynamics.Dynamic("mf"))
    mid_rh_measure.insert(0, expressions.TextExpression("cresc."))
    last_rh_measure = rh.getElementsByClass(stream.Measure).last()
    last_rh_measure.insert(0, dynamics.Dynamic("pp"))
    last_rh_measure.insert(0, expressions.TextExpression("morendo"))

    return s


# ---------------------------------------------------------------------------
# Polyrhythm fixture — 3-against-4 cross rhythm. Purpose: exercise the
# tuplet handling in score_io.fmt_duration and the digest output.
#
# Right hand plays 4 straight quarter notes per bar. Left hand plays 3
# half-note triplets per bar (each = 4/3 quarterLengths, auto-tupleted
# by music21). Bar 3 adds eighth-note triplets in the RH for variety.
# ---------------------------------------------------------------------------


def polyrhythm() -> stream.Score:
    s = stream.Score()
    s.metadata = metadata.Metadata()
    s.metadata.title = "3-against-4 Polyrhythm Study"
    s.metadata.composer = "original, for test fixture"

    rh = stream.Part()
    rh.partName = "RH"
    rh.insert(0, instrument.Piano())
    rh.append(clef.TrebleClef())
    rh.append(key.Key("C"))
    rh.append(meter.TimeSignature("4/4"))
    rh.append(tempo.MetronomeMark(number=80))

    lh = stream.Part()
    lh.partName = "LH"
    lh.insert(0, instrument.Piano())
    lh.append(clef.BassClef())
    lh.append(key.Key("C"))
    lh.append(meter.TimeSignature("4/4"))

    # m.1 — straight 4 quarters vs. 3 half-note triplets
    for p in ("C5", "D5", "E5", "F5"):
        rh.append(note.Note(p, quarterLength=1))
    for p in ("C3", "E3", "G3"):
        lh.append(note.Note(p, quarterLength=Fraction(4, 3)))

    # m.2 — same idea, higher
    for p in ("G5", "F5", "E5", "D5"):
        rh.append(note.Note(p, quarterLength=1))
    for p in ("G3", "E3", "C3"):
        lh.append(note.Note(p, quarterLength=Fraction(4, 3)))

    # m.3 — eighth-note triplets in RH (9 per bar = 3 groups of 3), straight
    # quarters in LH so tuplets appear in BOTH voices and both directions.
    triplet_pitches = ["C5", "D5", "E5"] * 4  # 12 notes to fill whole bar
    # Each eighth triplet = 1/3 quarter. 12 notes × 1/3 = 4 quarters.
    for p in triplet_pitches:
        rh.append(note.Note(p, quarterLength=Fraction(1, 3)))
    for p in ("C3", "E3", "G3", "C4"):
        lh.append(note.Note(p, quarterLength=1))

    # m.4 — resolve: whole note vs. half notes
    rh.append(note.Note("C5", quarterLength=4))
    lh.append(note.Note("C3", quarterLength=2))
    lh.append(note.Note("G2", quarterLength=2))

    s.insert(0, rh)
    s.insert(0, lh)
    s.makeMeasures(inPlace=True)
    return s


# ---------------------------------------------------------------------------
# Pop ballad fixture — original 8-bar piano + vocal, I-V-vi-IV in C major.
# The staple "four-chord" pop progression. Vocal carries syllabic lyrics
# across two phrases so the lyrics + multi-part + chord tests all have
# something realistic to check.
# ---------------------------------------------------------------------------


_POP_CHORDS_PER_BAR = [
    # (bass_root, triad_voicing_above, roman)
    ("C3", ("C4", "E4", "G4"), "I"),     # C
    ("G2", ("B3", "D4", "G4"), "V"),     # G
    ("A2", ("C4", "E4", "A4"), "vi"),    # Am
    ("F2", ("A3", "C4", "F4"), "IV"),    # F
    ("C3", ("C4", "E4", "G4"), "I"),     # C
    ("G2", ("B3", "D4", "G4"), "V"),     # G
    ("A2", ("C4", "E4", "A4"), "vi"),    # Am
    ("F2", ("A3", "C4", "F4"), "IV"),    # F
]

# One melody line per bar: 4 quarters, chord-tone based, mostly stepwise.
_POP_MELODY = [
    # m.1 "When the night"
    [("E4", 1), ("G4", 1), ("G4", 1), ("E4", 1)],
    # m.2 "comes a-round"
    [("D4", 1), ("G4", 1), ("G4", 1), ("F4", 1)],
    # m.3 "and the stars"
    [("E4", 1), ("A4", 1), ("A4", 1), ("G4", 1)],
    # m.4 "shine so bright"
    [("F4", 1), ("A4", 1), ("G4", 1), ("F4", 1)],
    # m.5 "I'll be home"
    [("E4", 1), ("G4", 1), ("G4", 1), ("E4", 1)],
    # m.6 "think-ing of"
    [("D4", 1), ("G4", 1), ("G4", 1), ("F4", 1)],
    # m.7 "all the times"
    [("E4", 1), ("A4", 1), ("A4", 1), ("G4", 1)],
    # m.8 "we had a-lone"
    [("F4", 1), ("E4", 1), ("D4", 1), ("C4", 1)],
]

# Hyphen grammar matches debussy's lyric parser: "word-part" splits syllables.
# Exactly 32 syllables — one per quarter note across 8 bars of 4/4.
_POP_LYRICS = (
    "When the night comes "       # m.1  (4)
    "a-round I am "                # m.2  (4)
    "think-ing of you "            # m.3  (4)
    "so far a-way "                # m.4  (4)
    "I'll be right here "          # m.5  (4)
    "wait-ing for the "            # m.6  (4)
    "mor-ning light to "           # m.7  (4)
    "bring you back home"          # m.8  (4)
)


def pop_ballad() -> stream.Score:
    s = stream.Score()
    s.metadata = metadata.Metadata()
    s.metadata.title = "Four-Chord Ballad"
    s.metadata.composer = "original, for test fixture"

    # --- Vocal line ---
    vocal = stream.Part()
    vocal.partName = "Vocal"
    vocal.insert(0, instrument.Vocalist())
    vocal.append(clef.TrebleClef())
    vocal.append(key.Key("C"))
    vocal.append(meter.TimeSignature("4/4"))
    vocal.append(tempo.MetronomeMark(number=78, text="Gently"))

    for bar in _POP_MELODY:
        for pitch_name, ql in bar:
            vocal.append(note.Note(pitch_name, quarterLength=ql))

    # --- Piano: RH triads on beats 1 & 3, LH bass on downbeat ---
    piano_rh = stream.Part()
    piano_rh.partName = "Piano RH"
    piano_rh.insert(0, instrument.Piano())
    piano_rh.append(clef.TrebleClef())
    piano_rh.append(key.Key("C"))
    piano_rh.append(meter.TimeSignature("4/4"))

    piano_lh = stream.Part()
    piano_lh.partName = "Piano LH"
    piano_lh.insert(0, instrument.Piano())
    piano_lh.append(clef.BassClef())
    piano_lh.append(key.Key("C"))
    piano_lh.append(meter.TimeSignature("4/4"))

    for bass_root, voicing, _roman in _POP_CHORDS_PER_BAR:
        # RH: chord on beat 1 (half note), same chord on beat 3 (half note)
        for _ in range(2):
            c = chord.Chord(list(voicing))
            c.duration = duration.Duration(2)  # half note
            piano_rh.append(c)
        # LH: root on beat 1 (whole note)
        piano_lh.append(note.Note(bass_root, quarterLength=4))

    s.insert(0, vocal)
    s.insert(0, piano_rh)
    s.insert(0, piano_lh)
    s.makeMeasures(inPlace=True)

    # Attach lyrics to the vocal part using the same grammar as the CLI op
    from debussy.ops import _split_lyric
    syllables = _split_lyric(_POP_LYRICS)
    vocal_notes = [
        n for n in vocal.recurse().notesAndRests if isinstance(n, note.Note)
    ]
    for n, (syl, syllabic) in zip(vocal_notes, syllables):
        if not syl and syllabic == "middle":
            continue
        n.lyrics.append(note.Lyric(text=syl, number=1, syllabic=syllabic))

    # Dynamic swell for texture
    first_vocal_measure = vocal.getElementsByClass(stream.Measure).first()
    if first_vocal_measure is not None:
        first_vocal_measure.insert(0, dynamics.Dynamic("mp"))
    mid_vocal_measure = vocal.getElementsByClass(stream.Measure)[4]
    mid_vocal_measure.insert(0, dynamics.Dynamic("mf"))

    return s


# ---------------------------------------------------------------------------
# Multi-voice-per-staff — keyboard SATB reduction.
#
# Two staves (treble + bass), each containing two explicit voices.
# Treble: Soprano = voice 1, Alto = voice 2
# Bass:   Tenor   = voice 1, Bass = voice 2
#
# This is the "music21 stream.Voice inside stream.Measure" path that
# `stream.Part`-per-instrument scores never exercise. It's also how
# keyboard music is typically notated in real publications.
# ---------------------------------------------------------------------------

# (soprano, alto, tenor, bass) whole-note chord per measure — classic I-IV-V-I
_SATB_PLAGAL = [
    ("E5", "C5", "G4", "C3"),   # m.1  I   (C major)
    ("F5", "C5", "A4", "F3"),   # m.2  IV  (F major)
    ("D5", "B4", "G4", "G3"),   # m.3  V   (G major)
    ("E5", "C5", "G4", "C3"),   # m.4  I   (C major)
]


def _make_staff(
    part_name: str,
    clef_obj,
    upper_pitches: list[str],
    lower_pitches: list[str],
) -> stream.Part:
    """Build one staff that contains two explicit voices per measure."""
    p = stream.Part()
    p.partName = part_name
    p.insert(0, instrument.Piano())
    p.insert(0, clef_obj)
    p.insert(0, key.Key("C"))
    p.insert(0, meter.TimeSignature("4/4"))

    for i, (upper, lower) in enumerate(zip(upper_pitches, lower_pitches), start=1):
        m = stream.Measure(number=i)
        v1 = stream.Voice()
        v1.id = "1"
        v1.append(note.Note(upper, quarterLength=4))
        v2 = stream.Voice()
        v2.id = "2"
        v2.append(note.Note(lower, quarterLength=4))
        m.insert(0, v1)
        m.insert(0, v2)
        p.append(m)

    return p


def multi_voice() -> stream.Score:
    s = stream.Score()
    s.metadata = metadata.Metadata()
    s.metadata.title = "SATB Keyboard Reduction (plagal cadence)"
    s.metadata.composer = "original, for test fixture"

    sopranos = [v[0] for v in _SATB_PLAGAL]
    altos    = [v[1] for v in _SATB_PLAGAL]
    tenors   = [v[2] for v in _SATB_PLAGAL]
    basses   = [v[3] for v in _SATB_PLAGAL]

    treble = _make_staff("Treble", clef.TrebleClef(), sopranos, altos)
    # Put a tempo mark only on the top staff (standard engraving convention)
    first_treble_measure = treble.getElementsByClass(stream.Measure).first()
    first_treble_measure.insert(0, tempo.MetronomeMark(number=60, text="Adagio"))

    bass_staff = _make_staff("Bass", clef.BassClef(), tenors, basses)

    s.insert(0, treble)
    s.insert(0, bass_staff)
    return s


# ---------------------------------------------------------------------------
# Structure demo — 12-bar AABA-ish form exercising every code path in the
# `debussy structure` view. Single part for simplicity.
#
# m.1   ||: whole note  (Rehearsal A, repeat-start)
# m.2       whole note
# m.3       whole note
# m.4   [1. whole note  :||   (repeat-end, first ending)
# m.5   [2. whole note        (second ending)
# m.6       whole note  (Rehearsal B, key change G, tempo Allegro 132)
# m.7       whole note
# m.8       whole note  (Segno)
# m.9       whole note  (time change 3/4, Rehearsal C)
# m.10      whole note  (tempo rit.)
# m.11      whole note  (Coda sign, D.S. al Coda expression)
# m.12      whole note  (Fine, final barline)
# ---------------------------------------------------------------------------


def structure_demo() -> stream.Score:
    s = stream.Score()
    s.metadata = metadata.Metadata()
    s.metadata.title = "Structure Demo (AABA with all markings)"
    s.metadata.composer = "original, for test fixture"

    p = stream.Part()
    p.partName = "Melody"
    p.insert(0, instrument.Piano())
    p.insert(0, clef.TrebleClef())
    p.insert(0, key.Key("C"))
    p.insert(0, meter.TimeSignature("4/4"))
    p.insert(0, tempo.MetronomeMark(number=72, text="Andante"))

    # 12 measures of whole notes (pitch just climbs a C major scale)
    pitches = ["C5", "D5", "E5", "F5", "G5", "A5",
               "B5", "C6", "B5", "A5", "G5", "C5"]
    measures: list[stream.Measure] = []
    for i, pitch_name in enumerate(pitches, start=1):
        m = stream.Measure(number=i)
        m.append(note.Note(pitch_name, quarterLength=4))
        p.append(m)
        measures.append(m)

    # Rehearsal marks
    measures[0].insert(0, expressions.RehearsalMark("A"))
    measures[5].insert(0, expressions.RehearsalMark("B"))
    measures[8].insert(0, expressions.RehearsalMark("C"))

    # Repeat bars
    measures[0].leftBarline = bar.Repeat(direction="start")
    measures[3].rightBarline = bar.Repeat(direction="end", times=2)

    # First / second ending brackets
    rb1 = spanner.RepeatBracket([measures[3]], number=1)
    rb2 = spanner.RepeatBracket([measures[4]], number=2)
    p.insert(0, rb1)
    p.insert(0, rb2)

    # Mid-piece modulation: G major from m.6 onward
    measures[5].insert(0, key.KeySignature(1))  # one sharp = G major
    measures[5].insert(0, tempo.MetronomeMark(number=132, text="Allegro"))

    # Segno on m.8
    measures[7].insert(0, repeat.Segno())

    # Time signature change in m.9
    measures[8].insert(0, meter.TimeSignature("3/4"))
    # (we keep the whole-note as 3-beat in 3/4 — it becomes a dotted half
    #  on write; that's fine, the content of the measure isn't what we test)
    measures[8].notes[0].duration = duration.Duration(3)

    measures[9].insert(0, expressions.TextExpression("rit."))
    measures[9].notes[0].duration = duration.Duration(3)

    # Coda sign + D.S. al Coda expression at m.11
    measures[10].insert(0, repeat.Coda())
    measures[10].notes[0].duration = duration.Duration(3)
    measures[10].insert(3, repeat.DalSegno())

    # Fine + final barline on m.12
    measures[11].notes[0].duration = duration.Duration(3)
    measures[11].insert(0, repeat.Fine())
    measures[11].rightBarline = bar.Barline("final")

    s.insert(0, p)
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
        ("bach_chorale", bach_chorale),
        ("chopin_prelude", chopin_prelude),
        ("polyrhythm", polyrhythm),
        ("pop_ballad", pop_ballad),
        ("multi_voice", multi_voice),
        ("structure_demo", structure_demo),
    ]:
        s = builder()
        out = here / f"{name}.musicxml"
        s.write("musicxml", fp=str(out))
        print(f"wrote {out}")
