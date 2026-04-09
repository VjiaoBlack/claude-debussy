"""Live-reload MusicXML preview server.

Routes:
  /             → HTML viewer
  /score.xml    → raw MusicXML bytes (cache-busted)
  /score.svg    → all pages rendered as a single <svg>-per-page sequence
                  (served via JSON so the client can rebuild the page list
                  without re-fetching on every zoom change)
  /score.json   → {pages: [svg1, svg2, ...], midi: base64-midi, generation: N}
  /events       → SSE channel that pings clients when the file changes
  /print        → HTML page pre-rendered for browser "Save as PDF"

The server renders with the Verovio Python binding on the backend, which
gives us identical output to the PDF exporter and avoids depending on
verovio.js at runtime (no CDN fetch, no wasm warm-up).
"""

from __future__ import annotations

import base64
import http.server
import json
import socketserver
import threading
import time
import webbrowser
from pathlib import Path

from debussy.score_io import load as load_score


# ---------------------------------------------------------------------------
# HTML page
# ---------------------------------------------------------------------------

_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>debussy — __FILE__</title>
  <style>
    :root {
      --fg: #1a1a1a;
      --muted: #888;
      --ok: #2a7;
      --err: #c33;
      --bg: #f6f5f1;
      --panel: #ffffff;
      --border: #e0dfd8;
    }
    html, body { margin: 0; padding: 0; background: var(--bg); color: var(--fg);
                 font: 14px/1.4 -apple-system, system-ui, sans-serif; }
    header { position: sticky; top: 0; z-index: 10; display: flex; align-items: center;
             gap: .75em; padding: .6em 1em; background: var(--panel);
             border-bottom: 1px solid var(--border); }
    header h1 { font-size: 14px; font-weight: 600; margin: 0; flex: 1; }
    header h1 small { color: var(--muted); font-weight: 400; margin-left: .5em; }
    header button { padding: .35em .8em; border: 1px solid var(--border);
                    background: var(--panel); border-radius: 5px;
                    cursor: pointer; font: inherit; }
    header button:hover { background: #f0efea; }
    header button:active { transform: translateY(1px); }
    #status { font-size: 12px; color: var(--muted); min-width: 14em; text-align: right; }
    #status.ok { color: var(--ok); }
    #status.err { color: var(--err); }
    #zoom-val { display: inline-block; width: 3em; text-align: center; color: var(--muted); }
    main { max-width: 100%; padding: 1em; }
    .page { background: white; border: 1px solid var(--border);
            margin: 0 auto 1em; box-shadow: 0 1px 3px rgba(0,0,0,.05);
            display: block; }
    .page svg { display: block; max-width: 100%; height: auto; }
    #err { white-space: pre-wrap; color: var(--err); font-family: ui-monospace, monospace;
           font-size: 12px; padding: 1em; }
  </style>
</head>
<body>
  <header>
    <h1>🎼 __FILE__ <small id="meta"></small></h1>
    <button id="play">▶ Play</button>
    <button id="stop">■</button>
    <button id="zoom-out">−</button>
    <span id="zoom-val">100%</span>
    <button id="zoom-in">+</button>
    <button id="print">⎙ PDF</button>
    <span id="status">connecting…</span>
  </header>
  <main id="pages">loading…</main>
  <pre id="err"></pre>

  <script src="https://cdn.jsdelivr.net/npm/html-midi-player@1.5.0/dist/html-midi-player.min.js"></script>
  <script>
    const status = document.getElementById('status');
    const pagesEl = document.getElementById('pages');
    const errBox = document.getElementById('err');
    const metaEl = document.getElementById('meta');
    const zoomVal = document.getElementById('zoom-val');
    let zoom = 1.0;
    let currentMidi = null;   // data URL of current MIDI
    let midiAudio = null;     // Audio element playing current MIDI (fallback)
    let generation = 0;

    function setStatus(text, cls) {
      status.textContent = text;
      status.className = cls || '';
    }

    async function render() {
      const gen = ++generation;
      try {
        const resp = await fetch('/score.json?t=' + Date.now());
        if (!resp.ok) throw new Error('fetch ' + resp.status);
        const data = await resp.json();
        if (gen !== generation) return;

        pagesEl.innerHTML = '';
        data.pages.forEach((svg, i) => {
          const wrap = document.createElement('div');
          wrap.className = 'page';
          wrap.style.width = (100 * zoom) + '%';
          wrap.style.maxWidth = (850 * zoom) + 'px';
          wrap.innerHTML = svg;
          pagesEl.appendChild(wrap);
        });
        currentMidi = 'data:audio/midi;base64,' + data.midi;
        metaEl.textContent = `${data.pages.length} page${data.pages.length > 1 ? 's' : ''}`;
        errBox.textContent = '';
        setStatus('rendered ' + new Date().toLocaleTimeString(), 'ok');
      } catch (e) {
        errBox.textContent = String(e);
        setStatus('render error', 'err');
      }
    }

    function applyZoom() {
      zoomVal.textContent = Math.round(zoom * 100) + '%';
      [...document.querySelectorAll('.page')].forEach(el => {
        el.style.width = (100 * zoom) + '%';
        el.style.maxWidth = (850 * zoom) + 'px';
      });
    }

    document.getElementById('zoom-in').onclick = () => {
      zoom = Math.min(3, zoom + 0.1); applyZoom();
    };
    document.getElementById('zoom-out').onclick = () => {
      zoom = Math.max(0.3, zoom - 0.1); applyZoom();
    };

    document.getElementById('play').onclick = async () => {
      if (!currentMidi) return;
      // Simple fallback: open in a <audio> element that hosts a MIDI data URL.
      // Most browsers won't play MIDI natively, so we instead POST to an
      // in-page MIDI player widget if html-midi-player loaded, else we
      // download the MIDI.
      if (window.customElements && customElements.get('midi-player')) {
        let el = document.getElementById('inline-midi');
        if (!el) {
          el = document.createElement('midi-player');
          el.id = 'inline-midi';
          el.setAttribute('sound-font', '');
          el.style.display = 'none';
          document.body.appendChild(el);
        }
        el.src = currentMidi;
        el.start();
      } else {
        // Fallback: prompt download
        const a = document.createElement('a');
        a.href = currentMidi;
        a.download = 'preview.mid';
        a.click();
      }
    };

    document.getElementById('stop').onclick = () => {
      const el = document.getElementById('inline-midi');
      if (el) el.stop();
    };

    document.getElementById('print').onclick = () => window.print();

    // Zoom with ctrl/cmd + wheel
    window.addEventListener('wheel', (e) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        zoom = Math.max(0.3, Math.min(3, zoom + (e.deltaY < 0 ? 0.1 : -0.1)));
        applyZoom();
      }
    }, { passive: false });

    // Initial render + SSE
    render();
    const es = new EventSource('/events');
    es.onmessage = (ev) => {
      const d = JSON.parse(ev.data);
      if (d.event === 'change') render();
    };
    es.onopen = () => setStatus('watching…', 'ok');
    es.onerror = () => setStatus('disconnected', 'err');
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# score rendering with Verovio
# ---------------------------------------------------------------------------


