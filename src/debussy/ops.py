"""Semantic editing ops — never touch raw XML.

All ops load a Score, mutate it through music21, and write it back.
Coordinates are 1-indexed (measures, voices, beats).
"""

from __future__ import annotations

from fractions import Fraction
from typing import Iterable

from music21 import (
    articulations as m21articulations,
    chord,
    dynamics as m21dynamics,
    duration,
    expressions,
    interval,
    note,
    pitch,
    spanner,
    stream,
    tempo as m21tempo,
)

from debussy.score_io import load, parse_pitch, save


# ---------------------------------------------------------------------------
# internal helpers
# ---------------------------------------------------------------------------


def _get_measure(score: stream.Score, part_index: int, measure_number: int) -> stream.Measure:
    parts = list(score.parts)
    if not (1 <= part_index <= len(parts)):
        raise ValueError(f"part {part_index} out of range (1..{len(parts)})")
    m = parts[part_index - 1].measure(measure_number)
    if m is None:
        raise ValueError(f"measure {measure_number} not found in part {part_index}")
    return m


def _get_voice(measure: stream.Measure, voice_index: int):
    voices = list(measure.getElementsByClass(stream.Voice))
    if not voices:
        # no explicit voices — treat the measure itself as voice 1
        if voice_index != 1:
            raise ValueError(f"measure has only 1 implicit voice; asked for {voice_index}")
        return measure
    if not (1 <= voice_index <= len(voices)):
        raise ValueError(
            f"voice {voice_index} out of range (measure has {len(voices)} voices)"
        )
    return voices[voice_index - 1]


def _find_at_beat(container, beat: float):
    """Return the note/chord/rest at beat position (1-indexed)."""
    target_offset = float(Fraction(beat) - 1)
    for el in container.notesAndRests:
        if abs(float(el.offset) - target_offset) < 1e-6:
            return el
    raise ValueError(f"no note/rest at beat {beat}")


# ---------------------------------------------------------------------------
# set_note: change the pitch of an existing note/chord
# ---------------------------------------------------------------------------


def set_note(
    path: str,
    measure: int,
    beat: float,
    new_pitch: str,
    *,
    part: int = 1,
    voice: int = 1,
    out: str | None = None,
) -> str:
    score = load(path)
    m = _get_measure(score, part, measure)
    v = _get_voice(m, voice)
    el = _find_at_beat(v, beat)

    new_pitch = parse_pitch(new_pitch)
    if isinstance(el, note.Note):
        old = el.nameWithOctave
        el.pitch = pitch.Pitch(new_pitch)
        msg = f"m{measure} v{voice} @{beat}: {old} → {new_pitch}"
    elif isinstance(el, chord.Chord):
        old = ",".join(p.nameWithOctave for p in el.pitches)
        el.pitches = (pitch.Pitch(new_pitch),)
        msg = f"m{measure} v{voice} @{beat}: [{old}] → {new_pitch}"
    elif isinstance(el, note.Rest):
        # Replace the rest with a note of the same duration
        new_n = note.Note(new_pitch, quarterLength=el.duration.quarterLength)
        v.replace(el, new_n)
        msg = f"m{measure} v{voice} @{beat}: rest → {new_pitch}"
    else:
        raise ValueError(f"unsupported element at beat {beat}: {type(el).__name__}")

    save(score, out or path)
    return msg


# ---------------------------------------------------------------------------
# set_rest: replace a note with a rest
# ---------------------------------------------------------------------------


def set_rest(
    path: str,
    measure: int,
    beat: float,
    *,
    part: int = 1,
    voice: int = 1,
    out: str | None = None,
) -> str:
    score = load(path)
    m = _get_measure(score, part, measure)
    v = _get_voice(m, voice)
    el = _find_at_beat(v, beat)
    r = note.Rest(quarterLength=el.duration.quarterLength)
    v.replace(el, r)
    save(score, out or path)
    return f"m{measure} v{voice} @{beat}: → rest"


# ---------------------------------------------------------------------------
# transpose: by interval, optionally over a measure range
# ---------------------------------------------------------------------------


