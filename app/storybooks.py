"""Typed story choices and versioned illustrated books, separate from free writing."""
import re
import uuid

from core import Problem, Store, now


def option(identifier, text, image, answer):
    return {"id":identifier,"text":text,"image":"/storybooks/"+image+".png","answer":answer}


PAGES = [
    [option("cover", "the space cat.", "cover", "the space cat")],
    [option("hop", "the cat can hop.", "hop", "hop"), option("nap", "the cat can nap.", "nap", "nap")],
    [option("moon", "the cat is on the moon.", "moon", "moon"), option("star", "the cat is on a star.", "star", "star")],
    [option("red-bed", "the cat has a red bed.", "red-bed", "red"), option("blue-bed", "the cat has a blue bed.", "blue-bed", "blue")],
]
STEMS = ('the space cat.', 'the cat can …', 'the cat is on …', 'the cat has a … bed.')
TEMPLATE = {"id":"space-cat","title":"The Space Cat","image":"/storybooks/cover.png","pages":PAGES,
            "description":"A little cat. A very big adventure.","stems":STEMS,
            "instructions":(None,'choose-1','choose-2','choose-3')}
LUCIANA_PAGES = [
    [option('luciana-mat','luciana sat on the mat.','luciana/mat','mat'),
     option('luciana-hat','luciana sat on the hat.','luciana/hat','hat')],
    [option('luciana-cat','luciana pat the cat.','luciana/cat','cat'),
     option('luciana-rat','luciana pat the rat.','luciana/rat','rat')],
    [option('luciana-drink','luciana ran to the drink.','luciana/drink','drink'),
     option('luciana-sock','luciana ran to the sock.','luciana/sock','sock')],
    [option('luciana-sad','luciana was sad.','luciana/sad','sad'),
     option('luciana-mad','luciana was mad.','luciana/mad','mad')],
    [option('luciana-dad','dad was the best fun.','luciana/dad','dad was the best fun')],
]
TEMPLATES = {'space-cat':TEMPLATE,'luciana-and-dad':{
    'id':'luciana-and-dad','title':'Luciana and Dad','image':'/storybooks/luciana/dad.png',
    'description':'A little adventure. A happy ending with Dad.','pages':LUCIANA_PAGES,
    'stems':('luciana sat on the …','luciana pat the …','luciana ran to the …','luciana was …','dad was the best fun.'),
    'instructions':tuple('choose-luciana-'+str(index) for index in range(4))+(None,),
}}


def matches(text, target):
    return re.findall(r"[a-z]+",text.lower()) == re.findall(r"[a-z]+",target.lower())


def prompts():
    result={"welcome":"Make your own storybook. Type a word to choose what happens next. Your picture will appear and I will read the page. Then choose what happens next.",
            "choose":"What happens next? Type one of the words. Press space or enter to see your picture and hear the next page.",
            "choose-1":"What can the cat do? Type hop or nap. Then press space or enter.",
            "choose-2":"Where does the cat go? Type moon or star. Then press space or enter.",
            "choose-3":"What colour is the bed? Type red or blue. Then press space or enter.",
            "copy":"Copy the words above. Each letter has a sound. Press the space bar to hear your word. Tap the arrow when you have finished.",
            "finished":"You made your own book! Tap the speaker to hear it, or turn the pages.",
            "help":"Type one of the words above. Look at the glowing letter. You can use backspace to change a letter.",
            "conflict":"Your book has newer saved words. Your typing is safe here too. Ask a grown-up to help you choose which words to keep."}
    for index,text in enumerate((
        'What did Luciana sit on? Type mat or hat. Then press space or enter.',
        'What did Luciana pat? Type cat or rat. Then press space or enter.',
        'What did Luciana run to? Type drink or sock. Then press space or enter.',
        'How did Luciana feel? Type sad or mad. Then press space or enter.',
    )):result['choose-luciana-'+str(index)]=text
    for template in TEMPLATES.values():
        for choices in template['pages']:
            for choice in choices:
                result["page-"+choice["id"]]=choice["text"]
                for word in re.findall(r"[a-z]+",choice["text"]):result["word-"+word]=word
    return result


