"""Generate a couple of tiny MusicXML example files for smoke tests.

Run: python examples/gen_examples.py
"""

from pathlib import Path

from music21 import chord, clef, key, meter, note, stream, tempo


def twinkle() -> stream.Score:
    s = stream.Score()
    s.metadata = None
    from music21 import metadata
    s.metadata = metadata.Metadata()
    s.metadata.title = "Twinkle Twinkle Little Star"
    s.metadata.composer = "trad."

    # Melody
    mel = stream.Part()
    mel.partName = "Melody"
    mel.append(clef.TrebleClef())
    mel.append(key.Key("C"))
    mel.append(meter.TimeSignature("4/4"))
    mel.append(tempo.MetronomeMark(number=100))

    notes = [
        ("C4", 1), ("C4", 1), ("G4", 1), ("G4", 1),
        ("A4", 1), ("A4", 1), ("G4", 2),
        ("F4", 1), ("F4", 1), ("E4", 1), ("E4", 1),
        ("D4", 1), ("D4", 1), ("C4", 2),
    ]
    for name, ql in notes:
        mel.append(note.Note(name, quarterLength=ql))

    # Bass — basic I-IV-V progression
    bass = stream.Part()
    bass.partName = "Bass"
    bass.append(clef.BassClef())
    bass.append(key.Key("C"))
    bass.append(meter.TimeSignature("4/4"))

    bass_notes = [
        ("C3", 4),
        ("F3", 2), ("C3", 2),
        ("F3", 2), ("C3", 2),
        ("G3", 2), ("C3", 2),
    ]
    for name, ql in bass_notes:
        bass.append(note.Note(name, quarterLength=ql))

    s.insert(0, mel)
    s.insert(0, bass)
    s.makeMeasures(inPlace=True)
    return s


if __name__ == "__main__":
    here = Path(__file__).parent
    t = twinkle()
    t.write("musicxml", fp=str(here / "twinkle.musicxml"))
    print("wrote", here / "twinkle.musicxml")
