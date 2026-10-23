"""Local learning settings and durable, versioned writing storage."""
from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager
from datetime import datetime, timezone
from difflib import SequenceMatcher
import io
import json
import re
from pathlib import Path
import sqlite3
import threading
import uuid
import wave

ORDER = list("masdtinpgockubfelhrjvywzx")
ALPHABET = "abcdefghijklmnopqrstuvwxyz"
SOURCE = "https://home.oxfordowl.co.uk/reading/reading-schemes-oxford-levels/read-write-inc-phonics-guide/"
DEFAULTS = {"letters": ORDER[:5], "auto_read_words": False, "phonics_enabled": True}
MAX_TEXT = 12000
EDITING = set(" \n.,!?'–-")
WORDS = re.compile(r"[A-Za-z]+(?:['’–-][A-Za-z]+)*")
WALLPAPERS = [
    {"id": "hills", "name": "Hills", "image": "/wallpaper.svg"},
    {"id": "seaside", "name": "Seaside", "image": "/wallpapers/seaside.svg"},
    {"id": "flowers", "name": "Flowers", "image": "/wallpapers/flowers.svg"},
    {"id": "woodland", "name": "Woodland", "image": "/wallpapers/woodland.svg"},
    {"id": "space", "name": "Space", "image": "/wallpapers/space.svg"},
    {"id": "rainbow", "name": "Rainbow", "image": "/wallpapers/rainbow.svg"},
]


def word_timings(text, chunks):
    """Pair written words with Piper's measured phoneme sample boundaries.

    Never guess timings if the phonemizer expands or joins words differently.
    Character offsets use UTF-16, matching the browser's text selection API.
    """
    groups, elapsed = [], 0.0
    for chunk in chunks:
        if not chunk.phoneme_alignments:
            return []
        position, start, end = 0, None, None
        for alignment in chunk.phoneme_alignments:
            next_position = position + int(alignment.num_samples)
            phoneme = alignment.phoneme
            if phoneme.isspace() or phoneme in "^$_.!?;:,()\"…":
                if start is not None:
                    groups.append((elapsed + start / chunk.sample_rate,
                                   elapsed + end / chunk.sample_rate))
                    start, end = None, None
            else:
                if start is None:
                    start = position
                end = next_position
            position = next_position
        if start is not None:
            groups.append((elapsed + start / chunk.sample_rate, elapsed + end / chunk.sample_rate))
        elapsed += len(chunk.audio_int16_bytes) / (chunk.sample_width * chunk.sample_channels * chunk.sample_rate)
    words = list(WORDS.finditer(text))
    if len(words) != len(groups):
        return []
    return [[len(text[:word.start()].encode("utf-16-le")) // 2,
             len(text[:word.end()].encode("utf-16-le")) // 2,
             round(start, 5), round(end, 5)] for word, (start, end) in zip(words, groups)]


class Problem(Exception):
    def __init__(self, message, status=400, **details):
        super().__init__(message)
        self.status, self.details = status, details


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Settings:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        config = DEFAULTS | (json.loads(self.path.read_text("utf-8")) if self.path.exists() else {})
        letters = config["letters"]
        if not isinstance(letters, list) or not letters or any(
            not isinstance(c, str) or len(c) != 1 or c not in "abcdefghijklmnopqrstuvwxyz" for c in letters
        ):
            raise Problem("The learning settings need a grown-up.", 503)
        if any(type(config[key]) is not bool for key in ("auto_read_words", "phonics_enabled")):
            raise Problem("The learning settings need a grown-up.", 503)
        return {"letters": list(dict.fromkeys(letters)), "auto_read_words": config["auto_read_words"],
                "phonics_enabled": config["phonics_enabled"]}

    def update(self, **changes):
        config = self.load() | changes
        # Validate a candidate before replacing the file used by the app.
        if not config["letters"] or any(c not in "abcdefghijklmnopqrstuvwxyz" or len(c) != 1 for c in config["letters"]):
            raise ValueError("Choose one or more lowercase letters")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".new")
        temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)
        return config