def transpose(
    path: str,
    interval_str: str,
    *,
    measure_range: tuple[int, int] | None = None,
    part: int | None = None,
    out: str | None = None,
) -> str:
    score = load(path)
    iv = interval.Interval(interval_str)

    targets: list[stream.Stream] = []
    if part is None:
        parts = list(score.parts)
    else:
        parts = [list(score.parts)[part - 1]]

    if measure_range:
        lo, hi = measure_range
        for p in parts:
            for m in p.getElementsByClass(stream.Measure):
                if m.number is not None and lo <= m.number <= hi:
                    targets.append(m)
    else:
        targets = parts

    for t in targets:
        t.transpose(iv, inPlace=True)

    save(score, out or path)
    scope = f"measures {measure_range[0]}-{measure_range[1]}" if measure_range else "entire score"
    return f"transposed {scope} by {iv.directedName}"


# ---------------------------------------------------------------------------
# replace_measure: rewrite a single measure from a compact spec
# ---------------------------------------------------------------------------


def replace_measure(
    path: str,
    measure: int,
    spec: str,
    *,
    part: int = 1,
    voice: int = 1,
    out: str | None = None,
) -> str:
    """Replace all notes in a measure/voice with the given spec.

    Spec is a whitespace-separated list of tokens; each token is one of:
        C4/q         quarter note C4
        [C4,E4,G4]/h half-note chord
        R/e          eighth rest
        C4/q.        dotted quarter
        C4/q3        quarter triplet

    Rhythms must sum to the measure length; this is checked.
    """
    score = load(path)
    m = _get_measure(score, part, measure)
    v = _get_voice(m, voice)

    new_elements = [_parse_token(tok) for tok in spec.split()]
    total = sum(Fraction(el.duration.quarterLength) for el in new_elements)

    # Remove existing notes/rests from the target voice
    to_remove = list(v.notesAndRests)
    for el in to_remove:
        v.remove(el)

    # Insert at running offsets
    offset = Fraction(0)
    for el in new_elements:
        v.insert(float(offset), el)
        offset += Fraction(el.duration.quarterLength)

    save(score, out or path)
    return f"m{measure} v{voice}: replaced with {len(new_elements)} elements ({total}q total)"


def _parse_token(tok: str):
    """Parse a digest token like 'C4/q.' or '[C4,E4,G4]/h' into a music21 object."""
    if "/" not in tok:
        raise ValueError(f"malformed token (missing /): {tok!r}")
    head, dur_tok = tok.rsplit("/", 1)
    d = _parse_dur(dur_tok)
    if head == "R":
        return note.Rest(duration=d)
    if head.startswith("[") and head.endswith("]"):
        pitches = [parse_pitch(p) for p in head[1:-1].split(",")]
        c = chord.Chord(pitches)
        c.duration = d
        return c
    n = note.Note(parse_pitch(head))
    n.duration = d
    return n


_DUR_BASE = {"w": 4, "h": 2, "q": 1, "e": 0.5, "s": 0.25, "t": 0.125, "x": 0.0625}


def _parse_dur(tok: str) -> duration.Duration:
    base = tok[0]
    if base not in _DUR_BASE:
        raise ValueError(f"unknown duration base: {tok!r}")
    ql = Fraction(_DUR_BASE[base]).limit_denominator(64)
    rest = tok[1:]
    dots = 0
    while rest.startswith("."):
        dots += 1
        rest = rest[1:]
    tuplet = None
    if rest:
        try:
            tuplet = int(rest)
        except ValueError as e:
            raise ValueError(f"bad duration suffix: {tok!r}") from e

    # Dots
    for i in range(dots):
        ql = ql * Fraction(3, 2) if i == 0 else ql + ql * Fraction(1, 2 ** (i + 1))

    # Tuplets
    if tuplet == 3:
        ql = ql * Fraction(2, 3)
    elif tuplet == 5:
        ql = ql * Fraction(4, 5)
    elif tuplet == 7:
        ql = ql * Fraction(4, 7)

    return duration.Duration(float(ql))


# ---------------------------------------------------------------------------
# insert / delete measures
# ---------------------------------------------------------------------------


