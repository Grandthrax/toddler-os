"""Separate loopback-only parent dashboard; never served by the child web port."""
import argparse
import hmac
from http.cookies import SimpleCookie, CookieError
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import time

from core import Problem
from screen_lock import LockSettings
from server import Handler

STATIC = Path(__file__).resolve().parent / 'admin_static'
COOKIE = 'little_pages_parent'


def access_key(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return path.read_text('utf-8').strip()
    token = secrets.token_urlsafe(32)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
        output.write(token + '\n')
    return token


class AdminServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port, config, token_file):
        self.settings = LockSettings(config)
        self.token = access_key(token_file)
        if len(self.token) < 32:
            raise RuntimeError('The parent access key needs replacing.')
        self.session = secrets.token_urlsafe(32)
        self.session_until = 0
        super().__init__(('127.0.0.1', port), AdminHandler)


class AdminHandler(Handler):
    def guard(self, mutate=False):
        expected = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        if self.headers.get('Host') not in expected:
            raise Problem('Open the parent dashboard directly.', 403)
        if mutate and (self.headers.get('Origin') not in {'http://' + host for host in expected}
                       or self.headers.get('X-Little-Pages') != '1'
                       or self.headers.get('Content-Type', '').split(';')[0] != 'application/json'):
            raise Problem('Open the parent dashboard directly to change settings.', 403)

    def authenticated(self):
        try:
            cookie = SimpleCookie(self.headers.get('Cookie') or '')
            token = cookie[COOKIE].value if COOKIE in cookie else ''
        except CookieError:
            token = ''
        if time.monotonic() >= self.server.session_until or not hmac.compare_digest(token, self.server.session):
            raise Problem('Use your private parent access link to open the dashboard.', 401)

    def get(self, path):
        if path == '/api/config':
            self.authenticated()
            self.respond(self.server.settings.public())
        elif path == '/favicon.ico':
            self.respond(b'', code=204, mime='image/x-icon')
        elif path in ('/', '/admin.js', '/admin.css'):
            self.file(STATIC / ('index.html' if path == '/' else path.lstrip('/')))
        else:
            raise Problem('That parent page was not found.', 404)

    def change(self, path, body):
        if path == '/api/session' and self.command == 'POST':
            if set(body) != {'token'} or not isinstance(body['token'], str) or not hmac.compare_digest(body['token'], self.server.token):
                raise Problem('Check your parent access link.', 403)
            self.server.session_until = time.monotonic() + 12 * 3600
            self.respond({'authenticated': True}, headers={
                'Set-Cookie': f'{COOKIE}={self.server.session}; Path=/; HttpOnly; SameSite=Strict; Max-Age=43200'})
        elif path == '/api/config' and self.command == 'PUT':
            self.authenticated()
            if set(body) != {'enabled', 'idle_minutes', 'password'} or type(body['idle_minutes']) is not int or not 1 <= body['idle_minutes'] <= 60:
                raise Problem('Choose an idle time from one to 60 minutes.')
            self.respond(self.server.settings.update(body['enabled'], body['idle_minutes'] * 60, body['password']))
        else:
            raise Problem('That parent action is not available.', 404)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8877)
    parser.add_argument('--lock-settings', type=Path, required=True)
    parser.add_argument('--token-file', type=Path, required=True)
    args = parser.parse_args()
    app = AdminServer(args.port, args.lock_settings, args.token_file)
    print(f'Parent dashboard: http://127.0.0.1:{app.server_port}/ (private access link required)', flush=True)
    try:
        app.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.server_close()


if __name__ == '__main__':
    main()
