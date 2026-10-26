"""Mission solvability, interpreter branches, sequential rewards and durable drafts."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from core import Problem, Settings, Store
from mouse import MouseGame, execute, validate
from mouse_content import LEVELS, PATHS, prompts, seq
from server import Application
import test_app


class MouseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
        self.store=Store(self.folder,Settings(self.folder/'settings.json'));self.game=MouseGame(self.store)
    def tearDown(self):self.temp.cleanup()
    def solve(self,n):
        result=self.game.run({'level':n,'program':LEVELS[n-1]['solution']})
        self.assertTrue(result['success'],n)
        return self.game.complete({'run_id':result['id']})

    def test_all_45_missions_have_working_solutions_and_valid_cells(self):
        self.assertEqual(len(LEVELS),45)
        for level in LEVELS:
            validate(level['starter'],level)
            for garden in level['scenes']:
                self.assertEqual(len(garden['cells']),len(set(map(tuple,garden['cells']))))
                for group in ('cheese','keys','doors'):
                    self.assertTrue(all(p in garden['cells'] for p in garden[group]))
                self.assertTrue(execute(level['solution'],level,garden)['win'],level['level'])
            if level['level']>=21:self.assertGreaterEqual(len(level['scenes']),1)

    def test_choices_observe_both_truth_values_and_do_not_run_skipped_actions(self):
        for n,condition in ((30,'cheese'),(33,'path'),(37,'path'),(40,'left'),(42,'cheese')):
            level=LEVELS[n-1]
            values={frame['result'] for scene in level['scenes'] for frame in execute(level['solution'],level,scene)['trace'] if frame['event']=='check' and frame['condition']==condition}
            self.assertEqual(values,{True,False},n)
        empty=execute(LEVELS[28]['solution'],LEVELS[28],LEVELS[28]['scenes'][0])
        self.assertFalse(any(frame['event']=='pick' for frame in empty['trace']))
        for n in (30,33,36,37,38,39,40,41,42,43,44,45):
            # Dropping the condition cannot solve all the differing scenes by just
            # executing the reference true branch as an unconditional sequence.
            flat=[]
            for node in LEVELS[n-1]['solution']:flat.extend(node['yes'] if 'if' in node else [node])
            self.assertFalse(all(execute(flat,LEVELS[n-1],s)['win'] for s in LEVELS[n-1]['scenes']),n)

    def test_bumps_empty_paws_and_wrong_door_do_not_complete(self):
        for n,program in ((1,seq('RFF')),(24,seq('PFF')),(25,seq('FFOF'))):
            if n>1:
                with self.store.connect() as db:
                    for i in range(1,n):db.execute('INSERT OR IGNORE INTO mouse_completions VALUES(?,?)',(i,'test'))
                    for i in range(3,n,3):db.execute('INSERT OR IGNORE INTO mouse_rewards VALUES(?,?,?,?)',(i,'outfit',1,'test'))
            result=self.game.run({'level':n,'program':program});self.assertFalse(result['success'])
            with self.assertRaises(Problem):self.game.complete({'run_id':result['id']})

    def test_sequential_unlocks_and_all_twelve_rewards_once_only(self):
        with self.assertRaises(Problem):self.game.level(2)
        for n in range(1,len(LEVELS)+1):
            state=self.solve(n)
            if state['pending']:
                self.assertEqual(state['pending'],n)
                if n<len(LEVELS):
                    with self.assertRaises(Problem):self.game.level(n+1)
                branch=next(b for b in PATHS if state['earned'][b]<4)  # Max one path, then the next.
                body={'level':n,'branch':branch}
                state=self.game.reward(body);self.assertEqual(self.game.reward(body),state)
        self.assertEqual(state['earned'],dict.fromkeys(PATHS,4));self.assertIsNone(state['pending'])
        self.assertEqual(len(state['completed']),45)
        self.assertEqual(MouseGame(self.store).state(),state)

    def test_replay_and_concurrent_completion_do_not_farm_upgrades(self):
        result=self.game.run({'level':1,'program':seq('F')})
        with ThreadPoolExecutor(2) as pool:list(pool.map(self.game.complete,[{'run_id':result['id']}]*2))
        self.assertEqual(self.game.state()['completed'],[1])
        self.solve(1);self.assertEqual(self.game.state()['completed'],[1])
        self.assertEqual(self.game.state()['earned'],dict.fromkeys(PATHS,0))
        with self.assertRaises(Problem):self.game.reward({'level':3,'branch':'outfit'})
        with self.assertRaises(Problem):self.game.complete({'run_id':'forged'})

    def test_practice_is_inserted_after_ten_without_introducing_new_tools(self):
        self.assertEqual(LEVELS[9]['id'],'10')
        self.assertEqual(LEVELS[19]['id'],'11')
        self.assertEqual(len({l['id'] for l in LEVELS}),45)
        practice=LEVELS[10:19]
        self.assertEqual([l['chapter'] for l in practice],[1]*9)
        for level in practice:
            self.assertEqual(level['actions'],['forward','left','right'])
            self.assertEqual(level['conditions'],[])
            self.assertFalse(level['otherwise'])
            self.assertGreaterEqual(len(level['solution']),5)
            if level['starter']:
                self.assertFalse(execute(level['starter'],level,level['scenes'][0])['win'])
        self.assertEqual(sum(bool(l['starter']) for l in practice),3)
        self.assertEqual(LEVELS[27]['id'],'19')  # If still follows collecting.
        self.assertEqual(LEVELS[36]['id'],'28')  # Otherwise still follows If.

    def test_legacy_progress_drafts_runs_and_rewards_move_together_once(self):
        story=self.store.create();self.store.save(story['id'],'a cat sat',0)
        with self.store.connect() as db:
            db.execute('DELETE FROM mouse_meta')  # Original 36-mission schema.
            for n in range(1,19):db.execute('INSERT INTO mouse_completions VALUES(?,?)',(n,'old'))
            for index,n in enumerate(range(3,19,3)):
                db.execute('INSERT INTO mouse_rewards VALUES(?,?,?,?)',(n,PATHS[index//4],index%4+1,'old'))
            db.execute('INSERT INTO mouse_drafts VALUES(?,?,?)',(11,json.dumps(seq('FLF')),'old'))
            db.execute('INSERT INTO mouse_runs VALUES(?,?,?,?,?)',('receipt',18,'[]',1,'old'))
            db.execute('UPDATE mouse_equipped SET outfit=3,gadgets=1')
        game=MouseGame(self.store);state=game.state()
        self.assertEqual(state['completed'],list(range(1,11))+list(range(20,28)))
        self.assertEqual(state['next_level'],11)
        self.assertTrue(state['levels'][10]['unlocked'])
        self.assertFalse(state['levels'][11]['unlocked'])
        self.assertTrue(state['levels'][26]['unlocked'])  # Replays stay available.
        self.assertEqual(state['earned'],{'outfit':4,'gadgets':2,'magic':0})
        self.assertEqual(state['equipped'],{'outfit':3,'gadgets':1,'magic':0})
        self.assertEqual(game.level(20)['program'],seq('FLF'))
        self.assertEqual(game.level(11)['program'],[])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT level FROM mouse_runs WHERE id=?',('receipt',)).fetchone()[0],27)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertEqual(MouseGame(self.store).state(),state)
        self.assertEqual(self.store.story(story['id'])['text'],'a cat sat')

    def test_legacy_pending_reward_and_maxed_collection_do_not_block_practice(self):
        with self.store.connect() as db:
            db.execute('DELETE FROM mouse_meta')
            for n in range(1,13):db.execute('INSERT INTO mouse_completions VALUES(?,?)',(n,'old'))
            for n in (3,6,9):db.execute('INSERT INTO mouse_rewards VALUES(?,?,?,?)',(n,'outfit',n//3,'old'))
        game=MouseGame(self.store)
        self.assertEqual(game.state()['pending'],21)
        game.reward({'level':21,'branch':'outfit'})
        self.assertTrue(game.state()['levels'][10]['unlocked'])
        # A finished original collection must never demand a thirteenth item.
        with self.store.connect() as db:
            for n in range(1,46):db.execute('INSERT OR IGNORE INTO mouse_completions VALUES(?,?)',(n,'old'))
            for index,n in enumerate((24,27,30,33,36,39,42,45)):
                db.execute('INSERT INTO mouse_rewards VALUES(?,?,?,?)',(n,PATHS[1+index//4],index%4+1,'old'))
        state=game.state()
        self.assertIsNone(state['pending']);self.assertEqual(state['choices'],[])
        self.assertTrue(all(l['unlocked'] for l in state['levels']))

    def test_drafts_survive_restart_and_never_change_existing_writing(self):
        story=self.store.create();self.store.save(story['id'],'a cat sat',0)
        self.game.draft({'level':1,'program':seq('L')})
        self.assertEqual(MouseGame(self.store).level(1)['program'],seq('L'))
        self.assertNotIn('solution',self.game.level(1))
        self.assertEqual(self.store.story(story['id'])['text'],'a cat sat')
        with self.assertRaises(Problem):self.game.draft({'level':45,'program':[]})

    def test_bounded_interpreter_rejects_future_nested_or_malformed_blocks(self):
        bad=[None,{},[{}],[{'action':'fly'}],[{'action':[]}],seq('F'*50),[{'if':'path','yes':seq('F'),'no':[]}]]
        for program in bad:
            with self.assertRaises(Problem):validate(program,LEVELS[0])
        nested=[{'if':'path','yes':[{'if':'path','yes':[],'no':[]}],'no':[]}]
        with self.assertRaises(Problem):validate(nested,LEVELS[36])
        with self.assertRaises(Problem):validate([{'if':'path','yes':[],'no':seq('R')}],LEVELS[30])
        for n in (True,0,46,'1',None):
            with self.assertRaises(Problem):self.game.level(n)
        with self.assertRaises(Problem):self.game.equip({'outfit':1,'gadgets':0,'magic':0})

    def test_spoken_prompts_are_bundled_and_hashed(self):
        folder=Path(__file__).resolve().parents[1]/'app/static/mouse/audio'
        manifest=json.loads((folder/'manifest.json').read_text())['prompts']
        self.assertEqual(set(manifest),set(prompts()))
        for name,text in prompts().items():
            data=(folder/(name+'.wav')).read_bytes()
            self.assertEqual(data[:4],b'RIFF');self.assertGreater(len(data),1000)
            self.assertEqual(manifest[name]['text'],text)
            self.assertEqual(hashlib.sha256(data).hexdigest(),manifest[name]['sha256'])


class MouseHTTPTests(unittest.TestCase):
    setUp=test_app.HTTPTests.setUp
    tearDown=test_app.HTTPTests.tearDown
    request=test_app.HTTPTests.request
    def test_mouse_boundary_and_failed_attempts(self):
        self.assertEqual(self.request('/api/mouse')[0],200)
        self.assertEqual(self.request('/api/mouse/levels/45')[0],403)
        self.assertEqual(self.request('/api/mouse/run',{'level':1,'program':seq('R')},'POST',{'Origin':'https://elsewhere.example'})[0],403)
        self.assertEqual(self.request('/api/mouse/run',{'level':1,'program':[{'action':'fly'}]},'POST')[0],400)
        status,_,result=self.request('/api/mouse/run',{'level':1,'program':seq('F')},'POST')
        self.assertEqual(status,200);self.assertTrue(result['success'])
        self.assertEqual(self.request('/api/mouse/complete',{'run_id':result['id']},'POST')[0],200)
        self.assertEqual(self.request('/api/mouse/levels/2')[0],200)