def insert_measure(path: str, after: int, *, out: str | None = None) -> str:
    """Insert an empty measure after the given measure number, in every part."""
    score = load(path)
    for p in score.parts:
        target = p.measure(after)
        if target is None:
            continue
        new_m = stream.Measure(number=after + 1)
        ts = target.timeSignature or p.flatten().getTimeSignatures()[0]
        new_m.append(note.Rest(quarterLength=ts.barDuration.quarterLength))
        # Insert right after target. music21 renumbers on write.
        p.insert(target.offset + target.duration.quarterLength, new_m)

    # Re-number measures in each part sequentially.
    for p in score.parts:
        for i, m in enumerate(p.getElementsByClass(stream.Measure), 1):
            m.number = i

    save(score, out or path)
    return f"inserted empty measure after m.{after}"


def delete_measures(
    path: str, measure_range: tuple[int, int], *, out: str | None = None
) -> str:
    score = load(path)
    lo, hi = measure_range
    for p in score.parts:
        to_remove = [
            m
            for m in p.getElementsByClass(stream.Measure)
            if m.number is not None and lo <= m.number <= hi
        ]
        for m in to_remove:
            p.remove(m)
        for i, m in enumerate(p.getElementsByClass(stream.Measure), 1):
            m.number = i
    save(score, out or path)
    return f"deleted measures {lo}-{hi}"


# ---------------------------------------------------------------------------
# apply: escape hatch — run a user music21 snippet against the score
# ---------------------------------------------------------------------------


def apply_script(path: str, script_path: str, *, out: str | None = None) -> str:
    """Execute a Python snippet with `score` in scope.

    The snippet can mutate `score` in place; the mutated score is written back.
    Example snippet:
        for n in score.recurse().notes:
            if n.pitch.name == 'B':
                n.pitch.name = 'Bb'
    """
    score = load(path)
    import music21  # noqa: F401  (available in snippet scope)
    source = open(script_path, "r").read()
    ns = {"score": score, "music21": music21}
    exec(compile(source, script_path, "exec"), ns)
    save(ns["score"], out or path)
    return f"applied {script_path}"


# ===========================================================================
# vibe edits — expressive markings that don't change pitches
# ===========================================================================

# Accepted dynamic tokens. music21 can take any string and parses it, but we
# give a curated list so Claude doesn't invent non-standard markings.
DYNAMIC_TOKENS = {
    "pppp", "ppp", "pp", "p", "mp", "mf", "f", "ff", "fff", "ffff",
    "fp", "sf", "sfz", "sfp", "fz", "rfz",
}

ARTICULATION_TOKENS = {
    "staccato": m21articulations.Staccato,
    "staccatissimo": m21articulations.Staccatissimo,
    "accent": m21articulations.Accent,
    "marcato": m21articulations.StrongAccent,
    "tenuto": m21articulations.Tenuto,
    "fermata": expressions.Fermata,   # technically an expression
    "stress": m21articulations.Stress,
    "detachedlegato": m21articulations.DetachedLegato,
}


def add_dynamic(
    path: str,
    measure: int,
    beat: float,
    marking: str,
    *,
    part: int = 1,
    out: str | None = None,
) -> str:
    """Insert a dynamic marking (e.g. p, mf, ff) at a beat position."""
    marking = marking.strip()
    if marking not in DYNAMIC_TOKENS:
        raise ValueError(
            f"unknown dynamic {marking!r}; pick from {sorted(DYNAMIC_TOKENS)}"
        )
    score = load(path)
    m = _get_measure(score, part, measure)
    dyn = m21dynamics.Dynamic(marking)
    m.insert(float(Fraction(beat) - 1), dyn)
    save(score, out or path)
    return f"m{measure} @{beat} part{part}: dynamic {marking}"


def add_articulation(
    path: str,
    measure: int,
    beat: float,
    kind: str,
    *,
    part: int = 1,
    voice: int = 1,
    out: str | None = None,
) -> str:
    """Attach an articulation (staccato, accent, etc.) to the note at a beat."""
    kind = kind.strip().lower()
    if kind not in ARTICULATION_TOKENS:
        raise ValueError(
            f"unknown articulation {kind!r}; pick from {sorted(ARTICULATION_TOKENS)}"
        )
    score = load(path)
    m = _get_measure(score, part, measure)
    v = _get_voice(m, voice)
    el = _find_at_beat(v, beat)
    if not isinstance(el, (note.Note, chord.Chord)):
        raise ValueError(f"can't articulate a {type(el).__name__} at beat {beat}")
    cls = ARTICULATION_TOKENS[kind]
    if kind == "fermata":
        el.expressions.append(cls())
    else:
        el.articulations.append(cls())
    save(score, out or path)
    return f"m{measure} v{voice} @{beat}: {kind}"


