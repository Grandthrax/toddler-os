"""Story choices, saved copying, concurrency and app boundaries."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import wave

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from core import Problem,Settings,Store
from storybooks import PAGES,TEMPLATES,Storybooks,matches,prompts
import test_app


class StorybookTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
        self.store=Store(self.folder,Settings(self.folder/'settings.json'));self.books=Storybooks(self.store)
        self.book=self.books.create({'template':'space-cat'})

    def tearDown(self):self.temp.cleanup()

    def save(self,index,choice=None,text=None,finished=False):
        page=self.book['pages'][index];choice=choice or page['choices'][0]['id']
        target=next(item['text'] for item in page['choices'] if item['id']==choice)
        body={'choice':choice,'text':target if text is None else text,'finished':finished,'version':page['version']}
        self.book=self.books.save(self.book['id'],index,body);return body

    def test_picture_choices_saved_typing_and_finished_book_survive_restart(self):
        self.save(0,text='the spa')
        self.assertEqual(Storybooks(self.store).book(self.book['id']),self.book)
        for index,choice in enumerate(('cover','nap','star','blue-bed')):self.save(index,choice,finished=True)
        self.assertTrue(self.book['completed']);self.assertEqual(self.book['done'],4)
        self.assertTrue(self.book['pages'][2]['image'].endswith('/star.png'))
        self.assertEqual(Storybooks(self.store).library()['books'][0]['done'],4)

    def test_incorrect_copy_is_saved_but_cannot_finish_or_skip_a_page(self):
        self.save(0,text='the spase cat')
        with self.assertRaises(Problem):self.save(0,text='the spase cat',finished=True)
        with self.assertRaises(Problem):self.save(1,finished=True)
        self.assertEqual(self.books.book(self.book['id'])['pages'][0]['text'],'the spase cat')
        self.assertTrue(matches(' THE  SPACE cat! ','the space cat.'))
        self.assertFalse(matches('the cat space','the space cat.'))

    def test_typed_word_selects_the_story_and_retains_partial_answers(self):
        self.book=self.books.save(self.book['id'],0,{'answer':'the space cat','version':0,'finished':True})
        self.book=self.books.save(self.book['id'],1,{'answer':'na','version':0,'finished':False})
        self.assertEqual(self.book['pages'][1]['answer'],'na')
        self.assertIsNone(self.book['pages'][1]['choice'])
        self.assertEqual(Storybooks(self.store).book(self.book['id']),self.book)
        with self.assertRaises(Problem):self.books.save(self.book['id'],1,{'answer':'nope','version':1,'finished':True})
        body={'answer':'NAP ','version':1,'finished':False}
        self.book=self.books.save(self.book['id'],1,body)
        self.assertEqual(self.book['pages'][1]['choice'],'nap')
        self.assertEqual(self.book['pages'][1]['text'],'the cat can nap.')
        self.assertEqual(self.book['pages'][1]['answer'],'NAP ')
        self.assertEqual(self.books.save(self.book['id'],1,body),self.book)
        self.assertFalse(self.book['pages'][1]['finished'])
        with self.assertRaises(Problem):self.save(2,finished=True)
        self.book=self.books.save(self.book['id'],1,body|{'version':2,'finished':True})
        self.assertTrue(self.book['pages'][1]['finished'])
        self.assertEqual(self.book['pages'][1]['answer'],'NAP ')
        self.assertEqual(self.book['pages'][1]['text'],'the cat can nap.')
        self.assertEqual(Storybooks(self.store).book(self.book['id']),self.book)
        self.save(2,'star',finished=True)

    def test_fixed_pages_require_no_typing_but_cannot_skip_word_choices(self):
        body={'version':0,'finished':True}
        self.book=self.books.save(self.book['id'],0,body)
        self.assertTrue(self.book['pages'][0]['finished'])
        self.assertEqual(self.book['pages'][0]['text'],'the space cat.')
        self.assertIsNone(self.book['pages'][0]['answer'])
        self.assertEqual(self.books.save(self.book['id'],0,body),self.book)
        with self.assertRaises(Problem):self.books.save(self.book['id'],1,body)
        with self.assertRaises(Problem):self.books.save(self.book['id'],2,body)

    def test_old_copying_progress_and_revisions_survive_answer_column_migration(self):
        self.save(0,text='the spa')
        with self.store.connect() as db:
            for table in ('storybook_pages','storybook_revisions'):db.execute('ALTER TABLE '+table+' DROP COLUMN answer')
        migrated=Storybooks(self.store).book(self.book['id'])
        self.assertEqual(migrated['pages'][0]['text'],'the spa')
        self.assertIsNone(migrated['pages'][0]['answer'])
        self.assertEqual(migrated['pages'][1]['answer'],'')
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT text FROM storybook_revisions WHERE page=0 ORDER BY version DESC LIMIT 1').fetchone()[0],'the spa')



    def test_lost_response_retry_is_idempotent_and_stale_edits_conflict(self):
        body=self.save(0,text='the ')
        self.assertEqual(self.books.save(self.book['id'],0,body),self.book)
        with self.assertRaises(Problem) as error:self.books.save(self.book['id'],0,body|{'text':'the cat'})
        self.assertEqual(error.exception.status,409)
        self.assertEqual(error.exception.details['book'],self.book)
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM storybook_revisions WHERE page=0').fetchone()[0],2)

    def test_changing_picture_keeps_old_words_in_revisions_and_reopens_later_pages(self):
        for index in range(4):self.save(index,finished=True)
        self.save(1,'nap',text='',finished=False)
        self.assertFalse(self.book['completed']);self.assertFalse(self.book['pages'][2]['finished'])
        self.assertEqual(self.book['pages'][2]['text'],'the cat is on the moon.')
        with self.store.connect() as db:
            old=db.execute('SELECT choice,text FROM storybook_revisions WHERE book_id=? AND page=1 ORDER BY version',(self.book['id'],)).fetchall()
            self.assertIn(('hop','the cat can hop.'),[tuple(row) for row in old])

    def test_invalid_templates_pages_choices_and_payloads_do_not_write(self):
        for body in ({'template':'unknown'},{'template':'space-cat','extra':1}):
            with self.assertRaises(Problem):self.books.create(body)
        valid={'choice':'cover','text':'the','finished':False,'version':0}
        for change in ({'choice':[]},{'choice':'moon'},{'text':'<script>'},{'text':'a'*501},{'finished':1},{'version':True},{'extra':1}):
            with self.assertRaises(Problem):self.books.save(self.book['id'],0,valid|change)
        with self.assertRaises(Problem):self.books.save(self.book['id'],True,valid)
        with self.assertRaises(Problem):self.books.book('../settings')
        self.assertEqual(self.books.book(self.book['id']),self.book)

    def test_separate_books_and_existing_writing_are_preserved_in_backup(self):
        story=self.store.create();self.store.save(story['id'],'mat',0);self.store.set_wallpaper('space')
        second=self.books.create({'template':'space-cat'});self.save(0,text='the cat')
        self.assertEqual(self.books.book(second['id'])['pages'][0]['text'],'')
        self.assertEqual(self.store.story(story['id'])['text'],'mat')
        self.assertEqual(self.store.desktop()['wallpaper'],'space')
        restored=self.folder/'restored';restored.mkdir()
        with self.store.connect() as source,closing(sqlite3.connect(restored/'stories.sqlite3')) as target:source.backup(target)
        self.assertEqual(Storybooks(Store(restored,self.store.settings)).book(self.book['id']),self.book)

    def test_all_illustrations_and_spoken_words_are_bundled(self):
        folder=Path(__file__).resolve().parents[1]/'app/static/storybooks'
        manifest=json.loads((folder/'audio/manifest.json').read_text())
        self.assertEqual(set(manifest['prompts']),set(prompts()))
        for name,text in prompts().items():
            entry=manifest['prompts'][name];raw=(folder/'audio'/(name+'.wav')).read_bytes()
            self.assertEqual(entry['text'],text);self.assertEqual(hashlib.sha256(raw).hexdigest(),entry['sha256'])
            with wave.open(str(folder/'audio'/(name+'.wav'))) as audio:self.assertGreater(audio.getnframes(),100)
            if name.startswith('page-'):self.assertEqual(len(entry['words']),len(text.split()))
        for template in TEMPLATES.values():
            for choices in template['pages']:
                for item in choices:self.assertEqual((folder/item['image'].removeprefix('/storybooks/')).read_bytes()[:8],b'\x89PNG\r\n\x1a\n')

    def test_word_feedback_uses_natural_sentence_sources_without_runaway_duration(self):
        folder=Path(__file__).resolve().parents[1]/'app/static/storybooks/audio'
        manifest=json.loads((folder/'manifest.json').read_text())['prompts']
        for name,entry in manifest.items():
            if name.startswith('word-'):
                source=manifest[entry['source_page']]
                boundary=source['words'][entry['source_word']]
                self.assertEqual(source['text'][boundary[0]:boundary[1]],entry['text'])
                self.assertEqual(entry['recipe'],2)
                with wave.open(str(folder/(name+'.wav'))) as audio:
                    duration=audio.getnframes()/audio.getframerate()
                self.assertTrue(.15<duration<1.2,(name,duration))
                self.assertTrue(0<=entry['words'][0][2]<entry['words'][0][3]<=duration)
        with wave.open(str(folder/'page-moon.wav')) as audio:
            self.assertLess(audio.getnframes()/audio.getframerate(),3,'The moon page must be one continuous sentence')
        self.assertEqual(len(manifest['page-moon']['words']),6)


class StorybookHTTPTests(unittest.TestCase):
    setUp=test_app.HTTPTests.setUp
    tearDown=test_app.HTTPTests.tearDown
    request=test_app.HTTPTests.request

    def test_storybook_routes_require_normal_origin_and_version_guards(self):
        self.assertEqual(self.request('/api/storybooks')[2]['books'],[])
        self.assertEqual(self.request('/api/storybooks',{'template':'space-cat'},'POST',{'Origin':'https://example.com'})[0],403)
        status,_,book=self.request('/api/storybooks',{'template':'space-cat'},'POST');self.assertEqual(status,201)
        path='/api/storybooks/'+book['id']+'/pages/0'
        body={'version':0,'text':'the','choice':'cover','finished':False}
        self.assertEqual(self.request(path,body,'PUT')[0],200)
        self.assertEqual(self.request(path,body|{'text':'cat'},'PUT')[0],409)
        self.assertEqual(self.request(path,body,'POST')[0],405)
        self.assertEqual(self.request('/api/storybooks/'+book['id'])[2]['pages'][0]['text'],'the')


if __name__=='__main__':unittest.main()
