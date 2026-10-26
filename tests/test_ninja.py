"""Ninja Maths progress, retry, reward and data-isolation checks."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from core import Problem, Settings, Store
from ninja import NinjaGame, UPGRADES
from ninja_content import BRANCHES, ITEMS, LEVELS, expected, prompts, questions_for
import test_app


class NinjaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.store = Store(self.folder, Settings(self.folder / "settings.json"))
        self.game = NinjaGame(self.store)

    def tearDown(self):
        self.temp.cleanup()

    def answer_body(self, state, answer=None):
        return {"run_id": state["run_id"], "question_id": state["question"]["id"], "version": state["version"],
                "request_id": str(uuid.uuid4()), "answer": expected(state["question"]) if answer is None else answer}

    def finish(self, level=1):
        state = self.game.start(level)
        for _ in range(5):
            state = self.game.answer(self.answer_body(state))["state"]
        return state

    def test_start_and_restart_resume_the_same_real_questions(self):
        first = self.game.start()
        self.assertEqual(self.game.start(), first)
        self.assertFalse(first["next_level_unlocked"])
        self.assertEqual(len(first["question"]["choices"]), 3)
        self.assertIn(first["question"]["quantity"], first["question"]["choices"])
        second = self.game.answer(self.answer_body(first))["state"]
        reopened = NinjaGame(Store(self.folder, self.store.settings))
        self.assertEqual(reopened.state(), second)
        self.assertEqual(second["solved"], 1)
        self.assertEqual(second["question"]["kind"], "number")

    def test_wrong_answers_help_and_restart_keep_the_current_puzzle(self):
        state = self.game.start()
        wrong = self.game.answer(self.answer_body(state, 0))
        self.assertFalse(wrong["correct"])
        self.assertEqual(wrong["state"]["solved"], 0)
        state = wrong["state"]
        helped = self.game.help({"run_id":state["run_id"], "question_id":state["question"]["id"], "version":state["version"]})
        self.assertTrue(helped["question"]["hinted"])
        self.assertEqual(NinjaGame(self.store).state(), helped)
        self.assertFalse(helped["next_level_unlocked"])

    def test_duplicate_and_concurrent_answer_retries_advance_once(self):
        body = self.answer_body(self.game.start())
        with ThreadPoolExecutor(2) as pool:
            replies = list(pool.map(self.game.answer, [body, body]))
        self.assertTrue(all(r["correct"] for r in replies))
        self.assertEqual(self.game.state()["solved"], 1)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM ninja_answers").fetchone()[0], 1)

    def test_stale_or_changed_request_cannot_solve_a_different_puzzle(self):
        state = self.game.start(); body = self.answer_body(state)
        self.game.answer(body)
        for changed in (body | {"request_id":str(uuid.uuid4())}, body | {"answer":0}):
            with self.assertRaises(Problem) as error:
                self.game.answer(changed)
            self.assertEqual(error.exception.status, 409)
        self.assertEqual(self.game.state()["solved"], 1)

    def test_five_puzzles_unlock_next_level_and_pending_reward_survives_restart(self):
        final = self.finish()
        self.assertEqual(final["stage"], "reward")
        self.assertTrue(final["next_level_unlocked"])
        self.assertTrue(final["next_level_available"])
        self.assertEqual(len(final["upgrades"]), 3)
        self.assertEqual(NinjaGame(self.store).state(), final)
        self.assertEqual(self.game.start(), final)

    def test_reward_is_once_only_and_replays_do_not_create_another(self):
        self.finish()
        earned = self.game.reward({"upgrade":"spark-sword"})
        self.assertEqual(self.game.reward({"upgrade":"spark-sword"}), earned)
        self.finish()
        with self.assertRaises(Problem) as error:
            self.game.reward({"upgrade":"golden-guard"})
        self.assertEqual(error.exception.status, 409)
        self.assertEqual(self.game.state()["owned"], ["starter", "spark-sword"])

    def test_earned_equipment_survives_reopen_and_unearned_items_are_unavailable(self):
        with self.assertRaises(Problem):
            self.game.reward({"upgrade":"sun-cloak"})
        self.finish();self.game.reward({"upgrade":"sun-cloak"})
        self.assertEqual(self.game.equip({"upgrade":"starter"})["equipped"], "starter")
        self.assertEqual(self.game.equip({"upgrade":"sun-cloak"})["equipped"], "sun-cloak")
        self.assertEqual(NinjaGame(self.store).state()["equipped"], "sun-cloak")
        with self.assertRaises(Problem):
            self.game.equip({"upgrade":"golden-guard"})

    def test_game_does_not_change_stories_settings_or_wallpaper_and_backup_preserves_it(self):
        story = self.store.create();self.store.save(story["id"], "cat", 0)
        self.store.set_wallpaper("flowers");self.finish();self.game.reward({"upgrade":"golden-guard"})
        self.assertEqual(self.store.story(story["id"])["text"], "cat")
        self.assertEqual(len(self.store.revisions(story["id"])), 2)
        self.assertEqual(self.store.desktop()["wallpaper"], "flowers")
        self.assertEqual(self.store.settings.load()["letters"], list("masdt"))
        folder = self.folder / "restored";folder.mkdir()
        with self.store.connect() as db, closing(sqlite3.connect(folder / "stories.sqlite3")) as target:
            db.backup(target)
        restored = NinjaGame(Store(folder, self.store.settings))
        self.assertEqual(restored.state(), self.game.state())

    def test_invalid_answers_and_upgrade_choices_do_not_change_progress(self):
        state = self.game.start()
        for answer in (True, "4", [], {}, -1, 11, 1.5):
            with self.assertRaises(Problem):
                self.game.answer(self.answer_body(state, answer))
        for upgrade in ([], {}, True, "missing"):
            with self.assertRaises(Problem):
                self.game.reward({"upgrade":upgrade})
        self.assertEqual(self.game.state(), state)

    def test_all_ten_levels_unlock_in_order_with_pending_choice_and_restart(self):
        for level in range(1,11):
            with self.subTest(level=level):
                if level<10:
                    with self.assertRaises(Problem): self.game.start(level+1)
                state=self.game.start(level)
                self.assertEqual(state['level'],level)
                for _ in range(5):
                    question=state['question']
                    wrong=(expected(question)+1)%3 if question['kind']=='groups' else (expected(question)+1)%11
                    reply=self.game.answer(self.answer_body(state,wrong))
                    self.assertFalse(reply['correct']);self.assertEqual(reply['state']['solved'],state['solved'])
                    state=reply['state']
                    state=self.game.help({'run_id':state['run_id'],'question_id':question['id'],'version':state['version']})
                    self.assertTrue(state['question']['hinted'])
                    self.assertEqual(NinjaGame(self.store).state(),state)
                    state=self.game.answer(self.answer_body(state))['state']
                self.assertEqual(state['pending_level'],level)
                self.assertEqual(NinjaGame(self.store).start(),state)
                item=next(item for item in state['upgrades'] if item['branch']==BRANCHES[(level-1)%3])
                body={'upgrade':item['id'],'level':level}
                state=self.game.reward(body)
                self.assertEqual(self.game.reward(body),state)
                self.assertEqual(state['loadout'][item['branch']],item['rank'])
        self.assertTrue(state['chapter_complete'])
        self.assertEqual(state['earned'],{'sword':4,'armour':3,'power':3})
        self.assertTrue(all(level['status']=='completed' for level in state['levels'][:10]))
        rewards=state['rewards'].copy()
        for level in range(1,11):
            self.assertEqual(self.finish(level)['stage'],'complete')
        self.assertEqual(self.game.state()['rewards'],rewards)

    def test_each_path_stops_at_four_and_ten_missions_always_have_a_choice(self):
        # Enumerate the distinct earned-rank states, avoiding 3**10 duplicate paths.
        reachable={(0,0,0)}
        for completed in range(10):
            following=set()
            for ranks in reachable:
                choices=[item for item in UPGRADES if item['rank']==ranks[BRANCHES.index(item['branch'])]+1]
                self.assertGreaterEqual(len(choices),1)
                self.assertEqual({item['branch'] for item in choices},{branch for branch,rank in zip(BRANCHES,ranks) if rank<4})
                for item in choices:
                    changed=list(ranks);changed[BRANCHES.index(item['branch'])]+=1;following.add(tuple(changed))
            reachable=following
        self.assertIn((4,4,2),reachable)
        self.assertTrue(all(max(ranks)<=4 for ranks in reachable))

    def test_maxed_path_is_not_offered_and_cannot_earn_a_fifth_rank(self):
        for level in range(1,5):
            state=self.finish(level)
            item=next(item for item in state['upgrades'] if item['branch']=='sword')
            self.game.reward({'upgrade':item['id'],'level':level})
        state=self.finish(5)
        self.assertEqual(state['maxed'],['sword'])
        self.assertEqual({item['branch'] for item in state['upgrades']},{'armour','power'})
        with self.assertRaises(Problem): self.game.reward({'upgrade':'sword-5','level':5})
        self.assertEqual(self.game.state(),state)
        self.assertEqual(NinjaGame(self.store).state(),state)

    def test_legacy_high_ranks_keep_completion_and_reoffer_each_retired_reward_once(self):
        # A real old save could spend all ten rewards on a single branch.
        for level in range(1,11):
            state=self.finish(level)
            branch='sword' if level<=4 else 'armour' if level<=8 else 'power'
            item=next(item for item in state['upgrades'] if item['branch']==branch)
            self.game.reward({'upgrade':item['id'],'level':level})
        with self.store.connect() as db:
            db.execute("UPDATE ninja_rewards SET upgrade='sword-'||level WHERE level>4")
            db.execute("UPDATE ninja_loadout SET sword=10,armour=0,power=0 WHERE id=1")
            db.execute("UPDATE ninja_profile SET equipped='sword-10',reward='sword-10' WHERE id=1")
        self.game=NinjaGame(self.store)
        state=self.game.state()
        self.assertEqual(state['completed_level'],10)
        self.assertEqual(state['pending_level'],5)
        self.assertEqual(state['loadout']['sword'],4)
        self.assertEqual(state['equipped'],'sword-4')
        self.assertEqual(NinjaGame(self.store).state(),state)
        for level in range(5,11):
            item=next(item for item in state['upgrades'] if item['branch']==('armour' if level<9 else 'power'))
            body={'upgrade':item['id'],'level':level}
            state=self.game.reward(body)
            self.assertEqual(self.game.reward(body),state)
        self.assertTrue(state['chapter_complete'])
        self.assertEqual(state['earned'],{'sword':4,'armour':4,'power':2})
        self.assertEqual(NinjaGame(self.store).state(),state)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM ninja_retired_rewards').fetchone()[0],6)

    def test_catalogue_has_twelve_distinct_layer_assets_and_five_covered_bodies(self):
        import struct
        self.assertEqual(len(UPGRADES),12)
        self.assertEqual(len({item['image'] for item in UPGRADES}),12)
        folder=Path(__file__).resolve().parents[1]/'app/static/ninja/gear-v2'
        files=[folder/('body-'+str(n)+'.png') for n in range(5)]
        files += [folder/(branch+'-'+str(n)+'.png') for branch in ('sword','power') for n in range(1,5)]
        for file in files:
            raw=file.read_bytes()
            self.assertEqual(raw[:8],b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack('>II',raw[16:24]),(1024,1536))
            self.assertEqual(raw[25],6,'RGBA layer: '+file.name)

    def test_combined_equipment_and_old_tiers_survive_outfit_switches(self):
        for level,branch in enumerate(('sword','armour','power','sword'),1):
            state=self.finish(level);item=next(i for i in state['upgrades'] if i['branch']==branch)
            self.game.reward({'upgrade':item['id'],'level':level})
        self.assertEqual(self.game.state()['loadout'],{'sword':2,'armour':1,'power':1})
        self.assertEqual(self.game.equip({'upgrade':'spark-sword'})['loadout'],{'sword':1,'armour':1,'power':1})
        self.assertEqual(self.game.equip({'upgrade':'starter'})['loadout'],dict.fromkeys(BRANCHES,0))
        self.game.equip({'upgrade':'golden-guard'});state=self.game.equip({'upgrade':'sword-2'})
        self.assertEqual(state['loadout'],{'sword':2,'armour':1,'power':0})
        self.assertEqual(NinjaGame(self.store).state(),state)

    def test_switching_missions_keeps_partial_runs_and_stale_answers_cannot_cross_levels(self):
        self.finish();self.game.reward({'upgrade':'spark-sword'})
        state=self.game.start(2);body=self.answer_body(state)
        state=self.game.answer(body)['state'];run=state['run_id'];question=state['question']
        self.game.start(1)
        with self.assertRaises(Problem): self.game.answer(body|{'request_id':str(uuid.uuid4())})
        restored=self.game.start(2)
        self.assertEqual(restored['run_id'],run);self.assertEqual(restored['question'],question);self.assertEqual(restored['solved'],1)

    def test_original_prototype_migration_keeps_completed_reward_and_partial_replay(self):
        self.finish();self.game.reward({'upgrade':'sun-cloak'})
        partial=self.game.answer(self.answer_body(self.game.start(1)))['state']
        with self.store.connect() as db:
            for table in ('ninja_loadout','ninja_rewards','ninja_completions'): db.execute('DROP TABLE '+table)
            db.execute('ALTER TABLE ninja_runs DROP COLUMN level')
        migrated=NinjaGame(self.store).state()
        self.assertEqual(migrated['solved'],1);self.assertEqual(migrated['question'],partial['question'])
        self.assertEqual(migrated['rewards'],{'1':'sun-cloak'});self.assertEqual(migrated['loadout'],{'sword':0,'armour':0,'power':1})
        self.assertEqual(migrated['levels'][1]['status'],'ready')

    def test_original_pending_upgrade_and_old_saved_question_are_preserved(self):
        self.finish()
        with self.store.connect() as db:
            for table in ('ninja_loadout','ninja_rewards','ninja_completions'): db.execute('DROP TABLE '+table)
            db.execute('ALTER TABLE ninja_runs DROP COLUMN level')
        self.game=NinjaGame(self.store)
        self.assertEqual(self.game.state()['pending_level'],1)
        self.assertEqual(self.game.reward({'upgrade':'golden-guard'})['rewards'],{'1':'golden-guard'})
        state=self.game.start(1)
        old={'id':state['question']['id'],'quantity':4,'kind':'choice','choices':[3,4,5]}
        with self.store.connect() as db:
            questions=json.loads(db.execute('SELECT questions FROM ninja_runs WHERE id=?',(state['run_id'],)).fetchone()[0]);questions[0]=old
            db.execute('UPDATE ninja_runs SET questions=? WHERE id=?',(json.dumps(questions),state['run_id']))
        self.assertTrue(self.game.answer(self.answer_body(self.game.state()))['correct'])

    def test_authored_questions_are_unambiguous_in_range_and_have_offline_prompts(self):
        audio=prompts()
        tasks=set()
        for level in LEVELS:
            for q in questions_for(level['id'],'test'):
                tasks.add(q['task']);answer=expected(q)
                self.assertTrue(0<=answer<=(10 if level['id']<=10 else 20))
                if q['kind']=='groups': self.assertEqual(len(set(q['numbers'])),3)
                else:
                    self.assertEqual(len(set(q['choices'])),3);self.assertIn(answer,q['choices'])
                self.assertIn(q['audio'],audio);self.assertIn(q['help_audio'],audio)
        self.assertEqual(tasks,{'count','compare','add','missing','subtract','bonds'})

    def test_bundled_voice_manifest_matches_all_current_text_and_audio_hashes(self):
        import hashlib,wave
        folder=Path(__file__).resolve().parents[1]/'app/static/ninja/audio'
        manifest=json.loads((folder/'manifest.json').read_text())
        self.assertEqual(manifest['voice'],'en_GB-cori-high')
        for name,text in prompts().items():
            with self.subTest(prompt=name):
                self.assertEqual(manifest['prompts'][name]['text'],text)
                file=folder/(name+'.wav')
                self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),manifest['prompts'][name]['sha256'])
                with wave.open(str(file)) as audio:
                    self.assertEqual(audio.getframerate(),22050);self.assertGreater(audio.getnframes(),100)

    def test_invalid_level_reward_rank_and_late_duplicate_reward_cannot_skip_progress(self):
        for level in (True,0,11,1.5,[],{},'2'):
            with self.assertRaises(Problem): self.game.start(level)
        self.finish()
        with self.assertRaises(Problem): self.game.reward({'level':1,'upgrade':'sword-10'})
        self.game.reward({'upgrade':'spark-sword','level':1});self.finish(2)
        self.game.reward({'upgrade':'golden-guard','level':2})
        self.assertEqual(self.game.reward({'upgrade':'spark-sword','level':1})['rewards'],{'1':'spark-sword','2':'golden-guard'})
        with self.assertRaises(Problem): self.game.reward({'upgrade':'sun-cloak','level':2})


class NinjaHTTPTests(unittest.TestCase):
    setUp = test_app.HTTPTests.setUp
    tearDown = test_app.HTTPTests.tearDown
    request = test_app.HTTPTests.request
    def test_ninja_http_guards_and_start(self):
        self.assertEqual(self.request('/api/ninja')[2]['stage'], 'home')
        self.assertEqual(self.request('/api/ninja/start', {}, 'POST', {'Origin':'https://example.com'})[0], 403)
        self.assertEqual(self.request('/api/ninja/start', {}, 'POST', {'X-Little-Pages':''})[0], 403)
        self.assertEqual(self.request('/api/ninja/start', {'level':2}, 'POST')[0], 409)
        self.assertEqual(self.request('/api/ninja/start', {'level':None}, 'POST')[0], 400)
        self.assertEqual(self.request('/api/ninja/start', {}, 'POST')[2]['stage'], 'question')
        self.assertEqual(self.request('/api/ninja/reward', {'upgrade':'spark-sword'}, 'POST')[0], 409)

    def test_ninja_assets_and_prompts_are_local_and_readable(self):
        import io,wave
        for item in UPGRADES[:1]+[ITEMS['golden-guard'],ITEMS['sun-cloak'],{'image':'/ninja/hero-starter.png'}]:
            status, headers, raw = self.request(item['image'])
            self.assertEqual(status, 200)
            self.assertEqual(raw[:8], b'\x89PNG\r\n\x1a\n')
        for name in ('choice','number','match','try-again','correct','reward','help-10','earned-spark-sword'):
            status, headers, raw = self.request('/ninja/audio/'+name+'.wav')
            self.assertEqual(status, 200)
            with wave.open(io.BytesIO(raw)) as audio:
                self.assertGreater(audio.getnframes(), 100)


if __name__ == '__main__':
    unittest.main()
