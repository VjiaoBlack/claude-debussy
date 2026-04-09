"""Music-theoretic analysis: key, chord progression, cadences.

These functions all take a path and return formatted text for Claude.
"""

from __future__ import annotations

from music21 import chord, key, roman, stream

from debussy.score_io import fmt_beat, load


def analyze_key(path: str) -> str:
    """Run key analysis and report the top candidates."""
    score = load(path)
    k = score.analyze("key")
    alts = k.alternateInterpretations[:4] if k.alternateInterpretations else []
    lines = [
        f"# key analysis",
        f"best:  {k.tonic.name} {k.mode}  (corr={k.correlationCoefficient:.3f})",
    ]
    if alts:
        lines.append("alternatives:")
        for a in alts:
            lines.append(
                f"  {a.tonic.name} {a.mode}  (corr={a.correlationCoefficient:.3f})"
            )
    return "\n".join(lines)


def analyze_chords(
    path: str,
    measure_range: tuple[int, int] | None = None,
    beat_resolution: float = 1.0,
) -> str:
    """Chordify the score and report one chord per beat (or per measure).

    beat_resolution=1.0 → per beat; =0.0 → one chord per measure (longest chord)
    """
    score = load(path)
    k = score.analyze("key")
    chordified = score.chordify()

    lines = [f"# chords  key={k.tonic.name} {k.mode}"]
    for m in chordified.getElementsByClass(stream.Measure):
        if m.number is None:
            continue
        if measure_range and not (measure_range[0] <= m.number <= measure_range[1]):
            continue

        mlines: list[str] = [f"m.{m.number}:"]
        if beat_resolution <= 0:
            # Longest chord in the measure
            longest = None
            for c in m.getElementsByClass(chord.Chord):
                if longest is None or c.duration.quarterLength > longest.duration.quarterLength:
                    longest = c
            if longest is not None:
                mlines[0] += f"  {_chord_descr(longest, k)}"
        else:
            for c in m.getElementsByClass(chord.Chord):
                beat = fmt_beat(float(c.offset) + 1)
                mlines.append(f"  {beat}  {_chord_descr(c, k)}")
        lines.extend(mlines)

    return "\n".join(lines)


def _chord_descr(c: chord.Chord, k: key.Key) -> str:
    try:
        rn = roman.romanNumeralFromChord(c, k)
        figure = rn.figure
    except Exception:
        figure = "?"
    pitches = ",".join(p.nameWithOctave.replace("-", "b") for p in c.pitches)
    common = c.pitchedCommonName
    return f"{figure:<6}  {common:<30}  [{pitches}]"


def analyze_progression(path: str) -> str:
    """High-level progression: Roman numeral list, one per measure."""
    score = load(path)
    k = score.analyze("key")
    chordified = score.chordify()

    figures: list[tuple[int, str]] = []
    for m in chordified.getElementsByClass(stream.Measure):
        if m.number is None:
            continue
        longest = None
        for c in m.getElementsByClass(chord.Chord):
            if longest is None or c.duration.quarterLength > longest.duration.quarterLength:
                longest = c
        if longest is None:
            continue
        try:
            rn = roman.romanNumeralFromChord(longest, k)
            figures.append((m.number, rn.figure))
        except Exception:
            figures.append((m.number, "?"))

    lines = [f"# progression  key={k.tonic.name} {k.mode}"]
    # Group 4 measures per line for readability
    row: list[str] = []
    for i, (mnum, fig) in enumerate(figures):
        row.append(f"m{mnum}:{fig}")
        if (i + 1) % 4 == 0:
            lines.append("  " + "  ".join(row))
            row = []
    if row:
        lines.append("  " + "  ".join(row))

    return "\n".join(lines)
