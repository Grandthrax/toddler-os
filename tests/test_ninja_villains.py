"""Chapter two: sequential battles, durable once-only trophies and retries."""
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from core import Settings,Store,Problem
from ninja import NinjaGame
from ninja_content import expected,LEVELS,DEFEATS


class VillainTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        folder=Path(self.temp.name)
        self.store=Store(folder,Settings(folder/'settings.json'))
        self.game=NinjaGame(self.store)

    def tearDown(self):
        self.temp.cleanup()

    def finish(self,level):
        state=self.game.start(level)
        for _ in range(5):
            state=self.game.answer({'run_id':state['run_id'],'question_id':state['question']['id'],
                'version':state['version'],'answer':expected(state['question']),
                'request_id':str(uuid.uuid4())})['state']
        return state

    def training(self):
        for level in range(1,11):
            state=self.finish(level)
            self.game.reward({'upgrade':state['upgrades'][0]['id'],'level':level})

    def test_twenty_missions_unlock_and_trophies_survive_restart(self):
        self.training()
        original=self.game.state()['loadout']
        for level in range(11,21):
            with self.assertRaises(Problem):self.game.start(level+1)
            state=self.finish(level)
            self.assertEqual(state['stage'],'battle')
            self.assertEqual(NinjaGame(self.store).state()['battle_level'],level)
            self.assertEqual(self.game.start()['stage'],'battle')
            body={'level':level,'method':DEFEATS[(level-11)%3]['id']}
            state=self.game.defeat(body)
            self.assertEqual(self.game.defeat(body),state)
            self.assertEqual(len(state['trophies']),level-10)
            self.assertEqual(state['loadout'],original)
            self.assertEqual(NinjaGame(self.store).state()['trophies'],state['trophies'])
            with self.assertRaises(Problem):self.game.defeat(body|{'method':'invalid'})
        self.assertTrue(state['campaign_complete'])
        self.assertFalse(state['next_level_available'])
        self.assertEqual(self.finish(11)['stage'],'complete')
        self.assertEqual(len(self.game.state()['trophies']),10)

    def test_unearned_and_malformed_defeats_never_award_trophies(self):
        for body in ({'level':11,'method':'sword'},{'level':True,'method':'sword'},
                     {'level':11,'method':[]},{'level':21,'method':'sword'},
                     {'level':11,'method':'sword','extra':True}):
            with self.assertRaises(Problem):self.game.defeat(body)
        self.assertEqual(self.game.state()['trophies'],[])

    def test_each_villain_has_unique_original_art_and_its_trophy(self):
        root=Path(__file__).resolve().parents[1]/'app/static'
        images=set()
        for level in LEVELS[10:]:
            for key in ('image','trophy_image'):
                path=root/level['villain'][key].lstrip('/')
                self.assertTrue(path.is_file())
                images.add(path.read_bytes())
        self.assertEqual(len(images),20)
