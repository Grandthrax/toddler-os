"""Toddler OS: loopback-only offline learning application."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
from urllib.parse import parse_qs, unquote, urlsplit

from core import ALPHABET, ORDER, SOURCE, MAX_TEXT, Problem, Settings, Speech, Store
from ninja import NinjaGame
from storybooks import Storybooks

STATIC = Path(__file__).resolve().parent / "static"


class Application(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port, data, settings=None, model=None, phonics=None):
        self.settings = Settings(settings or Path(data) / "settings.json")
        self.settings.load()
        self.store = Store(data, self.settings)
        self.ninja = NinjaGame(self.store)
        self.storybooks = Storybooks(self.store)
        self.speech = Speech(model)
        self.phonics = Path(phonics or STATIC / "phonics/custom").resolve()
        super().__init__(("127.0.0.1", port), Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = "ToddlerOS/0.1"

    def log_message(self, format, *args):
        # Do not log story text, request bodies or query strings.
        if args and str(args[0]).startswith("POST /api/read"):
            return
        super().log_message(format, *args)

    def headers_safe(self, content_type, size):
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; "
                         "font-src 'self'; img-src 'self' data:; media-src 'self' blob:; "
                         "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.send_header("X-Frame-Options", "DENY")

    def respond(self, body, code=200, mime="application/json; charset=utf-8", headers=None):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.headers_safe(mime, len(body))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def guard(self, mutate=False):
        expected = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if self.headers.get("Host") not in expected:
            raise Problem("This address is not enabled.", 403)
        if mutate:
            if self.headers.get("Origin") not in {"http://" + host for host in expected}:
                raise Problem("Open this app directly to make changes.", 403)
            if self.headers.get("X-Little-Pages") != "1" or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                raise Problem("That request is not enabled.", 403)

    def body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 100000:
                raise ValueError()
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError()
            return data
        except (ValueError, UnicodeError):
            raise Problem("That request could not be read.")

    def handle_request(self, mutate=False):
        self.connection.settimeout(15)
        try:
            self.guard(mutate)
            path = unquote(urlsplit(self.path).path)
            if not mutate:
                self.get(path)
            else:
                self.change(path, self.body())
        except Problem as exc:
            self.respond({"error": str(exc), **exc.details}, exc.status)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        except Exception as exc:
            self.log_error("Request failed: %s", type(exc).__name__)
            self.respond({"error": "Something needs a grown-up. Your saved writing is still here."}, 500)

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request(True)

    def do_PUT(self):
        self.handle_request(True)

    def get(self, path):
        app = self.server
        if path == "/api/settings":
            self.respond(app.settings.load() | {"programme": "Read Write Inc. — Set 1 order",
                         "sequence": ORDER, "source": SOURCE, "max_text": MAX_TEXT,
                         "keyboard_letters": list(ALPHABET),
                         "voice_ready": app.speech.ready(), "phonics_available": [
                             c for c in "abcdefghijklmnopqrstuvwxyz" if self.sound_file(c) is not None]})
        elif path == "/api/stories":
            query = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
            if set(query) - {"archived"} or query.get("archived") not in (None, ["0"], ["1"]):
                raise Problem("Choose your stories or your put-away stories.")
            self.respond({"stories": app.store.stories(archived=query.get("archived") == ["1"])})
        elif path == "/api/desktop":
            self.respond(app.store.desktop())
        elif path == "/api/ninja":
            self.respond(app.ninja.state())
        elif path == "/api/storybooks":
            self.respond(app.storybooks.library())
        elif match := re.fullmatch(r"/api/storybooks/([a-f0-9-]+)", path):
            self.respond(app.storybooks.book(match[1]))
        elif match := re.fullmatch(r"/api/stories/([a-f0-9-]+)(/revisions)?", path):
            self.respond({"revisions": app.store.revisions(match[1])} if match[2] else app.store.story(match[1]))
        elif path == "/health":
            self.respond({"status": "ok", "application": "Toddler OS", "version": "0.1.0"})
        elif match := re.fullmatch(r"/phonics/([a-z])", path):
            file = self.sound_file(match[1])
            if file is None:
                raise Problem("That sound needs a recording.", 404)
            self.file(file)
        elif path.startswith("/api/"):
            raise Problem("That page could not be found.", 404)
        else:
            file = (STATIC / ("index.html" if path == "/" else path.lstrip("/"))).resolve()
            if not file.is_relative_to(STATIC) or not file.is_file():
                raise Problem("That page could not be found.", 404)
            self.file(file)

    def sound_file(self, letter):
        for extension in (".wav", ".ogg", ".mp3"):
            candidate = (self.server.phonics / (letter + extension)).resolve()
            if candidate.is_relative_to(self.server.phonics) and candidate.is_file():
                return candidate
        return None

    def file(self, path):
        mime = {".js": "text/javascript", ".ogg": "audio/ogg", ".wav": "audio/wav",
                ".ttf": "font/ttf"}.get(path.suffix, mimetypes.guess_type(path)[0] or "application/octet-stream")
        self.respond(path.read_bytes(), mime=mime)

    def change(self, path, body):
        app = self.server
        if path == "/api/storybooks" and self.command == "POST":
            self.respond(app.storybooks.create(body),201)
        elif match := re.fullmatch(r"/api/storybooks/([a-f0-9-]+)/pages/([0-9]+)",path):
            if self.command != 'PUT':raise Problem('That action is not enabled.',405)
            self.respond(app.storybooks.save(match[1],int(match[2]),body))
        elif path in ("/api/ninja/start", "/api/ninja/answer", "/api/ninja/help", "/api/ninja/reward", "/api/ninja/equip") and self.command == "POST":
            action = path.rsplit("/", 1)[1]
            if action == "start":
                if set(body) - {"level"} or ("level" in body and body["level"] is None):
                    raise Problem("Choose a mission number with its play button.")
                self.respond(app.ninja.start(body.get("level")))
            else:
                self.respond(getattr(app.ninja, action)(body))
        elif path == "/api/desktop" and self.command == "PUT":
            if set(body) != {"wallpaper"}:
                raise Problem("Choose one background picture at a time.")
            self.respond(app.store.set_wallpaper(body["wallpaper"]))
        elif path == "/api/stories" and self.command == "POST":
            self.respond(app.store.create(), 201)
        elif match := re.fullmatch(r"/api/stories/([a-f0-9-]+)(/restore|/fork|/archive)?", path):
            if match[2] == "/archive" and self.command == "POST":
                if set(body) != {"archived", "version"}:
                    raise Problem("That story choice could not be read.")
                self.respond(app.store.set_archived(match[1], body["archived"], body["version"]))
            elif match[2] == "/fork" and self.command == "POST":
                self.respond(app.store.fork(match[1], body.get("text"), body.get("version")), 201)
            elif match[2] == "/restore" and self.command == "POST":
                revision = body.get("revision")
                if type(revision) is not int:
                    raise Problem("Choose an earlier piece of writing.")
                self.respond(app.store.save(match[1], "", body.get("version"), restore=revision))
            elif not match[2] and self.command == "PUT":
                self.respond(app.store.save(match[1], body.get("text"), body.get("version")))
            else:
                raise Problem("That action is not enabled.", 405)
        elif path == "/api/read" and self.command == "POST":
            audio, words = app.speech.render(body.get("text"))
            self.respond(audio, mime="audio/wav", headers={
                "X-Little-Pages-Words": json.dumps(words, separators=(",", ":"))})
        else:
            raise Problem("That action is not enabled.", 404)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8876)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--settings", type=Path)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--phonics-dir", type=Path)
    args = parser.parse_args()
    app = Application(args.port, args.data_dir, args.settings, args.model, args.phonics_dir)
    print(f"Toddler OS: http://127.0.0.1:{app.server_port} (loopback only)", flush=True)
    try:
        app.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.server_close()


if __name__ == "__main__":
    main()
