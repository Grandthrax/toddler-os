"""Bounded block interpreter and durable, sequential Mouse Missions progress."""
from copy import deepcopy
import json
import uuid
from core import Problem, now
from mouse_content import ACTIONS, CONDITIONS, PATHS, CHAPTERS, LEVELS, UPGRADE_NAMES


def validate(program, level):
    if not isinstance(program,list) or len(program)>level['limit']:
        raise Problem('Choose a short programme using the picture blocks.')
    total=0;conditions=set()
    for node in program:
        if not isinstance(node,dict):raise Problem('Choose a picture block.')
        if set(node)=={'action'} and node['action'] in level['actions']:
            total+=1;continue
        if set(node)!={'if','yes','no'} or node['if'] not in level['conditions']:
            raise Problem('That question is waiting for a later mission.')
        conditions.add(node['if']);total+=1
        for side in ('yes','no'):
            if not isinstance(node[side],list) or len(node[side])>12:raise Problem('Keep the question branches short.')
            if side=='no' and node[side] and not level['otherwise']:raise Problem('Otherwise comes in the next chapter.')
            for action in node[side]:
                if not isinstance(action,dict) or set(action)!={'action'} or action['action'] not in level['actions']:
                    raise Problem('Put movement or paw blocks inside a question.')
                total+=1
    if total>40:raise Problem('That programme has too many blocks. Try a shorter route.')
    return conditions


def execute(program, level, garden):
    validate(program,level)
    x,y,d=garden['start'];cheese=deepcopy(garden['cheese']);keys=deepcopy(garden['keys']);doors=deepcopy(garden['doors'])
    bag=False;trace=[];reason=None
    def position(direction=d):return [x+((1,0),(0,1),(-1,0),(0,-1))[direction][0],y+((1,0),(0,1),(-1,0),(0,-1))[direction][1]]
    def clear(direction):return position(direction) in garden['cells'] and position(direction) not in doors
    def snapshot(node,event,**extra):
        trace.append({'node':node,'event':event,'x':x,'y':y,'direction':d,'cheese':deepcopy(cheese),'keys':deepcopy(keys),'doors':deepcopy(doors),'bag':bag,**extra})
    snapshot([], 'start')
    def act(action,node):
        nonlocal x,y,d,bag,reason
        if action=='forward':
            if not clear(d):reason='bump'
            else:x,y=position(d)
        elif action=='left':d=(d-1)%4
        elif action=='right':d=(d+1)%4
        elif action=='pick':
            if [x,y] in cheese:cheese.remove([x,y])
            elif [x,y] in keys:keys.remove([x,y]);bag=True
            else:reason='empty'
        elif action=='open':
            if not bag or position(d) not in doors:reason='door'
            else:doors.remove(position(d))
        snapshot(node,reason or action)
    for index,node in enumerate(program):
        if 'action' in node:act(node['action'],[index])
        else:
            condition=node['if']
            value={'cheese':[x,y] in cheese,'path':clear(d),'key':bag,'left':clear((d-1)%4)}[condition]
            snapshot([index],'check',condition=condition,result=value)
            side='yes' if value else 'no'
            for child,action in enumerate(node[side]):
                act(action['action'],[index,side,child])
                if reason:break
        if reason:break
    win=(not reason and [x,y]==garden['goal'] and not keys and not doors and (not garden['collect'] or not cheese))
    snapshot([],'finish',win=bool(win),reason=reason or ('win' if win else 'unfinished'))
    return {'win':bool(win),'trace':trace}


