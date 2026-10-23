"""Durability, learning restrictions and local HTTP boundary checks."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from core import ORDER, Problem, Settings, Store, word_timings
from server import Application


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.settings = Settings(self.folder / "settings.json")
        self.store = Store(self.folder, self.settings)
        self.story = self.store.create()

    def tearDown(self):
        self.temp.cleanup()

    def test_default_is_first_five_read_write_inc_sounds(self):
        self.assertEqual(self.settings.load()["letters"], list("masdt"))
        self.assertEqual("".join(ORDER[:10]), "masdtinpgo")

    def test_save_and_revisions_survive_new_store_instance(self):
        first = self.store.save(self.story["id"], "mat", 0)
        second = self.store.save(first["id"], "mat sat", first["version"])
        reopened = Store(self.folder, self.settings)
        self.assertEqual(reopened.story(first["id"])["text"], "mat sat")
        self.assertEqual(len(reopened.revisions(first["id"])), 3)
        self.assertEqual(second["version"], 2)

    def test_unsupported_characters_rejected_by_server_storage(self):
        for content in ("<script>", "mat\x00", "123", "MAT"):
            with self.assertRaises(Problem) as error:
                self.store.save(self.story["id"], content, 0)
            self.assertEqual(error.exception.status, 422)
        self.assertEqual(self.store.story(self.story["id"])["text"], "")

    def test_keyboard_accepts_all_letters_independently_of_on_screen_keys(self):
        self.store.save(self.story["id"], "mat", 0)
        self.settings.update(letters=["a"])
        saved = self.store.save(self.story["id"], "abcdefghijklmnopqrstuvwxyz", 1)
        self.assertEqual(saved["text"], "abcdefghijklmnopqrstuvwxyz")
        self.assertEqual(self.settings.load()["letters"], ["a"])

    def test_deleted_work_can_be_restored_without_erasing_newer_revision(self):
        self.store.save(self.story["id"], "mat sat", 0)
        earlier = self.store.revisions(self.story["id"])[0]
        self.store.save(self.story["id"], "", 1)
        recovered = self.store.save(self.story["id"], "", 2, restore=earlier["id"])
        self.assertEqual(recovered["text"], "mat sat")
        self.assertEqual(recovered["version"], 3)
        self.assertEqual(len(self.store.revisions(self.story["id"])), 4)

    def test_stale_save_cannot_overwrite_newer_work(self):
        self.store.save(self.story["id"], "mat", 0)
        with self.assertRaises(Problem) as error:
            self.store.save(self.story["id"], "sat", 0)
        self.assertEqual(error.exception.status, 409)
        self.assertEqual(self.store.story(self.story["id"])["text"], "mat")

    def test_concurrent_saves_keep_one_and_reject_the_stale_writer(self):
        def write(text):
            try:
                return self.store.save(self.story["id"], text, 0)["text"]
            except Problem as error:
                return error.status
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(write, ["mat", "sat"]))
        self.assertIn(409, results)
        self.assertIn(self.store.story(self.story["id"])["text"], ("mat", "sat"))

    def test_sqlite_online_backup_restores_stories_and_history(self):
        self.store.save(self.story["id"], "mat sat", 0)
        self.store.set_wallpaper("flowers")
        self.store.set_archived(self.story["id"], True, 1)
        destination = self.folder / "copy.sqlite3"
        with self.store.connect() as db, closing(sqlite3.connect(destination)) as backup:
            db.backup(backup)
        with closing(sqlite3.connect(destination)) as backup:
            self.assertEqual(backup.execute("SELECT text FROM stories").fetchone()[0], "mat sat")
            self.assertEqual(backup.execute("SELECT count(*) FROM revisions").fetchone()[0], 2)
            self.assertEqual(backup.execute("SELECT value FROM preferences WHERE key='wallpaper'").fetchone()[0], "flowers")
            self.assertEqual(backup.execute("SELECT story_id FROM story_archive").fetchone()[0], self.story["id"])

    def test_desktop_choice_survives_restart_without_changing_writing_or_learning_settings(self):
        self.assertEqual(self.store.desktop()["wallpaper"], "hills")
        self.store.save(self.story["id"], "mat", 0)
        self.store.set_wallpaper("space")
        reopened = Store(self.folder, self.settings)
        self.assertEqual(reopened.desktop()["wallpaper"], "space")
        self.assertEqual(reopened.story(self.story["id"])["text"], "mat")
        self.assertEqual(len(reopened.revisions(self.story["id"])), 2)
        self.assertEqual(self.settings.load()["letters"], list("masdt"))

    def test_existing_version_one_database_gets_default_background_and_preserves_stories(self):
        self.store.save(self.story["id"], "mat", 0)
        with self.store.connect() as db:
            db.execute("DROP TABLE preferences")
            db.execute("DROP TABLE story_archive")
        reopened = Store(self.folder, self.settings)
        self.assertEqual(reopened.desktop()["wallpaper"], "hills")
        self.assertEqual(reopened.story(self.story["id"])["text"], "mat")
        self.assertFalse(reopened.story(self.story["id"])["archived"])

    def test_restore_cannot_read_another_storys_revision(self):
        other = self.store.create()
        revision = self.store.revisions(other["id"])[0]
        with self.assertRaises(Problem) as error:
            self.store.save(self.story["id"], "", 0, restore=revision["id"])
        self.assertEqual(error.exception.status, 404)

    def test_conflicting_draft_can_be_saved_on_a_fresh_page(self):
        self.store.save(self.story["id"], "mat", 0)
        self.store.save(self.story["id"], "sat", 1)
        copy = self.store.fork(self.story["id"], "mat dad", 1)
        self.assertNotEqual(copy["id"], self.story["id"])
        self.assertEqual(copy["text"], "mat dad")
        self.assertEqual(self.store.story(self.story["id"])["text"], "sat")

    def test_fresh_copy_rejects_unsupported_characters(self):
        with self.assertRaises(Problem) as error:
            self.store.fork(self.story["id"], "xyz123", 0)
        self.assertEqual(error.exception.status, 422)

    def test_archive_survives_restart_and_restore_preserves_every_revision(self):
        self.store.save(self.story["id"], "cat", 0)
        self.store.save(self.story["id"], "cat dog", 1)
        before = self.store.story(self.story["id"])
        revisions = self.store.revisions(self.story["id"])
        self.assertTrue(self.store.set_archived(self.story["id"], True, 2)["archived"])
        reopened = Store(self.folder, self.settings)
        self.assertEqual(reopened.stories(), [])
        self.assertEqual(reopened.stories(archived=True)[0]["id"], before["id"])
        self.assertEqual(reopened.stories(archived=None)[0]["id"], before["id"])
        self.assertEqual(reopened.revisions(before["id"]), revisions)
        recovered = reopened.set_archived(before["id"], False, 2)
        self.assertEqual(recovered, before)
        self.assertEqual(reopened.stories(archived=True), [])
        self.assertEqual(len(reopened.stories()), 1)

    def test_stale_archive_cannot_hide_new_writing_and_archived_edits_can_be_copied(self):
        self.store.save(self.story["id"], "cat", 0)
        with self.assertRaises(Problem) as error:
            self.store.set_archived(self.story["id"], True, 0)
        self.assertEqual(error.exception.status, 409)
        self.assertFalse(self.store.story(self.story["id"])["archived"])
        self.store.set_archived(self.story["id"], True, 1)
        with self.assertRaises(Problem) as error:
            self.store.save(self.story["id"], "cat dog", 1)
        self.assertEqual(error.exception.status, 409)
        copy = self.store.fork(self.story["id"], "cat dog", 1)
        self.assertEqual(copy["text"], "cat dog")
        self.assertFalse(copy["archived"])
        self.assertEqual(self.store.story(self.story["id"])["text"], "cat")
        self.assertTrue(self.store.story(self.story["id"])["archived"])

    def test_parent_text_export_includes_put_away_stories(self):
        import subprocess
        self.store.save(self.story["id"], "cat dog", 0)
        self.store.set_archived(self.story["id"], True, 1)
        destination = self.folder / "exported"
        subprocess.run([sys.executable, "-B", str(Path(__file__).resolve().parents[1] / "app/manage.py"),
                        "--data-dir", str(self.folder), "export", str(destination)], check=True, capture_output=True)
        self.assertEqual((destination / (self.story["id"] + ".txt")).read_text(), "cat dog")


class TimingTests(unittest.TestCase):
    @staticmethod
    def chunk(pairs):
        return SimpleNamespace(sample_rate=100, sample_width=2, sample_channels=1,
            audio_int16_bytes=b"\0\0" * sum(samples for _, samples in pairs),
            phoneme_alignments=[SimpleNamespace(phoneme=p, num_samples=n) for p, n in pairs])

    def test_repeated_words_use_distinct_audio_and_text_boundaries(self):
        chunk = self.chunk([("^", 10), ("m", 20), ("a", 10), ("t", 10), (" ", 15),
                            ("m", 20), ("a", 10), ("t", 10), (".", 20), ("$", 5)])
        self.assertEqual(word_timings("  mat mat.", [chunk]), [[2, 5, .1, .5], [6, 9, .65, 1.05]])

    def test_sentence_chunks_include_previous_audio_duration_and_utf16_offsets(self):
        chunk = self.chunk([("^", 10), ("a", 30), (".", 10), ("$", 10)])
        self.assertEqual(word_timings("\U0001f31f a.\na.", [chunk, chunk]), [[3, 4, .1, .4], [6, 7, .7, 1.0]])

    def test_missing_or_ambiguous_alignments_do_not_invent_word_timings(self):
        chunk = self.chunk([("a", 30)])
        self.assertEqual(word_timings("a a", [chunk]), [])
        chunk.phoneme_alignments = None
        self.assertEqual(word_timings("a", [chunk]), [])


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Application(0, self.temp.name)
        self.base = f"http://127.0.0.1:{self.app.server_port}"
        self.thread = threading.Thread(target=self.app.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.app.shutdown(); self.app.server_close(); self.thread.join()
        self.temp.cleanup()

    def request(self, path, data=None, method=None, headers=None):
        defaults = {"Origin": self.base, "X-Little-Pages": "1", "Content-Type": "application/json"}
        defaults.update(headers or {})
        request = Request(self.base + path, json.dumps(data).encode() if data is not None else None,
                          defaults, method=method)
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            body = response.read()
            return response.status, response.headers, json.loads(body) if "json" in response.headers.get("Content-Type", "") else body

    def test_normal_story_workflow(self):
        status, _, story = self.request("/api/stories", {}, "POST")
        self.assertEqual(status, 201)
        status, _, saved = self.request("/api/stories/" + story["id"], {"text":"mat", "version":0}, "PUT")
        self.assertEqual(status, 200)
        self.assertEqual(saved["text"], "mat")
        self.assertEqual(self.request("/api/stories")[2]["stories"][0]["preview"], "mat")

    def test_wrong_origin_or_missing_custom_header_cannot_write(self):
        self.assertEqual(self.request("/api/stories", {}, "POST", {"Origin":"https://example.com"})[0], 403)
        self.assertEqual(self.request("/api/stories", {}, "POST", {"X-Little-Pages":""})[0], 403)
        self.assertEqual(self.request("/api/stories")[2]["stories"], [])

    def test_untrusted_host_cannot_read_data(self):
        self.assertEqual(self.request("/api/stories", headers={"Host":"untrusted.example"})[0], 403)

    def test_settings_are_read_only_over_http(self):
        self.assertEqual(self.request("/api/settings", {"letters":["z"]}, "PUT")[0], 404)
        self.assertEqual(self.request("/api/settings")[2]["letters"], list("masdt"))
        self.assertEqual(self.request("/api/settings")[2]["keyboard_letters"], list("abcdefghijklmnopqrstuvwxyz"))

    def test_archive_restore_workflow_retains_story_and_revision_history(self):
        story = self.request("/api/stories", {}, "POST")[2]
        path = "/api/stories/" + story["id"]
        self.assertEqual(self.request(path, {"text":"cat dog", "version":0}, "PUT")[0], 200)
        self.assertEqual(self.request(path + "/archive", {"archived":True, "version":1}, "POST")[0], 200)
        self.assertEqual(self.request("/api/stories")[2]["stories"], [])
        self.assertEqual(self.request("/api/stories?archived=1")[2]["stories"][0]["id"], story["id"])
        self.assertEqual(self.request(path)[2]["text"], "cat dog")
        self.assertEqual(len(self.request(path + "/revisions")[2]["revisions"]), 2)
        self.assertEqual(self.request(path, method="DELETE")[0], 501)
        self.assertFalse(self.request(path + "/archive", {"archived":False, "version":1}, "POST")[2]["archived"])
        self.assertEqual(self.request("/api/stories")[2]["stories"][0]["preview"], "cat dog")

    def test_archive_requires_valid_choice_version_and_origin(self):
        story = self.request("/api/stories", {}, "POST")[2]
        path = "/api/stories/" + story["id"] + "/archive"
        for body in ({"archived":1,"version":0}, {"archived":True,"version":True}, {"archived":True},
                     {"archived":False,"version":-1}, {"archived":True,"version":0,"extra":1}):
            self.assertEqual(self.request(path, body, "POST")[0], 400)
        self.assertEqual(self.request(path, {"archived":True,"version":0}, "PUT")[0], 405)
        self.assertEqual(self.request(path, {"archived":True,"version":0}, "POST", {"Origin":"https://example.com"})[0], 403)
        self.assertEqual(self.request(path, {"archived":True,"version":0}, "POST", {"X-Little-Pages":""})[0], 403)
        for query in ("?archived=true", "?archived=1&archived=0", "?archived=", "?all=1"):
            self.assertEqual(self.request("/api/stories" + query)[0], 400)
        self.assertEqual(len(self.request("/api/stories")[2]["stories"]), 1)

    def test_desktop_allows_only_bundled_choices_and_requires_normal_write_guards(self):
        status, _, desktop = self.request("/api/desktop")
        self.assertEqual(status, 200)
        self.assertEqual(desktop["wallpaper"], "hills")
        for choice in desktop["choices"]:
            status, headers, _ = self.request(choice["image"])
            self.assertEqual(status, 200)
            self.assertIn("image/svg+xml", headers["Content-Type"])
        self.assertEqual(self.request("/api/desktop", {"wallpaper":"flowers"}, "PUT")[2]["wallpaper"], "flowers")
        for value in (None, [], {}, 1, "https://example.com/image.jpg", "../../settings.json", "missing"):
            self.assertEqual(self.request("/api/desktop", {"wallpaper":value}, "PUT")[0], 400)
        self.assertEqual(self.request("/api/desktop", {"wallpaper":"space", "letters":["z"]}, "PUT")[0], 400)
        for headers in ({"Origin":"https://example.com"}, {"X-Little-Pages":""}):
            self.assertEqual(self.request("/api/desktop", {"wallpaper":"space"}, "PUT", headers)[0], 403)
        self.assertEqual(self.request("/api/desktop")[2]["wallpaper"], "flowers")
        self.assertEqual(self.request("/api/settings")[2]["letters"], list("masdt"))

    def test_static_files_cannot_escape_the_asset_folder(self):
        self.assertEqual(self.request("/%2e%2e/core.py")[0], 404)
        status, headers, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertIn(b"Toddler OS", body)

    def test_voice_unavailable_is_explicit_and_does_not_use_cloud_fallback(self):
        self.assertFalse(self.request("/api/settings")[2]["voice_ready"])
        self.assertEqual(self.request("/api/read", {"text":"mat"}, "POST")[0], 503)

    def test_read_response_keeps_wav_audio_and_carries_word_timings(self):
        self.app.speech = SimpleNamespace(render=lambda text: (b"RIFF-test", [[0, 3, .1, .5]]))
        status, headers, body = self.request("/api/read", {"text":"mat"}, "POST")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"RIFF-test")
        self.assertEqual(json.loads(headers["X-Little-Pages-Words"]), [[0, 3, .1, .5]])


if __name__ == "__main__":
    unittest.main()