class Store:
    def __init__(self, folder, settings):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path = self.folder / "stories.sqlite3"
        self.settings = settings
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise RuntimeError("This database belongs to a newer application; restore compatible code")
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS stories (
                    id TEXT PRIMARY KEY, text TEXT NOT NULL, version INTEGER NOT NULL,
                    created TEXT NOT NULL, updated TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS revisions (
                    id INTEGER PRIMARY KEY, story_id TEXT NOT NULL REFERENCES stories(id),
                    version INTEGER NOT NULL, text TEXT NOT NULL, created TEXT NOT NULL,
                    UNIQUE(story_id, version)
                );
                CREATE INDEX IF NOT EXISTS revisions_story ON revisions(story_id, version DESC);
                CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS story_archive (
                    story_id TEXT PRIMARY KEY REFERENCES stories(id), archived TEXT NOT NULL
                );
                PRAGMA user_version=1;
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def identifier(value):
        try:
            return str(uuid.UUID(value))
        except (ValueError, TypeError, AttributeError):
            raise Problem("That story could not be found.", 404)

    def desktop(self):
        with self.connect() as db:
            row = db.execute("SELECT value FROM preferences WHERE key='wallpaper'").fetchone()
        selected = row[0] if row and row[0] in {w["id"] for w in WALLPAPERS} else "hills"
        return {"wallpaper": selected, "choices": WALLPAPERS}

    def set_wallpaper(self, selected):
        if not isinstance(selected, str) or selected not in {w["id"] for w in WALLPAPERS}:
            raise Problem("Choose one of your background pictures.")
        with self.connect() as db:
            db.execute("INSERT INTO preferences(key,value) VALUES('wallpaper',?) "
                       "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (selected,))
        return self.desktop()

    def story(self, identifier, db=None):
        if db is None:
            with self.connect() as db:
                return self.story(identifier, db)
        row = db.execute("SELECT s.*, EXISTS(SELECT 1 FROM story_archive a WHERE a.story_id=s.id) AS archived "
                         "FROM stories s WHERE s.id=?", (self.identifier(identifier),)).fetchone()
        if row is None:
            raise Problem("That story could not be found.", 404)
        return dict(row) | {"archived": bool(row["archived"])}

    def stories(self, archived=False):
        # None is used by the parent export to include both active and archived work.
        condition = "1" if archived is None else "a.story_id IS NOT NULL" if archived else "a.story_id IS NULL"
        with self.connect() as db:
            return [dict(row) for row in db.execute(
                "SELECT s.id,substr(s.text,1,160) AS preview,s.version,s.created,s.updated "
                "FROM stories s LEFT JOIN story_archive a ON a.story_id=s.id WHERE " + condition +
                " ORDER BY a.archived DESC,s.updated DESC"
            )]

    def set_archived(self, identifier, archived, version):
        if type(archived) is not bool or type(version) is not int or version < 0:
            raise Problem("That story choice could not be read.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            story = self.story(identifier, db)
            if story["version"] != version:
                raise Problem("That story has newer writing. Open it again before putting it away.", 409,
                              story=story)
            if archived:
                db.execute("INSERT OR IGNORE INTO story_archive(story_id,archived) VALUES(?,?)", (story["id"], now()))
            else:
                db.execute("DELETE FROM story_archive WHERE story_id=?", (story["id"],))
            return self.story(identifier, db)

    def create(self, text=""):
        identifier, stamp = str(uuid.uuid4()), now()
        with self.connect() as db:
            db.execute("INSERT INTO stories VALUES(?,?,0,?,?)", (identifier, text, stamp, stamp))
            db.execute("INSERT INTO revisions(story_id,version,text,created) VALUES(?,0,?,?)", (identifier, text, stamp))
            return self.story(identifier, db)

    def fork(self, identifier, text, version):
        """Preserve a conflicting draft on a new page based on its actual revision."""
        if type(version) is not int or not isinstance(text, str) or len(text) > MAX_TEXT:
            raise Problem("That unfinished writing could not be read.")
        with self.connect() as db:
            self.story(identifier, db)
            base = db.execute("SELECT text FROM revisions WHERE story_id=? AND version=?",
                              (identifier, version)).fetchone()
            if base is None:
                raise Problem("That earlier page could not be found.", 404)
            allowed = set(ALPHABET) | EDITING
            for op, _, _, start, end in SequenceMatcher(None, base["text"], text, autojunk=False).get_opcodes():
                if op in ("insert", "replace") and any(c not in allowed for c in text[start:end]):
                    raise Problem("Use letters, spaces and simple punctuation.", 422)
        copy = self.create(base["text"])
        return self.save(copy["id"], text, 0)

    def save(self, identifier, text, version, restore=None):
        if not isinstance(text, str) or len(text) > MAX_TEXT:
            raise Problem("This story is full. Start another page to write more.")
        if type(version) is not int or version < 0:
            raise Problem("The story version is missing.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = self.story(identifier, db)
            if old["archived"]:
                raise Problem("This story is put away. Keep a copy to save your new words.", 409, story=old)
            if old["version"] != version:
                raise Problem("This story has newer writing. Your words are still on this page.", 409,
                              story=old)
            if restore is not None:
                row = db.execute("SELECT text FROM revisions WHERE story_id=? AND id=?", (identifier, restore)).fetchone()
                if row is None:
                    raise Problem("That earlier writing could not be found.", 404)
                text = row["text"]
            else:
                allowed = set(ALPHABET) | EDITING
                # Preserve existing writing when the available on-screen keys change.
                # Exact historical text can also be brought back by Undo.
                historical = db.execute("SELECT 1 FROM revisions WHERE story_id=? AND text=? LIMIT 1",
                                        (identifier, text)).fetchone()
                if not historical:
                    for operation, _, _, start, end in SequenceMatcher(None, old["text"], text, autojunk=False).get_opcodes():
                        if operation in ("insert", "replace") and any(c not in allowed for c in text[start:end]):
                            raise Problem("Use letters, spaces and simple punctuation.", 422)
            if text != old["text"]:
                stamp, new_version = now(), old["version"] + 1
                db.execute("UPDATE stories SET text=?,version=?,updated=? WHERE id=?",
                           (text, new_version, stamp, identifier))
                db.execute("INSERT INTO revisions(story_id,version,text,created) VALUES(?,?,?,?)",
                           (identifier, new_version, text, stamp))
            return self.story(identifier, db)

    def revisions(self, identifier):
        with self.connect() as db:
            self.story(identifier, db)
            return [dict(row) for row in db.execute(
                "SELECT id,version,substr(text,1,180) AS preview,created FROM revisions "
                "WHERE story_id=? ORDER BY version DESC LIMIT 100", (identifier,))]


class Speech:
    """Piper is used for text reading only, never individual key feedback."""
    def __init__(self, model):
        self.model = Path(model) if model else None
        self.lock = threading.Lock()
        self.voice = None
        self.cache = OrderedDict()

    def ready(self):
        if not self.model or not self.model.is_file():
            return False
        try:
            import importlib.util
            return importlib.util.find_spec("piper") is not None
        except (ImportError, ValueError):
            return False

    def read(self, text):
        return self.render(text)[0]

    def render(self, text):
        if not isinstance(text, str) or not text.strip() or len(text) > 1000:
            raise Problem("Choose a short piece of writing to read.")
        if not self.ready():
            raise Problem("The reading voice needs a grown-up to finish setup.", 503)
        if not self.lock.acquire(timeout=10):
            raise Problem("The reading voice is busy. Try again in a moment.", 503)
        try:
            if text in self.cache:
                self.cache.move_to_end(text)
                return self.cache[text]
            if self.voice is None:
                from piper import PiperVoice
                self.voice = PiperVoice.load(str(self.model), include_alignments=True)
            chunks = list(self.voice.synthesize(text, include_alignments=True))
            if not chunks:
                raise Problem("Choose some words to read.")
            output = io.BytesIO()
            with wave.open(output, "wb") as wav:
                first = chunks[0]
                wav.setframerate(first.sample_rate)
                wav.setsampwidth(first.sample_width)
                wav.setnchannels(first.sample_channels)
                for chunk in chunks:
                    wav.writeframes(chunk.audio_int16_bytes)
            audio = output.getvalue()
            result = audio, word_timings(text, chunks)
            self.cache[text] = result
            while sum(len(item[0]) for item in self.cache.values()) > 8 * 1024 * 1024 or len(self.cache) > 24:
                self.cache.popitem(last=False)
            return result
        finally:
            self.lock.release()