class Storybooks:
    def __init__(self, store):
        self.store=store
        with store.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS storybook_books (
                    id TEXT PRIMARY KEY, template TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS storybook_pages (
                    book_id TEXT NOT NULL REFERENCES storybook_books(id), page INTEGER NOT NULL,
                    choice TEXT, text TEXT NOT NULL DEFAULT '', version INTEGER NOT NULL DEFAULT 0,
                    finished INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(book_id,page)
                );
                CREATE TABLE IF NOT EXISTS storybook_revisions (
                    id INTEGER PRIMARY KEY, book_id TEXT NOT NULL, page INTEGER NOT NULL,
                    choice TEXT, text TEXT NOT NULL, version INTEGER NOT NULL, finished INTEGER NOT NULL,
                    created TEXT NOT NULL, UNIQUE(book_id,page,version),
                    FOREIGN KEY(book_id,page) REFERENCES storybook_pages(book_id,page)
                );
            """)
            migrating_pages=False
            for table in ('storybook_pages','storybook_revisions'):
                if 'answer' not in {row[1] for row in db.execute('PRAGMA table_info('+table+')')}:
                    db.execute('ALTER TABLE '+table+' ADD COLUMN answer TEXT')
                    migrating_pages=migrating_pages or table=='storybook_pages'
            # Existing partial copied sentences remain available in the old
            # writing mode. Empty pages can immediately use typed word choices.
            # NULL also marks a confirmed choice awaiting its full-page copy.
            # Only convert empty legacy pages when first adding this column.
            if migrating_pages:
                db.execute("UPDATE storybook_pages SET answer='' WHERE answer IS NULL AND text='' AND finished=0")

    def library(self):
        with self.store.connect() as db:
            books=[]
            for row in db.execute('SELECT id,created,updated FROM storybook_books ORDER BY updated DESC,id'):
                book=self.book(row['id'],db)
                books.append({k:book[k] for k in ('id','title','image','created','updated','completed','done','total')})
            return {"templates":[{k:template[k] for k in ('id','title','image','description')} for template in TEMPLATES.values()],"books":books}

    def book(self, identifier, db=None):
        identifier=Store.identifier(identifier)
        if db is None:
            with self.store.connect() as db:return self.book(identifier,db)
        row=db.execute('SELECT * FROM storybook_books WHERE id=?',(identifier,)).fetchone()
        if row is None:raise Problem('That book could not be found.',404)
        template=TEMPLATES[row['template']]
        pages=[]
        for saved in db.execute('SELECT * FROM storybook_pages WHERE book_id=? ORDER BY page',(identifier,)):
            page=dict(saved);page.pop('book_id');page['finished']=bool(page['finished'])
            page['choices']=template['pages'][page['page']]
            chosen=next((item for item in page['choices'] if item['id']==page['choice']),None)
            page.update(target=chosen['text'] if chosen else '',image=chosen['image'] if chosen else None,
                        matches=bool(chosen and matches(page['text'],chosen['text'])),stem=template['stems'][page['page']],
                        decision=len(page['choices'])>1,instruction=template['instructions'][page['page']])
            pages.append(page)
        done=sum(page['finished'] for page in pages)
        return dict(row)|{"title":template['title'],"image":template['image'],"pages":pages,
                          "done":done,"total":len(template['pages']),"completed":done==len(template['pages'])}

    def create(self, body):
        if set(body)!={'template'} or not isinstance(body['template'],str) or body['template'] not in TEMPLATES:raise Problem('Choose one of your picture books.')
        template=TEMPLATES[body['template']]
        identifier=str(uuid.uuid4());stamp=now()
        with self.store.connect() as db:
            db.execute('INSERT INTO storybook_books VALUES(?,?,?,?)',(identifier,template['id'],stamp,stamp))
            for index,choices in enumerate(template['pages']):
                # Covers and fixed endings are read aloud without typing.
                answer='' if len(choices)>1 else None
                db.execute('INSERT INTO storybook_pages(book_id,page,choice,answer) VALUES(?,?,?,?)',
                           (identifier,index,choices[0]['id'] if len(choices)==1 else None,answer))
                self.revision(db,identifier,index)
            return self.book(identifier,db)

    @staticmethod
    def revision(db,identifier,index):
        row=db.execute('SELECT book_id,page,choice,text,version,finished,answer FROM storybook_pages WHERE book_id=? AND page=?',
                       (identifier,index)).fetchone()
        db.execute('INSERT INTO storybook_revisions(book_id,page,choice,text,version,finished,answer,created) VALUES(?,?,?,?,?,?,?,?)',
                   (*tuple(row),now()))

    def save(self, identifier, index, body):
        typed=set(body)=={'answer','version','finished'}
        fixed=set(body)=={'version','finished'}
        if not typed and not fixed and set(body)!={'choice','text','version','finished'}:raise Problem('Save one picture page at a time.')
        if type(index) is not int or index<0:raise Problem('Choose a page in your book.',404)
        if type(body['version']) is not int or body['version']<0 or type(body['finished']) is not bool:raise Problem('That page save could not be read.')
        writing=body['answer'] if typed else '' if fixed else body['text']
        if not isinstance(writing,str) or len(writing)>500 or re.search(r"[^A-Za-z \n.,!?'-]",writing):raise Problem('Use letters and spaces for your story.')
        identifier=Store.identifier(identifier)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');book=self.book(identifier,db)
            if index>=book['total']:raise Problem('Choose a page in your book.',404)
            page=book['pages'][index];choices=page['choices']
            if fixed and (page['decision'] or not body['finished']):raise Problem('Type one of the words on this page.')
            if not typed and not fixed and (not isinstance(body['choice'],str) or body['choice'] not in {item['id'] for item in choices}):raise Problem('Choose one of the words on this page.')
            if any(not previous['finished'] for previous in book['pages'][:index]):raise Problem('Finish the earlier pages first.',409,book=book)
            if typed:
                selected=next((item for item in choices if matches(writing,item['answer'])),None)
                if body['finished'] and not selected:raise Problem('Type one of the words above before turning the page.')
                saved={'choice':selected['id'] if selected else None,'text':selected['text'] if selected else '',
                       'answer':writing,'finished':body['finished']}
            elif fixed:saved={'choice':choices[0]['id'],'text':choices[0]['text'],'answer':None,'finished':True}
            else:saved={key:body[key] for key in ('choice','text','finished')}|{'answer':None}
            same=all(page[key]==saved[key] for key in ('choice','text','answer','finished'))
            if page['version']!=body['version']:
                if same and page['version']==body['version']+1:return book
                raise Problem('This page has newer saved words. Your typing is still here.',409,book=book)
            if same:return book
            if not typed and not fixed:
                target=next(item['text'] for item in choices if item['id']==body['choice'])
                if body['finished'] and not matches(body['text'],target):raise Problem('Copy the words above before turning the page.')
            if page['finished'] and not body['finished']:
                # Editing an earlier page reopens later pages without erasing them.
                db.execute('UPDATE storybook_pages SET finished=0,version=version+1 WHERE book_id=? AND page>? AND finished=1',(identifier,index))
                for later in book['pages'][index+1:]:
                    if later['finished']:self.revision(db,identifier,later['page'])
            db.execute('UPDATE storybook_pages SET choice=?,text=?,answer=?,version=version+1,finished=? WHERE book_id=? AND page=?',
                       (saved['choice'],saved['text'],saved['answer'],int(saved['finished']),identifier,index))
            self.revision(db,identifier,index)
            db.execute('UPDATE storybook_books SET updated=? WHERE id=?',(now(),identifier))
            return self.book(identifier,db)