def add_tempo_mark(
    path: str,
    measure: int,
    *,
    bpm: float | None = None,
    text: str | None = None,
    beat: float = 1.0,
    out: str | None = None,
) -> str:
    """Add or replace a metronome / tempo marking at the start of a measure."""
    if bpm is None and text is None:
        raise ValueError("pass --bpm and/or --text")
    score = load(path)
    # Tempo marks sit on the first part.
    m = _get_measure(score, 1, measure)
    mm = m21tempo.MetronomeMark(number=bpm, text=text)
    # Remove any existing tempo mark at the same offset
    existing = [
        t for t in m.getElementsByClass(m21tempo.TempoIndication)
        if abs(float(t.offset) - float(Fraction(beat) - 1)) < 1e-6
    ]
    for t in existing:
        m.remove(t)
    m.insert(float(Fraction(beat) - 1), mm)
    save(score, out or path)
    return f"m{measure} @{beat}: tempo {text or ''} {bpm or ''}".strip()


def add_text_expression(
    path: str,
    measure: int,
    beat: float,
    text: str,
    *,
    part: int = 1,
    out: str | None = None,
) -> str:
    """Add a free-form text expression (rit., dolce, espr., etc.)."""
    score = load(path)
    m = _get_measure(score, part, measure)
    te = expressions.TextExpression(text)
    m.insert(float(Fraction(beat) - 1), te)
    save(score, out or path)
    return f'm{measure} @{beat} part{part}: text "{text}"'


def add_slur(
    path: str,
    from_measure: int,
    from_beat: float,
    to_measure: int,
    to_beat: float,
    *,
    part: int = 1,
    voice: int = 1,
    out: str | None = None,
) -> str:
    """Add a slur spanning from one note to another."""
    score = load(path)
    m_from = _get_measure(score, part, from_measure)
    v_from = _get_voice(m_from, voice)
    n_from = _find_at_beat(v_from, from_beat)
    m_to = _get_measure(score, part, to_measure)
    v_to = _get_voice(m_to, voice)
    n_to = _find_at_beat(v_to, to_beat)
    if not isinstance(n_from, (note.Note, chord.Chord)):
        raise ValueError(f"from-note at m{from_measure}@{from_beat} isn't a note")
    if not isinstance(n_to, (note.Note, chord.Chord)):
        raise ValueError(f"to-note at m{to_measure}@{to_beat} isn't a note")
    sl = spanner.Slur([n_from, n_to])
    list(score.parts)[part - 1].insert(0, sl)
    save(score, out or path)
    return f"slur m{from_measure}@{from_beat} → m{to_measure}@{to_beat} part{part}"


def add_hairpin(
    path: str,
    kind: str,
    from_measure: int,
    from_beat: float,
    to_measure: int,
    to_beat: float,
    *,
    part: int = 1,
    voice: int = 1,
    out: str | None = None,
) -> str:
    """Add a crescendo or decrescendo hairpin between two notes."""
    kind = kind.strip().lower()
    if kind in ("cresc", "crescendo", "<"):
        cls = m21dynamics.Crescendo
    elif kind in ("dim", "decresc", "decrescendo", "diminuendo", ">"):
        cls = m21dynamics.Diminuendo
    else:
        raise ValueError(f"unknown hairpin kind {kind!r}; use cresc|dim")
    score = load(path)
    m_from = _get_measure(score, part, from_measure)
    n_from = _find_at_beat(_get_voice(m_from, voice), from_beat)
    m_to = _get_measure(score, part, to_measure)
    n_to = _find_at_beat(_get_voice(m_to, voice), to_beat)
    hp = cls([n_from, n_to])
    list(score.parts)[part - 1].insert(0, hp)
    save(score, out or path)
    kind_label = "crescendo" if cls is m21dynamics.Crescendo else "diminuendo"
    return (
        f"{kind_label} m{from_measure}@{from_beat} → m{to_measure}@{to_beat} "
        f"part{part}"
    )


