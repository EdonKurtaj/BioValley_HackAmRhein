"""Local dashboard API and built frontend: python -m risk_assessment.server."""

import argparse
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
from threading import Lock
from time import monotonic
from urllib.parse import parse_qs, urlsplit

from .dashboard import demo_dashboard, live_dashboard
from .decision import parse_time

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
LIVE_CACHE_SECONDS = 60
DEMO_ANCHOR = datetime.now(timezone.utc).replace(microsecond=0)
_live_lock = Lock()
_live_cached = None
_live_cached_at = 0.0


def dashboard_request(query: dict) -> dict:
    """Validate public query fields; callers cannot request arbitrary DB tables."""
    mode = query.get("mode", ["demo"])[0]
    if mode == "demo":
        anchor = parse_time(query.get("anchor", [None])[0]) or DEMO_ANCHOR
        elapsed = float(query.get("elapsedMinutes", ["0"])[0])
        return demo_dashboard(anchor, elapsed, query.get("scenario", ["fleet"])[0])
    if mode != "live":
        raise ValueError("mode must be demo or live")
    global _live_cached, _live_cached_at
    with _live_lock:
        if _live_cached is None or monotonic() - _live_cached_at >= LIVE_CACHE_SECONDS:
            _live_cached = live_dashboard()
            _live_cached_at = monotonic()
        return _live_cached


class DashboardHandler(BaseHTTPRequestHandler):
    def _send(self, status, data, content_type="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        origin = self.headers.get("Origin")
        if origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass  # A user can switch modes while a live fetch is in progress.

    def _json(self, status, payload):
        self._send(status, json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8"))

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path in ("/api/dashboard", "/api/map"):
            query = parse_qs(parsed.query)
            mode = query.get("mode", ["demo"])[0]
            try:
                if mode not in ("demo", "live"):
                    raise ValueError("mode must be demo or live")
                if mode == "demo":
                    # Invalid replay input gets 400; a failed live feed gets 503.
                    result = dashboard_request(query)
                else:
                    try:
                        result = dashboard_request(query)
                    except (ValueError, OSError):
                        self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "Live-Daten nicht erreichbar. Supabase-Konfiguration und Verbindung auf dem Server prüfen."})
                        return
                if parsed.path == "/api/map":
                    result = {key: result[key] for key in ("mode", "updatedAt", "locations")}
                self._json(HTTPStatus.OK, result)
            except (ValueError, TypeError, OverflowError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if parsed.path.startswith("/api/"):
            self._json(HTTPStatus.NOT_FOUND, {"error": "Unknown endpoint"})
            return
        path = (FRONTEND_DIST / parsed.path.lstrip("/")).resolve()
        if not path.is_relative_to(FRONTEND_DIST.resolve()):
            self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        if not path.is_file():
            path = FRONTEND_DIST / "index.html"
        if not path.is_file():
            self._json(HTTPStatus.NOT_FOUND, {"error": "Frontend zuerst mit npm run build im frontend-Ordner erstellen, oder Vite für Entwicklung starten."})
            return
        self._send(HTTPStatus.OK, path.read_bytes(), mimetypes.guess_type(str(path))[0] or "application/octet-stream")

    def log_message(self, format, *args):
        # Do not log query strings or source credentials.
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"BioValley dashboard: http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
