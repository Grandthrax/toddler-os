"""Local child unlock sessions; parent configuration never enters the child API."""
from collections import deque
import hashlib
import hmac
from http.cookies import SimpleCookie, CookieError
import json
import os
from pathlib import Path
import secrets
import threading
import time

from core import Problem

COOKIE = 'little_pages_child'


class LockSettings:
    def __init__(self, path):
        self.path = Path(path)
        self.mutex = threading.RLock()

    def load(self):
        if not self.path.exists():
            return {'enabled': False, 'idle_seconds': 300, 'salt': '', 'password_hash': ''}
        data = json.loads(self.path.read_text('utf-8'))
        if (type(data.get('enabled')) is not bool or type(data.get('idle_seconds')) is not int
                or not 1 <= data['idle_seconds'] <= 3600
                or not isinstance(data.get('salt'), str) or not isinstance(data.get('password_hash'), str)
                or (data['enabled'] and (len(data['salt']) != 32 or len(data['password_hash']) != 64))):
            raise Problem('The lock settings need a grown-up.', 503)
        return data

    @staticmethod
    def password_hash(password, salt):
        return hashlib.pbkdf2_hmac('sha256', password.casefold().encode('utf-8'),
                                   bytes.fromhex(salt), 250000).hex()

    def public(self):
        data = self.load()
        return {key: data[key] for key in ('enabled', 'idle_seconds')} | {'password_set': bool(data['password_hash'])}

    def update(self, enabled, idle_seconds, password=''):
        if type(enabled) is not bool or type(idle_seconds) is not int or not 1 <= idle_seconds <= 3600:
            raise Problem('Choose an idle time between one second and one hour.')
        if not isinstance(password, str) or len(password) > 64 or (password and not password.strip()):
            raise Problem('Choose a password with one to 64 characters.')
        with self.mutex:
            data = self.load() | {'enabled': enabled, 'idle_seconds': idle_seconds}
            if password:
                data['salt'] = secrets.token_hex(16)
                data['password_hash'] = self.password_hash(password, data['salt'])
            if enabled and not data['password_hash']:
                raise Problem('Set an unlock password before enabling the screen lock.')
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_name(self.path.name + '.' + secrets.token_hex(6) + '.new')
            try:
                descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
                with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
                    json.dump(data, output, indent=2); output.write('\n')
                temporary.replace(self.path)
            finally:
                temporary.unlink(missing_ok=True)
        return self.public()


class ScreenLock:
    def __init__(self, path, clock=time.monotonic):
        self.settings = LockSettings(path)
        self.clock = clock
        self.mutex = threading.RLock()
        self.sessions = {}
        self.attempts = deque()

    @staticmethod
    def token(cookie):
        try:
            cookies = SimpleCookie(cookie or '')
            return cookies[COOKIE].value if COOKIE in cookies else ''
        except CookieError:
            return ''

    @staticmethod
    def revision(config):
        return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()

    def status(self, cookie=None):
        with self.mutex:
            config = self.settings.load()
            token = self.token(cookie)
            now = self.clock()
            revision = self.revision(config)
            # Bound memory and expire sessions without relying on the browser.
            for key, (last, version) in list(self.sessions.items()):
                if version != revision or now - last >= config['idle_seconds']:
                    self.sessions.pop(key, None)
            return {'enabled': config['enabled'], 'idle_seconds': config['idle_seconds'],
                    'locked': config['enabled'] and token not in self.sessions}

    def require(self, cookie):
        if self.status(cookie)['locked']:
            raise Problem('Type your password to unlock your desktop.', 423)

    def activity(self, cookie):
        with self.mutex:
            self.require(cookie)
            token = self.token(cookie)
            if token in self.sessions:
                self.sessions[token] = (self.clock(), self.sessions[token][1])
            return self.status(cookie)

    def lock(self, cookie):
        with self.mutex:
            self.sessions.pop(self.token(cookie), None)
            return self.status(cookie)

    def unlock(self, password):
        if not isinstance(password, str) or not 1 <= len(password) <= 64:
            raise Problem('Type your password and try again.', 403)
        with self.mutex:
            config = self.settings.load()
            if not config['enabled']:
                return '', self.status()
            now = self.clock()
            while self.attempts and now - self.attempts[0] >= 60:
                self.attempts.popleft()
            if len(self.attempts) >= 8:
                raise Problem('Take a little rest, then try again.', 429)
            self.attempts.append(now)
            if not hmac.compare_digest(self.settings.password_hash(password, config['salt']), config['password_hash']):
                raise Problem('Have another go. Check your letters.', 403)
            self.attempts.clear()
            token = secrets.token_urlsafe(32)
            self.sessions[token] = (now, self.revision(config))
            return token, self.status(COOKIE + '=' + token)
