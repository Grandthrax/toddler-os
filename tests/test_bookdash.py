"""Licensed book integrity, untouched wordless edition and typed adaptations."""
from itertools import product
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from core import Problem,Settings,Store
from storybooks import Storybooks,prompts
from bookdash_content import TEMPLATES,COME_TEXT


class BookDashTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();folder=Path(self.temp.name)
        self.store=Store(folder,Settings(folder/'settings.json'));self.books=Storybooks(self.store)

    def tearDown(self):self.temp.cleanup()

    def finish(self,book,answers):
        for page in book['pages']:
            body={'version':page['version'],'finished':True}
            if page['decision']:body['answer']=next(answers)
            book=self.books.save(book['id'],page['page'],body)
        return book

    def test_all_adaptation_branches_finish_preserving_selected_words_and_pictures(self):
        for template in TEMPLATES.values():
            if template['edition']!='adaptation':continue
            for path in product(*[page for page in template['pages'] if len(page)>1]):
                book=self.books.create({'template':template['id']})
                book=self.finish(book,iter(choice['answer'] for choice in path))
                self.assertTrue(book['completed'])
                self.assertEqual([p['answer'] for p in book['pages'] if p['decision']],[c['answer'] for c in path])
                self.assertEqual([p['image'] for p in book['pages'] if p['decision']],[c['image'] for c in path])
                self.assertEqual(self.books.book(book['id']),book)

    def test_original_wordless_edition_never_invents_text_or_page_narration(self):
        book=self.books.create({'template':'wheres-that-cat-look'})
        self.assertEqual(book['edition'],'wordless');self.assertEqual(book['total'],13)
        self.assertTrue(all(not p['target'] and not p['decision'] for p in book['pages']))
        self.assertFalse(any(key.startswith('page-bd-where-look') or key=='page-bd-where-cover' for key in prompts()))
        book=self.finish(book,iter(()));self.assertTrue(book['completed'])
        self.assertTrue(all(not page['text'] for page in book['pages']))

    def test_reading_edition_preserves_original_text_and_picture_only_spreads(self):
        book=self.books.create({'template':'come-back-cat-read'})
        self.assertEqual([p['target'] for p in book['pages'][1:]],COME_TEXT)
        self.assertFalse(any(p['decision'] for p in book['pages']))
        with self.assertRaises(Problem):self.books.save(book['id'],1,{'version':0,'finished':True})
        self.assertTrue(self.finish(book,iter(()))['completed'])

    def test_every_licensed_edition_exposes_creators_and_adaptation_notice(self):
        for template in TEMPLATES.values():
            book=self.books.create({'template':template['id']});credit=book['credits']
            self.assertEqual(credit['license'],'CC BY 4.0')
            self.assertTrue(credit['source'].startswith('https://bookdash.org/books/'))
            self.assertGreaterEqual(len(credit['creators']),3)
            self.assertTrue(credit['changes'])
            summary=next(t for t in self.books.library()['templates'] if t['id']==template['id'])
            self.assertEqual(summary['edition'],template['edition']);self.assertTrue(summary['licensed'])

    def test_original_download_hashes_match_and_no_external_runtime_images(self):
        folder=Path(__file__).resolve().parents[1]/'app/static/storybooks/bookdash'
        manifest=json.loads((folder/'download-manifest.json').read_text())
        for entry in manifest['assets']:
            self.assertEqual(hashlib.sha256((folder/entry['file']).read_bytes()).hexdigest(),entry['sha256'])
        files={entry['file'] for entry in manifest['assets']}
        for template in TEMPLATES.values():
            for page in template['pages']:
                for item in page:
                    self.assertTrue(item['image'].startswith('/storybooks/bookdash/'))
                    self.assertIn(item['image'].rsplit('/',1)[1],files)

    def test_contracted_words_are_single_spoken_tokens(self):
        words=prompts()
        self.assertEqual(words['word-thats'],'that’s')
        self.assertEqual(words['word-dont'],'don’t')
        self.assertEqual(words['word-its'],'it’s')
        self.assertNotIn('word-s',words)


if __name__=='__main__':unittest.main()
