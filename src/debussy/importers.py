"""Import other formats into MusicXML.

- `import_file`: use music21 to parse MIDI, ABC, Humdrum/kern, MEI, etc.,
  and write out a MusicXML file.
- `transcribe_audio`: optional, requires `pip install debussy[transcribe]`
  to get Spotify's `basic-pitch`. Produces a MIDI file, then converts to
  MusicXML.
"""

from __future__ import annotations

from pathlib import Path

from debussy.score_io import load, save


_KNOWN_EXT = {
    ".mid": "midi",
    ".midi": "midi",
    ".abc": "abc",
    ".krn": "humdrum",
    ".mei": "mei",
    ".musicxml": "musicxml",
    ".xml": "musicxml",
    ".mxl": "musicxml",
}


def import_file(src_path: str, out: str | None = None) -> str:
    """Parse any format music21 understands and write it out as MusicXML."""
    src = Path(src_path)
    if not src.exists():
        raise FileNotFoundError(src)
    kind = _KNOWN_EXT.get(src.suffix.lower())
    if kind is None:
        raise ValueError(
            f"don't know how to import {src.suffix!r}; "
            f"try converting to .mid or .abc first"
        )
    if out is None:
        out = str(src.with_suffix(".musicxml"))
    out_path = Path(out)
    # music21 figures out the format from the extension
    score = load(src)
    save(score, out_path)
    return f"imported {src.name} ({kind}) → {out_path}"


def transcribe_audio(audio_path: str, out: str | None = None) -> str:
    """Audio → MIDI → MusicXML, via Spotify's basic-pitch (optional dep).

    Falls back to a clear install message if basic-pitch isn't available.
    """
    try:
        from basic_pitch.inference import predict_and_save  # type: ignore
        from basic_pitch import ICASSP_2022_MODEL_PATH  # type: ignore
    except Exception:
        return (
            "audio transcription requires the optional `basic-pitch` package.\n"
            "install with: pip install 'debussy[transcribe]'\n"
            "or directly:  pip install basic-pitch\n"
            "(basic-pitch pulls in TensorFlow; ~1 GB)"
        )

    audio = Path(audio_path)
    if not audio.exists():
        raise FileNotFoundError(audio)

    out_path = Path(out) if out else audio.with_suffix(".musicxml")
    tmp_dir = out_path.parent
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # basic-pitch writes a .mid alongside the audio file into an output dir
    predict_and_save(
        [str(audio)],
        str(tmp_dir),
        save_midi=True,
        sonify_midi=False,
        save_model_outputs=False,
        save_notes=False,
        model_or_model_path=ICASSP_2022_MODEL_PATH,
    )
    mid_path = tmp_dir / (audio.stem + "_basic_pitch.mid")
    if not mid_path.exists():
        return f"basic-pitch did not produce {mid_path}"

    # Convert the MIDI to MusicXML via music21
    score = load(mid_path)
    save(score, out_path)
    try:
        mid_path.unlink()
    except Exception:
        pass
    return f"transcribed {audio.name} → {out_path}"
