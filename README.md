# claude-debussy

An agentic harness for Claude Code that lets it work with MusicXML scores at
the level of **music**, not XML — key, chords, progressions, structure, voice
leading — and preview the results live in a browser.

## Why

MusicXML is the lingua franca of notation software (MuseScore, Finale, Sibelius,
Dorico, Logic, Lilypond, etc.), but it is also unbelievably verbose. Asking an
LLM to read or edit it directly is a mistake: raw XML eats context, and
hand-edited XML routinely breaks ties, voice offsets, and part structure.

`claude-debussy` wraps [music21](https://web.mit.edu/music21/) with a CLI
(`debussy`) that exposes two things Claude can drive:

1. **Views** that convert a score into compact, Claude-friendly text — key
   analysis, Roman-numeral progressions, structural outlines, and a custom
   per-measure "digest" format like `m.1 [I] v1 (Sop): @1 C4/q @2 E4/q …`.
2. **Ops** that make semantic edits by `(measure, beat, voice)` — Claude never
   sees or touches the XML.

A [`.claude/skills/debussy/SKILL.md`](.claude/skills/debussy/SKILL.md) tells
Claude Code how and when to use the tool.

## Install

```bash
# from the repo root
pip install -e .
```

This installs the `debussy` command. It pulls in `music21` as its only hard
dependency. Rendering PDFs or PNGs additionally requires `lilypond` or
`musescore` on the PATH, but the built-in browser preview needs nothing extra.

## Quick tour

```bash
# generate a toy score
python examples/gen_examples.py

# metadata and shape
debussy info examples/twinkle.musicxml

# compact per-measure text dump (this is what Claude "reads")
debussy digest examples/twinkle.musicxml --measures 1-4

# music theory
debussy key examples/twinkle.musicxml
debussy chords examples/twinkle.musicxml --per-measure
debussy progression examples/twinkle.musicxml
debussy structure examples/twinkle.musicxml

# semantic edits (in place)
debussy set-note examples/twinkle.musicxml --measure 1 --beat 1 --pitch E4
debussy transpose examples/twinkle.musicxml --interval -P5 --measures 1-2
debussy replace-measure examples/twinkle.musicxml --measure 1 \
  --spec "C4/q E4/q G4/q [C4,E4,G4]/q"

# render
debussy render examples/twinkle.musicxml --format midi --out /tmp/out.mid
debussy render examples/twinkle.musicxml --format musicxml --out /tmp/out.xml

# live preview — open the printed URL in a browser; auto-reloads on edits
debussy preview examples/twinkle.musicxml
```

## The typical Claude session

1. User drops a `.musicxml` file in the project and asks: *"The bridge feels
   too static — can you make the bass move more?"*
2. Claude runs `debussy info` / `digest` / `progression` to understand the
   piece and locate the bridge.
3. Claude tells the user: *"Start `debussy preview score.musicxml` in another
   terminal and open http://127.0.0.1:8765/."*
4. Claude proposes a new bass line in the digest notation.
5. On approval, Claude runs a sequence of `debussy replace-measure` /
   `debussy set-note` ops. Each one updates the file; Verovio in the browser
   re-renders automatically via SSE.
6. Claude runs `debussy digest` on the changed range to verify.

## Commands

### Views

| command | purpose |
|---|---|
| `debussy info FILE` | title, composer, analyzed key, time sig, tempo, parts, ranges, measure count |
| `debussy digest FILE [--measures A-B] [--part N]` | compact per-measure text dump |
| `debussy structure FILE` | rehearsal marks, repeats, tempo/key/time changes |
| `debussy key FILE` | best key + top-4 alternates with correlation scores |
| `debussy chords FILE [--measures A-B] [--per-measure]` | Roman-numeral chord analysis |
| `debussy progression FILE` | one-line Roman-numeral summary |

### Ops

| command | purpose |
|---|---|
| `debussy set-note FILE --measure N --beat B --pitch P [--part P] [--voice V]` | change the pitch at a beat |
| `debussy set-rest FILE --measure N --beat B` | replace a note with a rest |
| `debussy transpose FILE --interval I [--measures A-B] [--part P]` | transpose by music21 interval string (e.g. `M3`, `-P5`) |
| `debussy replace-measure FILE --measure N --spec "…"` | rewrite a measure/voice from a digest-style spec |
| `debussy insert-measure FILE --after N` | insert an empty measure |
| `debussy delete-measures FILE --range A-B` | remove a measure range |
| `debussy apply FILE SCRIPT.py` | run an arbitrary music21 python snippet with `score` in scope — escape hatch for anything the CLI doesn't cover |

### Render & preview

| command | purpose |
|---|---|
| `debussy render FILE --format midi\|musicxml\|pdf\|png\|lily [--out OUT]` | write the score in another format |
| `debussy preview FILE [--port 8765]` | local live-reload preview using Verovio (no install) |

## Digest notation

`debussy digest` output is the compact per-measure format Claude uses to read
and write music. `replace-measure --spec` accepts the same grammar.

```
m.1  [I]
  v1 (Soprano): @1 C4/q  @2 E4/q  @3 G4/q  @4 C5/q
  v1 (Bass):    @1 C3/h  @3 G3/h
```

| token | meaning |
|---|---|
| `m.N [Figure]` | measure number + Roman-numeral chord figure |
| `vK (Name)` | voice K of the named part |
| `@B` | beat position, 1-indexed |
| `C4`, `F#5`, `Bb3` | scientific pitch notation (`#` sharp, `b` flat) |
| `q`, `h`, `w`, `e`, `s`, `t` | quarter, half, whole, 8th, 16th, 32nd |
| `q.`, `h..` | dotted durations |
| `q3`, `e5`, `q7` | triplet / quintuplet / septuplet |
| `[C4,E4,G4]/q` | simultaneous chord |
| `R/q` | rest |
| `~C4/q` | continued tied note |

## Repository layout

```
claude-debussy/
├── .claude/
│   └── skills/debussy/SKILL.md     # how Claude Code should use this tool
├── src/debussy/
│   ├── cli.py          # argparse dispatcher
│   ├── score_io.py     # load / save + digest formatting primitives
│   ├── views.py        # info / digest / structure
│   ├── analyze.py      # key / chords / progression
│   ├── ops.py          # set-note, transpose, replace-measure, …
│   ├── render.py       # midi / musicxml / pdf (via lilypond or musescore)
│   └── preview.py      # stdlib HTTP + SSE + Verovio live-reload server
├── examples/
│   ├── gen_examples.py  # writes twinkle.musicxml
│   └── twinkle.musicxml
└── pyproject.toml
```

## Design notes

- **XML is never in Claude's context.** Views are the only way to read; ops are
  the only way to write. This keeps context small and prevents XML corruption.
- **1-indexed coordinates.** Measures, beats, voices, parts are all 1-indexed
  to match how musicians talk about them.
- **music21 underneath.** Every view and op delegates to music21, which has
  robust key detection, Roman-numeral analysis, and MusicXML I/O.
- **Verovio for preview.** The preview server is pure Python stdlib; the
  browser loads Verovio from CDN, so the only runtime dep is `music21`.
- **Escape hatch.** `debussy apply FILE SCRIPT.py` runs an arbitrary music21
  snippet with `score` in scope. Use this for ops the CLI doesn't cover rather
  than extending the CLI speculatively.
