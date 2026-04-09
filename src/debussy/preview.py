"""Live-reload MusicXML preview server.

Starts a local HTTP server that serves:
  /            → an HTML page that renders the score with Verovio (from CDN)
  /score.xml   → the current MusicXML file contents
  /events      → Server-Sent Events channel that pings clients when the file
                 changes on disk, prompting them to reload /score.xml

Runs entirely on the Python stdlib so there's no extra install step.
"""

from __future__ import annotations

import http.server
import json
import os
import socketserver
import threading
import time
from pathlib import Path

_PAGE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>debussy — live preview</title>
  <style>
    body { font-family: -apple-system, system-ui, sans-serif; margin: 0; padding: 1em;
           background: #fafaf7; color: #222; }
    header { display: flex; align-items: baseline; gap: 1em; margin-bottom: 1em; }
    header h1 { font-size: 1rem; font-weight: 600; margin: 0; }
    #status { font-size: 0.85rem; color: #888; }
    #status.ok { color: #2a7; }
    #status.err { color: #c33; }
    #score { background: white; border: 1px solid #e5e5e0;
             padding: 1em; border-radius: 6px; overflow-x: auto; }
    #err { white-space: pre-wrap; color: #c33; font-family: monospace;
           font-size: 0.85rem; }
  </style>
</head>
<body>
  <header>
    <h1>🎼 __FILE__</h1>
    <span id="status">connecting…</span>
  </header>
  <div id="score">loading…</div>
  <pre id="err"></pre>

  <script src="https://www.verovio.org/javascript/latest/verovio-toolkit-wasm.js"></script>
  <script>
    const status = document.getElementById("status");
    const score = document.getElementById("score");
    const errBox = document.getElementById("err");
    let tk = null;
    let generation = 0;

    function setStatus(text, cls) {
      status.textContent = text;
      status.className = cls || "";
    }

    async function render() {
      const gen = ++generation;
      try {
        const resp = await fetch("/score.xml?t=" + Date.now());
        if (!resp.ok) throw new Error("fetch " + resp.status);
        const xml = await resp.text();
        if (gen !== generation) return;  // a newer render superseded us
        const svg = tk.renderData(xml, {
          pageWidth: Math.min(window.innerWidth * 0.95 * 100, 2500),
          scale: 40,
          adjustPageHeight: true,
          breaks: "auto",
        });
        score.innerHTML = svg;
        errBox.textContent = "";
        setStatus("rendered " + new Date().toLocaleTimeString(), "ok");
      } catch (e) {
        errBox.textContent = String(e);
        setStatus("render error", "err");
      }
    }

    verovio.module.onRuntimeInitialized = async () => {
      tk = new verovio.toolkit();
      await render();

      const es = new EventSource("/events");
      es.onmessage = (ev) => {
        const data = JSON.parse(ev.data);
        if (data.event === "change") render();
      };
      es.onerror = () => setStatus("disconnected", "err");
      es.onopen = () => setStatus("watching…", "ok");
    };
  </script>
</body>
</html>
"""


class _Watcher:
    """Background thread that polls the file mtime and broadcasts changes."""

    def __init__(self, path: Path):
        self.path = path
        self.mtime = path.stat().st_mtime if path.exists() else 0
        self.subscribers: list[list] = []  # list of [list-of-pending-events]
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def subscribe(self) -> list:
        queue: list[str] = []
        with self.lock:
            self.subscribers.append(queue)
        return queue

    def unsubscribe(self, queue) -> None:
        with self.lock:
            if queue in self.subscribers:
                self.subscribers.remove(queue)

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


def _make_handler(score_path: Path, watcher: _Watcher):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args, **kwargs):  # quiet
            pass

        def do_GET(self):
            if self.path == "/" or self.path.startswith("/index"):
                html = _PAGE.replace("__FILE__", score_path.name)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
                return

            if self.path.startswith("/score.xml"):
                if not score_path.exists():
                    self.send_error(404, "score not found")
                    return
                data = score_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.recordare.musicxml+xml")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

            if self.path == "/events":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                queue = watcher.subscribe()
                try:
                    # send an initial ping so clients know we're live
                    self.wfile.write(b": hello\n\n")
                    self.wfile.flush()
                    while True:
                        if queue:
                            payload = queue.pop(0)
                            self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                            self.wfile.flush()
                        else:
                            # heartbeat every 15s so proxies don't time out
                            self.wfile.write(b": ping\n\n")
                            self.wfile.flush()
                            time.sleep(1.0)
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


def serve(path: str, port: int = 8765, host: str = "127.0.0.1") -> None:
    score_path = Path(path).resolve()
    if not score_path.exists():
        raise FileNotFoundError(score_path)
    watcher = _Watcher(score_path)
    handler = _make_handler(score_path, watcher)
    server = _ThreadingServer((host, port), handler)
    url = f"http://{host}:{port}/"
    print(f"debussy preview serving {score_path.name} at {url}")
    print("watching file for changes; edit via `debussy` ops to trigger reload")
    print("press Ctrl-C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        server.server_close()