class MouseGame:
    def __init__(self,store):
        self.store=store
        with store.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS mouse_drafts(level INTEGER PRIMARY KEY,program TEXT NOT NULL,updated TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS mouse_runs(id TEXT PRIMARY KEY,level INTEGER NOT NULL,program TEXT NOT NULL,success INTEGER NOT NULL,created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS mouse_completions(level INTEGER PRIMARY KEY,created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS mouse_rewards(level INTEGER PRIMARY KEY REFERENCES mouse_completions(level),branch TEXT NOT NULL,rank INTEGER NOT NULL,created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS mouse_equipped(id INTEGER PRIMARY KEY CHECK(id=1),outfit INTEGER NOT NULL DEFAULT 0,gadgets INTEGER NOT NULL DEFAULT 0,magic INTEGER NOT NULL DEFAULT 0);
            INSERT OR IGNORE INTO mouse_equipped(id) VALUES(1);
            CREATE TABLE IF NOT EXISTS mouse_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            ''')
            # Version 1 used the original 36 display numbers as identities. Move
            # every saved reference together, once, without marking practice done.
            db.execute('BEGIN IMMEDIATE')
            if not db.execute("SELECT 1 FROM mouse_meta WHERE key='curriculum'").fetchone():
                db.execute('PRAGMA defer_foreign_keys=ON')
                for table in ('mouse_completions','mouse_rewards','mouse_drafts','mouse_runs'):
                    db.execute(f'UPDATE {table} SET level=level+1000 WHERE level>10')
                    db.execute(f'UPDATE {table} SET level=level-991 WHERE level>1010')
                db.execute("INSERT INTO mouse_meta VALUES('curriculum','2')")

    def state(self,db=None):
        if db is None:
            with self.store.connect() as db:return self.state(db)
        completed=[row[0] for row in db.execute('SELECT level FROM mouse_completions ORDER BY level')]
        rewards={row['level']:dict(row) for row in db.execute('SELECT * FROM mouse_rewards ORDER BY level')}
        earned={branch:sum(row['branch']==branch for row in rewards.values()) for branch in PATHS}
        pending=next((n for n in completed if n%3==0 and n not in rewards),None) if any(earned[b]<4 for b in PATHS) else None
        next_level=next((n['level'] for n in LEVELS if n['level'] not in completed),len(LEVELS))
        equipped=dict(db.execute('SELECT outfit,gadgets,magic FROM mouse_equipped WHERE id=1').fetchone())
        return {'completed':completed,'next_level':next_level,'pending':pending,'earned':earned,'equipped':equipped,
                'chapters':list(CHAPTERS),'choices':[{'branch':b,'rank':earned[b]+1,'name':UPGRADE_NAMES[b][earned[b]]} for b in PATHS if earned[b]<4],
                'levels':[{'level':n['level'],'title':n['title'],'chapter':n['chapter'],'completed':n['level'] in completed,
                           'unlocked':n['level'] in completed or (n['level']==next_level and not pending)} for n in LEVELS]}

    def available(self,number,db):
        if type(number) is not int or not 1<=number<=len(LEVELS):raise Problem('Choose a numbered mission from the map.')
        if not self.state(db)['levels'][number-1]['unlocked']:raise Problem('Finish the earlier mission and choose its upgrade first.',403)
        return LEVELS[number-1]

    def level(self,number):
        with self.store.connect() as db:
            level=self.available(number,db)
            row=db.execute('SELECT program FROM mouse_drafts WHERE level=?',(number,)).fetchone()
            return {k:deepcopy(v) for k,v in level.items() if k!='solution'} | {'program':json.loads(row[0]) if row else deepcopy(level['starter'])}

    def draft(self,body):
        if set(body)!={'level','program'}:raise Problem('Choose a mission and programme.')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');level=self.available(body['level'],db);validate(body['program'],level)
            db.execute('INSERT INTO mouse_drafts VALUES(?,?,?) ON CONFLICT(level) DO UPDATE SET program=excluded.program,updated=excluded.updated',(body['level'],json.dumps(body['program']),now()))
        return {'saved':True}

    def run(self,body):
        if set(body)!={'level','program'}:raise Problem('Choose a mission and programme.')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');level=self.available(body['level'],db)
            used=validate(body['program'],level)
            results=[execute(body['program'],level,garden) for garden in level['scenes']]
            required=set(level['conditions'])<=used
            success=bool(body['program']) and all(r['win'] for r in results) and required
            run_id=str(uuid.uuid4())
            db.execute('INSERT INTO mouse_runs VALUES(?,?,?,?,?)',(run_id,body['level'],json.dumps(body['program']),int(success),now()))
            db.execute('INSERT INTO mouse_drafts VALUES(?,?,?) ON CONFLICT(level) DO UPDATE SET program=excluded.program,updated=excluded.updated',(body['level'],json.dumps(body['program']),now()))
            # Keep a bounded set of attempt receipts; completions and rewards are separate.
            db.execute('DELETE FROM mouse_runs WHERE id IN (SELECT id FROM mouse_runs ORDER BY rowid DESC LIMIT -1 OFFSET 100)')
            return {'id':run_id,'success':success,'needs_question':not required,'gardens':results}

    def complete(self,body):
        if set(body)!={'run_id'} or not isinstance(body['run_id'],str):raise Problem('Run your programme first.')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT level,success FROM mouse_runs WHERE id=?',(body['run_id'],)).fetchone()
            if not row or not row['success']:raise Problem('Keep trying your programme. You can do it.',409)
            self.available(row['level'],db)
            db.execute('INSERT OR IGNORE INTO mouse_completions VALUES(?,?)',(row['level'],now()))
            return self.state(db)

    def reward(self,body):
        if set(body)!={'level','branch'} or type(body['level']) is not int or body['branch'] not in PATHS:raise Problem('Choose a pictured upgrade.')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');state=self.state(db)
            old=db.execute('SELECT branch FROM mouse_rewards WHERE level=?',(body['level'],)).fetchone()
            if old:
                if old[0]!=body['branch']:raise Problem('This upgrade is already saved.',409)
                return state
            branch=body['branch'];rank=state['earned'][branch]+1
            if state['pending']!=body['level'] or rank>4:raise Problem('Complete three more missions for your next upgrade.',409)
            db.execute('INSERT INTO mouse_rewards VALUES(?,?,?,?)',(body['level'],branch,rank,now()))
            db.execute(f'UPDATE mouse_equipped SET {branch}=? WHERE id=1',(rank,))
            return self.state(db)

    def equip(self,body):
        if set(body)!=set(PATHS) or any(type(body[b]) is not int for b in PATHS):raise Problem('Choose things you have earned.')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');state=self.state(db)
            if any(not 0<=body[b]<=state['earned'][b] for b in PATHS):raise Problem('That outfit is waiting for a future adventure.',403)
            db.execute('UPDATE mouse_equipped SET outfit=?,gadgets=?,magic=? WHERE id=1',tuple(body[b] for b in PATHS))
            return self.state(db)
