"""Read-only 'views' — render a Score into compact text for Claude.

The goal of every view is to give Claude *just enough* information to reason
about the music, without dumping raw MusicXML into context.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Iterable

from music21 import chord, key, meter, note, stream, tempo

from debussy.score_io import fmt_beat, fmt_duration, fmt_pitch, load


# ---------------------------------------------------------------------------
# info: metadata + shape of the score
# ---------------------------------------------------------------------------


def info(path: str) -> str:
    score = load(path)
    md = score.metadata

    title = (md.title if md and md.title else "(untitled)")
    composer = (md.composer if md and md.composer else "(unknown)")

    parts = list(score.parts)
    measures_per_part = [len(p.getElementsByClass(stream.Measure)) for p in parts]
    max_measures = max(measures_per_part) if measures_per_part else 0

    # Key / time / tempo taken from the first measure that declares them
    k = score.analyze("key")
    ts_list = score.flatten().getElementsByClass(meter.TimeSignature)
    tempo_list = score.flatten().getElementsByClass(tempo.MetronomeMark)

    ts = ts_list[0].ratioString if ts_list else "?"
    tmpo = (
        f"♩={tempo_list[0].number}"
        if tempo_list and tempo_list[0].number
        else "(no tempo)"
    )

    lines = [
        f"title:     {title}",
        f"composer:  {composer}",
        f"key:       {k.tonic.name} {k.mode}  (analyzed, corr={k.correlationCoefficient:.2f})",
        f"time:      {ts}",
        f"tempo:     {tmpo}",
        f"parts:     {len(parts)}",
    ]
    for i, p in enumerate(parts, 1):
        name = (p.partName or f"Part {i}").strip()
        instr = p.getInstrument(returnDefault=False)
        instr_name = instr.instrumentName if instr else "?"
        lines.append(
            f"  {i}. {name}  [{instr_name}]  "
            f"measures={len(p.getElementsByClass(stream.Measure))}  "
            f"range={_range_string(p)}"
        )
    lines.append(f"measures:  {max_measures}")
    lines.append(f"duration:  {score.duration.quarterLength:g} quarters")
    return "\n".join(lines)


def _range_string(part: stream.Part) -> str:
    pitches = [
        n.pitch for n in part.recurse().notes if isinstance(n, note.Note)
    ] + [
        p for c in part.recurse().notes if isinstance(c, chord.Chord) for p in c.pitches
    ]
    if not pitches:
        return "(no notes)"
    lo = min(pitches, key=lambda p: p.ps)
    hi = max(pitches, key=lambda p: p.ps)
    return f"{fmt_pitch(lo.nameWithOctave)}–{fmt_pitch(hi.nameWithOctave)}"


# ---------------------------------------------------------------------------
# digest: compact per-measure note listing
# ---------------------------------------------------------------------------


def digest(
    path: str,
    measure_range: tuple[int, int] | None = None,
    part_index: int | None = None,
) -> str:
    """Render measures in a compact inline form.

    Format per measure:
        m.N  [key=... chord=...]
          v1 (PartName): @1 C4/q @2 E4/q @3 [C4,E4,G4]/h
          v2 (PartName): @1 R/h @3 G3/h
    """
    score = load(path)
    parts = list(score.parts)
    if part_index is not None:
        parts = [parts[part_index - 1]]

    # Roman numeral analysis (chordified) gives us a chord-per-measure context.
    analyzed_key = score.analyze("key")
    chordified = score.chordify()
    chord_by_measure: dict[int, str] = {}
    for m in chordified.getElementsByClass(stream.Measure):
        best = None
        for c in m.getElementsByClass(chord.Chord):
            if best is None or c.duration.quarterLength > best.duration.quarterLength:
                best = c
        if best is not None:
            try:
                from music21 import roman
                rn = roman.romanNumeralFromChord(best, analyzed_key)
                chord_by_measure[m.number] = rn.figure
            except Exception:
                chord_by_measure[m.number] = best.pitchedCommonName

    lines: list[str] = [
        f"# digest  key={analyzed_key.tonic.name}{'M' if analyzed_key.mode == 'major' else 'm'}"
    ]

    # Collect measure numbers present
    measure_nums: list[int] = sorted(
        {
            m.number
            for p in parts
            for m in p.getElementsByClass(stream.Measure)
            if m.number is not None
        }
    )
    if measure_range:
        lo, hi = measure_range
        measure_nums = [n for n in measure_nums if lo <= n <= hi]

    for mnum in measure_nums:
        rn = chord_by_measure.get(mnum, "")
        header = f"m.{mnum}"
        if rn:
            header += f"  [{rn}]"
        lines.append(header)
        for pidx, part in enumerate(parts, 1):
            mm = part.measure(mnum)
            if mm is None:
                continue
            pname = (part.partName or f"P{pidx}").strip()
            for vidx, voice_line in enumerate(_measure_voice_lines(mm), 1):
                lines.append(f"  v{vidx} ({pname}): {voice_line}")

    return "\n".join(lines)


def _measure_voice_lines(measure: stream.Measure) -> list[str]:
    """Return one line per Voice in the measure (or a single line if flat)."""
    voices = list(measure.getElementsByClass(stream.Voice))
    if not voices:
        return [_render_elements(measure.notesAndRests)]
    return [_render_elements(v.notesAndRests) for v in voices]


def _render_elements(elements: Iterable) -> str:
    tokens: list[str] = []
    for el in elements:
        beat = fmt_beat(Fraction(el.offset) + 1)  # 1-indexed beats
        dur = fmt_duration(el.duration.quarterLength)
        if isinstance(el, note.Rest):
            tokens.append(f"{beat} R/{dur}")
        elif isinstance(el, note.Note):
            prefix = "~" if el.tie and el.tie.type in ("continue", "stop") else ""
            tokens.append(f"{beat} {prefix}{fmt_pitch(el.nameWithOctave)}/{dur}")
        elif isinstance(el, chord.Chord):
            pitches = ",".join(fmt_pitch(p.nameWithOctave) for p in el.pitches)
            tokens.append(f"{beat} [{pitches}]/{dur}")
        else:
            tokens.append(f"{beat} ?/{dur}")
    return "  ".join(tokens)


# ---------------------------------------------------------------------------
# structure: phrase/repeat/rehearsal mark outline
# ---------------------------------------------------------------------------


def structure(path: str) -> str:
    score = load(path)
    lines = ["# structure"]

    # Rehearsal marks
    from music21 import expressions, repeat
    marks = list(score.flatten().getElementsByClass(expressions.RehearsalMark))
    if marks:
        lines.append("rehearsal marks:")
        for m in marks:
            mm = _measure_of(m)
            lines.append(f"  m.{mm}: {m.content}")

    # Repeats / endings / barlines
    from music21 import bar
    repeats = [b for b in score.flatten().getElementsByClass(bar.Repeat)]
    if repeats:
        lines.append("repeats:")
        for r in repeats:
            mm = _measure_of(r)
            lines.append(f"  m.{mm}: {r.direction}")

    # Tempo changes
    tempi = list(score.flatten().getElementsByClass(tempo.MetronomeMark))
    if tempi:
        lines.append("tempo changes:")
        for t in tempi:
            mm = _measure_of(t)
            num = t.number if t.number else "?"
            lines.append(f"  m.{mm}: {t.text or ''} ♩={num}")

    # Key signatures
    keysigs = list(score.flatten().getElementsByClass(key.KeySignature))
    if keysigs:
        lines.append("key signatures:")
        for k in keysigs:
            mm = _measure_of(k)
            lines.append(f"  m.{mm}: {k.sharps:+d} sharps")

    # Time signatures
    tsigs = list(score.flatten().getElementsByClass(meter.TimeSignature))
    if tsigs:
        lines.append("time signatures:")
        for t in tsigs:
            mm = _measure_of(t)
            lines.append(f"  m.{mm}: {t.ratioString}")

    if len(lines) == 1:
        lines.append("(no structural markings found)")
    return "\n".join(lines)


def _measure_of(el) -> int | str:
    """Walk up the music21 context tree to find the containing measure number."""
    ctx = el.getContextByClass(stream.Measure)
    return ctx.number if ctx and ctx.number is not None else "?"
