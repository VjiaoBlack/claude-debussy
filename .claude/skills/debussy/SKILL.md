---
name: debussy
description: >
  Work with MusicXML scores (.musicxml / .xml / .mxl) — read them, reason about
  them at the level of chords / keys / progressions / structure, make semantic
  edits, and preview the result live in a browser. Use this skill whenever the
  user asks about or wants to modify a music notation file.
---

# debussy — the MusicXML harness

This repo ships a CLI tool `debussy` that wraps [music21](https://web.mit.edu/music21/)
and gives Claude a set of high-level commands for reading, reasoning about, and
editing MusicXML scores. **Always use `debussy` instead of reading or editing
`.musicxml` files directly** — MusicXML is extremely verbose and easy to corrupt
with text edits.

## Golden rules

1. **NEVER `Read` or `Edit` a `.musicxml`, `.xml`, or `.mxl` file directly.**
   They are huge and mutating them by hand will break offsets, ties, voices,
   etc. Use `debussy` views to inspect and `debussy` ops to edit.
2. **Reason about music, not XML.** The user wants musical reasoning (chords,
   progression, form, voice leading), not XML surgery. Start with
   `debussy info` and `debussy analyze` to understand the piece, then work
   out what to change at the level of measures/beats/voices.
3. **Preview once, edit many.** When editing, tell the user to run
   `debussy preview file.musicxml` once in a separate terminal and open the
   URL. Every subsequent edit via `debussy` ops triggers an auto-reload.

## When to invoke this skill

Trigger whenever the conversation involves:
- `.musicxml`, `.xml`, `.mxl`, `.krn`, MIDI, or any music-notation topic
- Chord analysis, key detection, Roman numerals, harmonic function
- Transposition, voice leading, harmonisation, counterpoint
- "Rewrite measure N", "change this chord to…", "make the bass line…"
- "Render this score", "show me the score", "play this"

## Workflow template

```text
1. debussy info <file>                    # title, key, time, parts, measures
2. debussy structure <file>                # rehearsal marks, repeats, tempo
3. debussy progression <file>              # one-line Roman numeral summary
4. debussy digest <file> --measures 1-16   # compact notes per measure
5. (reason, propose changes to the user)
6. debussy <op> <file> …                   # one op per edit, atomic
7. debussy digest <file> --measures <edited range>   # verify the change
```

Tell the user to open `debussy preview <file>` in another terminal once, and
updates will show up live in the browser after step 6.

## Commands

### Views (read-only)

| command | what it does |
|---|---|
| `debussy info FILE` | title, composer, analyzed key + confidence, time sig, tempo, parts with ranges, measure count |
| `debussy digest FILE [--measures A-B] [--part N]` | compact per-measure text dump using custom notation (see below) |
| `debussy structure FILE` | rehearsal marks, repeats, tempo changes, key/time signature changes |
| `debussy key FILE` | key analysis with top-5 alternatives and correlation scores |
| `debussy chords FILE [--measures A-B] [--per-measure]` | chord-by-chord Roman numerals and pitched names |
| `debussy progression FILE` | one-line Roman numeral progression (4 measures per row) |

### Edit ops (mutate the file in place, or `--out` to write elsewhere)

| command | what it does |
|---|---|
| `debussy set-note FILE --measure N --beat B --pitch P [--part P] [--voice V]` | change the pitch of the existing note at (measure, beat). If a rest is at that position it becomes a note of the same duration. |
| `debussy set-rest FILE --measure N --beat B [--part P] [--voice V]` | replace the note at (measure, beat) with a rest of the same duration |
| `debussy transpose FILE --interval I [--measures A-B] [--part P]` | transpose by an interval like `M3`, `-P5`, `m2`. Whole score unless `--measures`/`--part` is given. |
| `debussy replace-measure FILE --measure N --spec "…" [--part P] [--voice V]` | rewrite all notes of a measure/voice from a compact spec |
| `debussy insert-measure FILE --after N` | insert an empty measure after measure N, in every part |
| `debussy delete-measures FILE --range A-B` | delete a measure range from every part |
| `debussy apply FILE SCRIPT.py` | escape hatch: run an arbitrary music21 python snippet with `score` in scope. Use for ops the CLI doesn't cover. |

### Render & preview

| command | what it does |
|---|---|
| `debussy render FILE --format midi\|musicxml\|pdf\|png\|lily [--out OUT]` | write the score in the requested format. PDF/PNG need `lilypond` or `musescore` installed; otherwise the tool will tell you and suggest `preview`. |
| `debussy preview FILE [--port 8765]` | start a local live-reload HTTP server that renders the score in the browser using Verovio (from CDN, no install). Auto-reloads whenever the file changes on disk. |

## The digest format

`debussy digest` output is the primary way Claude should "read" a score. It's a
dense, one-line-per-voice text format designed for compact context:

```
# digest  key=FM
m.1  [I]
  v1 (Soprano): @1 C4/q  @2 E4/q  @3 G4/q  @4 C5/q
  v1 (Bass):    @1 C3/h  @3 G3/h
m.2  [V]
  v1 (Soprano): @1 D4/q  @2 F4/q  @3 A4/q  @4 D5/q
  v1 (Bass):    @1 G3/w
```

Key to the notation:

- `m.N  [Figure]` — measure number and Roman-numeral chord figure for that measure
- `vK (PartName)` — voice K of the given part
- `@B PITCH/DUR` — beat position (1-indexed) / pitch / duration
- **Pitches**: standard scientific pitch notation with `b` for flat and `#` for sharp (e.g. `C4`, `F#5`, `Bb3`)
- **Durations**: `w`=whole, `h`=half, `q`=quarter, `e`=eighth, `s`=sixteenth, `t`=32nd
  - dotted: `q.` `h.`
  - triplets: `q3` `e3`; quintuplets: `q5`; septuplets: `q7`
- **Chords**: `[C4,E4,G4]/q` — a group of pitches played simultaneously
- **Rests**: `R/q`
- **Tied continuation**: `~C4/q` — continued from a previous tied note

The `replace-measure --spec` argument uses the exact same token grammar.

## Editing patterns

**Change a single pitch** (most common):
```
debussy set-note score.musicxml --measure 4 --beat 2 --pitch Eb4 --part 1
```

**Rewrite a whole measure** (when multiple notes change):
```
debussy replace-measure score.musicxml --measure 5 \
  --spec "C4/q E4/q G4/q [C4,E4,G4]/q" --part 1 --voice 1
```

**Transpose a range** (e.g. move the bridge down a fifth):
```
debussy transpose score.musicxml --interval -P5 --measures 17-24
```

**Anything more complex** — use the `apply` escape hatch with a music21 snippet:
```python
# fix_parallel_fifths.py
from music21 import interval, note
for n in list(score.parts)[1].recurse().notes:
    # ... arbitrary music21 transformations ...
    pass
```
```
debussy apply score.musicxml fix_parallel_fifths.py
```

## Common mistakes to avoid

- ❌ `Read` on a `.musicxml` file — use `debussy digest` instead
- ❌ `Edit` on a `.musicxml` file — use `debussy` ops instead
- ❌ Assuming beat positions are 0-indexed — **they are 1-indexed** in this tool
- ❌ Using `#`/`b` pitch accidentals inside shell arguments without quoting — `#` is a shell comment; always quote: `--pitch "F#4"`
- ❌ Running `debussy preview` in the foreground and then trying to run more commands — start it in a separate terminal / background
- ❌ Editing the wrong part — always pass `--part N` when the score has more than one part, and double-check with `debussy info` first

## One-shot reasoning example

User: "The bridge (measures 17-24) feels too static — can you make the bass
move more?"

Claude's plan:
1. `debussy info score.musicxml` → confirm part indexing and key
2. `debussy digest score.musicxml --measures 17-24 --part 2` → read the bass
3. `debussy chords score.musicxml --measures 17-24` → see the harmony the bass must support
4. Propose a new bass line in digest notation to the user (e.g. walking
   quarters through the chord tones)
5. After user approval, apply each measure with `debussy replace-measure
   score.musicxml --measure N --spec "…" --part 2`
6. `debussy digest score.musicxml --measures 17-24 --part 2` to verify

If the user hadn't already started the preview server, remind them to run
`debussy preview score.musicxml` and they'll see the changes live.