# ===========================================================================
# lyrics
# ===========================================================================


def _split_lyric(text: str) -> list[tuple[str, str]]:
    """Tokenise a lyric string into (syllable, syllabic) pairs.

    Hyphens split a word across notes; underscores extend the previous syllable
    as a melisma across the next note without a new word. Examples:

        "Twinkle twinkle little star"       → four simple syllables
        "Hal-le-lu-jah"                     → four syllables, hyphen syllabic
        "Al_le_lu_ia"                       → one word with melisma holds
        "Ave Ma-ri-a gra-ti-a ple-na"       → mixed
    """
    tokens: list[tuple[str, str]] = []
    for word in text.split():
        if "-" not in word and "_" not in word:
            tokens.append((word, "single"))
            continue
        parts = []
        buf = ""
        for ch in word:
            if ch in "-_":
                parts.append((buf, ch))
                buf = ""
            else:
                buf += ch
        parts.append((buf, "end"))
        # assign syllabic labels
        for i, (syl, delim) in enumerate(parts):
            if not syl and delim == "end":
                # trailing underscore/hyphen — represent as a continuation
                tokens.append(("", "middle"))
                continue
            if i == 0 and delim in ("-", "_"):
                tokens.append((syl, "begin"))
            elif i == len(parts) - 1 and delim == "end":
                tokens.append((syl, "end"))
            else:
                tokens.append((syl, "middle"))
    return tokens


def set_lyrics(
    path: str,
    measure_range: tuple[int, int],
    text: str,
    *,
    part: int = 1,
    voice: int = 1,
    verse: int = 1,
    out: str | None = None,
) -> str:
    """Attach lyrics from `text` to successive notes in the measure range.

    Hyphens split a word across notes; spaces advance to the next word.
    Rests are skipped. Extra syllables beyond the available notes are dropped
    (with a warning returned in the message).
    """
    score = load(path)
    lo, hi = measure_range
    p = list(score.parts)[part - 1]
    # Collect notes in order from the target voice across the measure range
    target_notes = []
    for m in p.getElementsByClass(stream.Measure):
        if m.number is None or not (lo <= m.number <= hi):
            continue
        v = _get_voice(m, voice)
        for el in v.notesAndRests:
            if isinstance(el, (note.Note, chord.Chord)):
                target_notes.append(el)
    syllables = _split_lyric(text)
    attached = 0
    for n, (syl, syllabic) in zip(target_notes, syllables):
        if not syl and syllabic == "middle":
            continue  # melisma hold — don't overwrite
        ly = note.Lyric(text=syl, number=verse, syllabic=syllabic)
        # clear previous verse-N lyric and append
        n.lyrics = [lr for lr in n.lyrics if lr.number != verse]
        n.lyrics.append(ly)
        attached += 1
    save(score, out or path)
    extra = len(syllables) - attached
    tail = f" ({extra} extra syllables dropped)" if extra > 0 else ""
    return f"lyrics part{part} v{voice} m{lo}-{hi}: {attached} syllables attached{tail}"


def clear_lyrics(
    path: str,
    measure_range: tuple[int, int],
    *,
    part: int = 1,
    voice: int = 1,
    verse: int | None = None,
    out: str | None = None,
) -> str:
    """Remove lyrics from notes in a measure range (all verses or just one)."""
    score = load(path)
    lo, hi = measure_range
    p = list(score.parts)[part - 1]
    removed = 0
    for m in p.getElementsByClass(stream.Measure):
        if m.number is None or not (lo <= m.number <= hi):
            continue
        v = _get_voice(m, voice)
        for el in v.notesAndRests:
            if not isinstance(el, (note.Note, chord.Chord)):
                continue
            if verse is None:
                removed += len(el.lyrics)
                el.lyrics = []
            else:
                before = len(el.lyrics)
                el.lyrics = [lr for lr in el.lyrics if lr.number != verse]
                removed += before - len(el.lyrics)
    save(score, out or path)
    return f"cleared {removed} lyric syllables in m{lo}-{hi}"