def _render_payload(score_path: Path) -> dict:
    """Render the score to {pages, midi} using the Verovio Python binding."""
    import verovio

    tk = verovio.toolkit()
    tk.setOptions(
        {
            "pageWidth": 2100,
            "pageHeight": 2970,
            "scale": 40,
            "adjustPageHeight": True,
            "breaks": "auto",
            "footer": "none",
            "header": "auto",
            "svgHtml5": True,
        }
    )
    tk.loadFile(str(score_path))
    n = tk.getPageCount()
    pages = [tk.renderToSVG(i) for i in range(1, n + 1)]
    midi = tk.renderToMIDI()  # base64 string
    return {"pages": pages, "midi": midi}


# ---------------------------------------------------------------------------
# file watcher
# ---------------------------------------------------------------------------


class _Watcher:
    def __init__(self, path: Path):
        self.path = path
        self.mtime = path.stat().st_mtime if path.exists() else 0
        self.subscribers: list[list] = []
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def subscribe(self) -> list:
        q: list[str] = []
        with self.lock:
            self.subscribers.append(q)
        return q

    def unsubscribe(self, q) -> None:
        with self.lock:
            if q in self.subscribers:
                self.subscribers.remove(q)

    def _broadcast(self, payload: str) -> None:
        with self.lock:
            for q in self.subscribers:
                q.append(payload)

    def _loop(self) -> None:
        while True:
            try:
                if self.path.exists():
                    mt = self.path.stat().st_mtime
                    if mt != self.mtime:
                        self.mtime = mt
                        self._broadcast(json.dumps({"event": "change"}))
            except Exception:
                pass
            time.sleep(0.4)


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------


def _make_handler(score_path: Path, watcher: _Watcher):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args, **kwargs):  # quiet
            pass

        def _send(self, code: int, ct: str, body: bytes, headers: dict | None = None):
            self.send_response(code)
            self.send_header("Content-Type", ct)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            if headers:
                for k, v in headers.items():
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            if self.path == "/" or self.path.startswith("/index"):
                html = _PAGE.replace("__FILE__", score_path.name)
                self._send(200, "text/html; charset=utf-8", html.encode("utf-8"))
                return

            if self.path.startswith("/score.xml"):
                if not score_path.exists():
                    self.send_error(404)
                    return
                self._send(
                    200,
                    "application/vnd.recordare.musicxml+xml",
                    score_path.read_bytes(),
                )
                return

            if self.path.startswith("/score.json"):
                try:
                    payload = _render_payload(score_path)
                    body = json.dumps(payload).encode("utf-8")
                    self._send(200, "application/json", body)
                except Exception as e:
                    err = json.dumps({"error": str(e), "pages": [], "midi": ""})
                    self._send(200, "application/json", err.encode("utf-8"))
                return

            if self.path == "/events":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                queue = watcher.subscribe()
                try:
                    self.wfile.write(b": hello\n\n")
                    self.wfile.flush()
                    last_beat = time.time()
                    while True:
                        if queue:
                            payload = queue.pop(0)
                            self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                            self.wfile.flush()
                            last_beat = time.time()
                        else:
                            if time.time() - last_beat > 15:
                                self.wfile.write(b": ping\n\n")
                                self.wfile.flush()
                                last_beat = time.time()
                            time.sleep(0.3)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    watcher.unsubscribe(queue)
                return

            self.send_error(404)

    return Handler


class _ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def serve(path: str, port: int = 8765, host: str = "127.0.0.1", open_browser: bool = True) -> None:
    score_path = Path(path).resolve()
    if not score_path.exists():
        raise FileNotFoundError(score_path)

    # Sanity-check: try loading once so the user gets an early error
    try:
        load_score(score_path)
    except Exception as e:
        print(f"warning: {score_path.name} failed to parse: {e}")

    watcher = _Watcher(score_path)
    handler = _make_handler(score_path, watcher)
    server = _ThreadingServer((host, port), handler)
    url = f"http://{host}:{port}/"
    print(f"debussy preview serving {score_path.name} at {url}")
    print("watching file for changes; edit via `debussy` ops to trigger reload")
    print("press Ctrl-C to stop")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        server.server_close()
