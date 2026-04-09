"""Command-line interface — the surface that Claude Code calls."""

from __future__ import annotations

import argparse
import sys
import traceback


def _measure_range(s: str) -> tuple[int, int]:
    if "-" in s:
        lo, hi = s.split("-", 1)
        return (int(lo), int(hi))
    n = int(s)
    return (n, n)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="debussy",
        description=(
            "Agentic harness for reading, reasoning about, editing, and previewing "
            "MusicXML scores. Designed for Claude Code to drive. Hides raw XML."
        ),
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # --- views ---
    p_info = sub.add_parser("info", help="high-level metadata about a score")
    p_info.add_argument("file")

    p_dig = sub.add_parser("digest", help="compact per-measure note listing")
    p_dig.add_argument("file")
    p_dig.add_argument("--measures", type=_measure_range, default=None,
                       help="measure range, e.g. 1-8 or 3")
    p_dig.add_argument("--part", type=int, default=None,
                       help="1-indexed part to show (default: all)")

    p_struct = sub.add_parser("structure", help="rehearsal marks, repeats, form")
    p_struct.add_argument("file")

    # --- analysis ---
    p_key = sub.add_parser("key", help="detect key with confidence + alternates")
    p_key.add_argument("file")

    p_ch = sub.add_parser("chords", help="chord-by-chord Roman numeral analysis")
    p_ch.add_argument("file")
    p_ch.add_argument("--measures", type=_measure_range, default=None)
    p_ch.add_argument("--per-measure", action="store_true",
                      help="collapse to one chord per measure")

    p_prog = sub.add_parser("progression", help="one-line Roman numeral progression")
    p_prog.add_argument("file")

    # --- edit ops ---
    p_sn = sub.add_parser("set-note", help="change pitch at a specific beat")
    p_sn.add_argument("file")
    p_sn.add_argument("--measure", type=int, required=True)
    p_sn.add_argument("--beat", type=float, required=True)
    p_sn.add_argument("--pitch", required=True,
                      help="pitch like C4, F#5, Bb3")
    p_sn.add_argument("--part", type=int, default=1)
    p_sn.add_argument("--voice", type=int, default=1)
    p_sn.add_argument("--out", default=None,
                      help="write to a different file (default: in place)")

    p_sr = sub.add_parser("set-rest", help="convert a note at a beat into a rest")
    p_sr.add_argument("file")
    p_sr.add_argument("--measure", type=int, required=True)
    p_sr.add_argument("--beat", type=float, required=True)
    p_sr.add_argument("--part", type=int, default=1)
    p_sr.add_argument("--voice", type=int, default=1)
    p_sr.add_argument("--out", default=None)

    p_tr = sub.add_parser("transpose", help="transpose by interval (e.g. M3, -P5)")
    p_tr.add_argument("file")
    p_tr.add_argument("--interval", required=True)
    p_tr.add_argument("--measures", type=_measure_range, default=None)
    p_tr.add_argument("--part", type=int, default=None)
    p_tr.add_argument("--out", default=None)

    p_rm = sub.add_parser("replace-measure", help="rewrite a measure/voice from a spec")
    p_rm.add_argument("file")
    p_rm.add_argument("--measure", type=int, required=True)
    p_rm.add_argument("--spec", required=True,
                      help='tokens like "C4/q E4/q G4/q [C4,E4,G4]/h R/e"')
    p_rm.add_argument("--part", type=int, default=1)
    p_rm.add_argument("--voice", type=int, default=1)
    p_rm.add_argument("--out", default=None)

    p_im = sub.add_parser("insert-measure", help="insert an empty measure after N")
    p_im.add_argument("file")
    p_im.add_argument("--after", type=int, required=True)
    p_im.add_argument("--out", default=None)

    p_dm = sub.add_parser("delete-measures", help="delete a range of measures")
    p_dm.add_argument("file")
    p_dm.add_argument("--range", dest="measures", type=_measure_range, required=True)
    p_dm.add_argument("--out", default=None)

    p_ap = sub.add_parser("apply", help="run a music21 python snippet against the score")
    p_ap.add_argument("file")
    p_ap.add_argument("script")
    p_ap.add_argument("--out", default=None)

    # --- vibe edits ---
    p_dyn = sub.add_parser("dynamic", help="add a dynamic marking (p, mf, ff, …)")
    p_dyn.add_argument("file")
    p_dyn.add_argument("--measure", type=int, required=True)
    p_dyn.add_argument("--beat", type=float, default=1.0)
    p_dyn.add_argument("--marking", required=True,
                       help="e.g. pp, p, mf, f, ff, sfz")
    p_dyn.add_argument("--part", type=int, default=1)
    p_dyn.add_argument("--out", default=None)

    p_art = sub.add_parser("articulation", help="add staccato / accent / tenuto / fermata …")
    p_art.add_argument("file")
    p_art.add_argument("--measure", type=int, required=True)
    p_art.add_argument("--beat", type=float, required=True)
    p_art.add_argument("--kind", required=True,
                       help="staccato, accent, tenuto, marcato, fermata, staccatissimo, stress, detachedlegato")
    p_art.add_argument("--part", type=int, default=1)
    p_art.add_argument("--voice", type=int, default=1)
    p_art.add_argument("--out", default=None)

    p_tempo = sub.add_parser("tempo", help="set a tempo / metronome marking")
    p_tempo.add_argument("file")
    p_tempo.add_argument("--measure", type=int, required=True)
    p_tempo.add_argument("--beat", type=float, default=1.0)
    p_tempo.add_argument("--bpm", type=float, default=None)
    p_tempo.add_argument("--text", default=None,
                         help='e.g. "Andante", "Allegro", "rit."')
    p_tempo.add_argument("--out", default=None)

    p_text = sub.add_parser("text", help="add a text expression (rit., dolce, espr. …)")
    p_text.add_argument("file")
    p_text.add_argument("--measure", type=int, required=True)
    p_text.add_argument("--beat", type=float, default=1.0)
    p_text.add_argument("--text", required=True)
    p_text.add_argument("--part", type=int, default=1)
    p_text.add_argument("--out", default=None)

    p_sl = sub.add_parser("slur", help="add a slur between two notes")
    p_sl.add_argument("file")
    p_sl.add_argument("--from-measure", type=int, required=True, dest="from_measure")
    p_sl.add_argument("--from-beat", type=float, required=True, dest="from_beat")
    p_sl.add_argument("--to-measure", type=int, required=True, dest="to_measure")
    p_sl.add_argument("--to-beat", type=float, required=True, dest="to_beat")
    p_sl.add_argument("--part", type=int, default=1)
    p_sl.add_argument("--voice", type=int, default=1)
    p_sl.add_argument("--out", default=None)

    p_hp = sub.add_parser("hairpin", help="add a crescendo or diminuendo")
    p_hp.add_argument("file")
    p_hp.add_argument("--kind", required=True, help="cresc | dim")
    p_hp.add_argument("--from-measure", type=int, required=True, dest="from_measure")
    p_hp.add_argument("--from-beat", type=float, required=True, dest="from_beat")
    p_hp.add_argument("--to-measure", type=int, required=True, dest="to_measure")
    p_hp.add_argument("--to-beat", type=float, required=True, dest="to_beat")
    p_hp.add_argument("--part", type=int, default=1)
    p_hp.add_argument("--voice", type=int, default=1)
    p_hp.add_argument("--out", default=None)

    # --- lyrics ---
    p_ly = sub.add_parser("lyrics", help="attach lyrics to notes in a measure range")
    p_ly.add_argument("file")
    p_ly.add_argument("--measures", type=_measure_range, required=True)
    p_ly.add_argument("--text", required=True,
                      help='word list; use hyphens to split a word across notes: "Hal-le-lu-jah Twin-kle twin-kle"')
    p_ly.add_argument("--part", type=int, default=1)
    p_ly.add_argument("--voice", type=int, default=1)
    p_ly.add_argument("--verse", type=int, default=1)
    p_ly.add_argument("--out", default=None)

    p_lyc = sub.add_parser("clear-lyrics", help="remove lyrics from a measure range")
    p_lyc.add_argument("file")
    p_lyc.add_argument("--measures", type=_measure_range, required=True)
    p_lyc.add_argument("--part", type=int, default=1)
    p_lyc.add_argument("--voice", type=int, default=1)
    p_lyc.add_argument("--verse", type=int, default=None,
                       help="only clear this verse number (default: all)")
    p_lyc.add_argument("--out", default=None)

    # --- import / transcribe ---
    p_im2 = sub.add_parser("import", help="convert MIDI/ABC/Humdrum/MEI → MusicXML")
    p_im2.add_argument("file")
    p_im2.add_argument("--out", default=None)

    p_tx = sub.add_parser("transcribe", help="transcribe audio (wav/mp3) → MusicXML (optional basic-pitch)")
    p_tx.add_argument("file")
    p_tx.add_argument("--out", default=None)

    # --- render & preview ---
    p_rn = sub.add_parser("render", help="render to midi / musicxml / pdf / png / lily")
    p_rn.add_argument("file")
    p_rn.add_argument("--format", default="midi",
                      choices=["midi", "musicxml", "pdf", "png", "svg", "lily"])
    p_rn.add_argument("--out", default=None)

    p_pv = sub.add_parser("preview", help="live-reload web preview (verovio)")
    p_pv.add_argument("file")
    p_pv.add_argument("--port", type=int, default=8765)
    p_pv.add_argument("--host", default="127.0.0.1")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.cmd == "info":
            from debussy.views import info
            print(info(args.file))

        elif args.cmd == "digest":
            from debussy.views import digest
            print(digest(args.file, measure_range=args.measures, part_index=args.part))

        elif args.cmd == "structure":
            from debussy.views import structure
            print(structure(args.file))

        elif args.cmd == "key":
            from debussy.analyze import analyze_key
            print(analyze_key(args.file))

        elif args.cmd == "chords":
            from debussy.analyze import analyze_chords
            print(analyze_chords(
                args.file,
                measure_range=args.measures,
                beat_resolution=0.0 if args.per_measure else 1.0,
            ))

        elif args.cmd == "progression":
            from debussy.analyze import analyze_progression
            print(analyze_progression(args.file))

        elif args.cmd == "set-note":
            from debussy.ops import set_note
            print(set_note(
                args.file, args.measure, args.beat, args.pitch,
                part=args.part, voice=args.voice, out=args.out,
            ))

        elif args.cmd == "set-rest":
            from debussy.ops import set_rest
            print(set_rest(
                args.file, args.measure, args.beat,
                part=args.part, voice=args.voice, out=args.out,
            ))

        elif args.cmd == "transpose":
            from debussy.ops import transpose
            print(transpose(
                args.file, args.interval,
                measure_range=args.measures, part=args.part, out=args.out,
            ))

        elif args.cmd == "replace-measure":
            from debussy.ops import replace_measure
            print(replace_measure(
                args.file, args.measure, args.spec,
                part=args.part, voice=args.voice, out=args.out,
            ))

        elif args.cmd == "insert-measure":
            from debussy.ops import insert_measure
            print(insert_measure(args.file, after=args.after, out=args.out))

        elif args.cmd == "delete-measures":
            from debussy.ops import delete_measures
            print(delete_measures(args.file, args.measures, out=args.out))

        elif args.cmd == "apply":
            from debussy.ops import apply_script
            print(apply_script(args.file, args.script, out=args.out))

        elif args.cmd == "dynamic":
            from debussy.ops import add_dynamic
            print(add_dynamic(
                args.file, args.measure, args.beat, args.marking,
                part=args.part, out=args.out,
            ))

        elif args.cmd == "articulation":
            from debussy.ops import add_articulation
            print(add_articulation(
                args.file, args.measure, args.beat, args.kind,
                part=args.part, voice=args.voice, out=args.out,
            ))

        elif args.cmd == "tempo":
            from debussy.ops import add_tempo_mark
            print(add_tempo_mark(
                args.file, args.measure,
                bpm=args.bpm, text=args.text, beat=args.beat, out=args.out,
            ))

        elif args.cmd == "text":
            from debussy.ops import add_text_expression
            print(add_text_expression(
                args.file, args.measure, args.beat, args.text,
                part=args.part, out=args.out,
            ))

        elif args.cmd == "slur":
            from debussy.ops import add_slur
            print(add_slur(
                args.file,
                args.from_measure, args.from_beat,
                args.to_measure, args.to_beat,
                part=args.part, voice=args.voice, out=args.out,
            ))

        elif args.cmd == "hairpin":
            from debussy.ops import add_hairpin
            print(add_hairpin(
                args.file, args.kind,
                args.from_measure, args.from_beat,
                args.to_measure, args.to_beat,
                part=args.part, voice=args.voice, out=args.out,
            ))

        elif args.cmd == "lyrics":
            from debussy.ops import set_lyrics
            print(set_lyrics(
                args.file, args.measures, args.text,
                part=args.part, voice=args.voice, verse=args.verse, out=args.out,
            ))

        elif args.cmd == "clear-lyrics":
            from debussy.ops import clear_lyrics
            print(clear_lyrics(
                args.file, args.measures,
                part=args.part, voice=args.voice, verse=args.verse, out=args.out,
            ))

        elif args.cmd == "import":
            from debussy.importers import import_file
            print(import_file(args.file, out=args.out))

        elif args.cmd == "transcribe":
            from debussy.importers import transcribe_audio
            print(transcribe_audio(args.file, out=args.out))

        elif args.cmd == "render":
            from debussy.render import render
            print(render(args.file, fmt=args.format, out=args.out))

        elif args.cmd == "preview":
            from debussy.preview import serve
            serve(args.file, port=args.port, host=args.host)

        else:
            parser.error(f"unknown command {args.cmd}")

    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        if "--trace" in sys.argv or __debug__ and False:
            traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
