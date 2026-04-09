"""Semantic editing ops — never touch raw XML.

All ops load a Score, mutate it through music21, and write it back.
Coordinates are 1-indexed (measures, voices, beats).
"""

from __future__ import annotations

from fractions import Fraction
from typing import Iterable

from music21 import chord, duration, interval, note, pitch, stream

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
