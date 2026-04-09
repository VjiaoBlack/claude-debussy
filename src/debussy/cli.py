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

    # --- render & preview ---
    p_rn = sub.add_parser("render", help="render to midi / musicxml / pdf / png / lily")
    p_rn.add_argument("file")
    p_rn.add_argument("--format", default="midi",
                      choices=["midi", "musicxml", "pdf", "png", "lily"])
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
