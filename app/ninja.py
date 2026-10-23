"""Durable chapter progress, once-only rewards and cumulative Ninja equipment."""
import json
import uuid

from core import Problem, now
from ninja_content import BRANCHES, ITEMS, LEVELS, MAX_RANK, UPGRADES, expected, questions_for


class NinjaGame:
    def __init__(self, store):
        self.store = store
        with store.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS ninja_runs (
                    id TEXT PRIMARY KEY, questions TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0,
                    version INTEGER NOT NULL DEFAULT 0, helped TEXT NOT NULL DEFAULT '[]',
                    completed INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL, level INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS ninja_profile (
                    id INTEGER PRIMARY KEY CHECK(id=1), completed_level INTEGER NOT NULL DEFAULT 0,
                    reward TEXT, equipped TEXT NOT NULL DEFAULT 'starter', current_run TEXT REFERENCES ninja_runs(id)
                );
                CREATE TABLE IF NOT EXISTS ninja_answers (
                    request_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES ninja_runs(id),
                    question_id TEXT NOT NULL, answer INTEGER NOT NULL, correct INTEGER NOT NULL, created TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ninja_completions (
                    level INTEGER PRIMARY KEY, run_id TEXT REFERENCES ninja_runs(id), created TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ninja_rewards (
                    level INTEGER PRIMARY KEY REFERENCES ninja_completions(level), upgrade TEXT NOT NULL, created TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ninja_loadout (
                    id INTEGER PRIMARY KEY CHECK(id=1), sword INTEGER NOT NULL DEFAULT 0,
                    armour INTEGER NOT NULL DEFAULT 0, power INTEGER NOT NULL DEFAULT 0
                );
                INSERT OR IGNORE INTO ninja_profile(id) VALUES(1);
            """)
            if "level" not in {row[1] for row in db.execute("PRAGMA table_info(ninja_runs)")}:
                db.execute("ALTER TABLE ninja_runs ADD COLUMN level INTEGER NOT NULL DEFAULT 1")
            profile = dict(db.execute("SELECT * FROM ninja_profile WHERE id=1").fetchone())
            if profile["completed_level"] and not db.execute("SELECT 1 FROM ninja_completions").fetchone():
                run = db.execute("SELECT id FROM ninja_runs WHERE completed=1 ORDER BY created DESC LIMIT 1").fetchone()
                db.execute("INSERT INTO ninja_completions VALUES(1,?,?)", (run[0] if run else None,now()))
                if profile["reward"] in ITEMS: db.execute("INSERT INTO ninja_rewards VALUES(1,?,?)", (profile["reward"],now()))
            if not db.execute("SELECT 1 FROM ninja_loadout").fetchone():
                loadout = {branch:0 for branch in BRANCHES}
                if profile["equipped"] in ITEMS:
                    item = ITEMS[profile["equipped"]];loadout[item["branch"]] = item["rank"]
                db.execute("INSERT INTO ninja_loadout VALUES(1,?,?,?)", tuple(loadout.values()))
            # Preserve every old reward receipt. Ranks beyond the new cap become
            # pending replacement choices on their already-completed missions.
            db.execute("CREATE TABLE IF NOT EXISTS ninja_retired_rewards (level INTEGER PRIMARY KEY, upgrade TEXT NOT NULL, created TEXT NOT NULL)")
            retired = db.execute("SELECT level,upgrade,created FROM ninja_rewards").fetchall()
            for row in retired:
                if row[1] not in ITEMS:
                    db.execute("INSERT OR IGNORE INTO ninja_retired_rewards VALUES(?,?,?)", tuple(row))
                    db.execute("DELETE FROM ninja_rewards WHERE level=?", (row[0],))
            for branch in BRANCHES:
                db.execute(f"UPDATE ninja_loadout SET {branch}=min({branch},?) WHERE id=1", (MAX_RANK,))
            for field in ("reward", "equipped"):
                old = profile[field]
                if old and old not in ITEMS and old != "starter":
                    branch = old.rsplit("-", 1)[0]
                    replacement = f"{branch}-{MAX_RANK}" if branch in BRANCHES else "starter"
                    db.execute(f"UPDATE ninja_profile SET {field}=? WHERE id=1", (replacement,))

    def state(self, db=None):
        if db is None:
            with self.store.connect() as db: return self.state(db)
        profile = dict(db.execute("SELECT * FROM ninja_profile WHERE id=1").fetchone())
        row = db.execute("SELECT * FROM ninja_runs WHERE id=?", (profile["current_run"],)).fetchone()
        run = dict(row) if row else None
        completions = {row[0] for row in db.execute("SELECT level FROM ninja_completions")}
        rewards = {row[0]:row[1] for row in db.execute("SELECT level,upgrade FROM ninja_rewards ORDER BY level")}
        completed = max(completions,default=0)
        pending = next((level for level in sorted(completions) if level not in rewards),None)
        stage = "reward" if pending else "question" if run and not run["completed"] else "complete" if run else "home"
        question = None
        if run and not run["completed"]:
            question = json.loads(run["questions"])[run["position"]]
            question = question | {"task":question.get("task","count"),"hinted":question["id"] in json.loads(run["helped"])}
        earned = {branch:0 for branch in BRANCHES}
        for identifier in rewards.values():
            item = ITEMS[identifier];earned[item["branch"]] = max(earned[item["branch"]],item["rank"])
        loadout = dict(db.execute("SELECT sword,armour,power FROM ninja_loadout WHERE id=1").fetchone())
        choices = [item | {"loadout":loadout | {item["branch"]:item["rank"]}} for item in UPGRADES if item["rank"] == earned[item["branch"]]+1]
        active_runs = {row[0]:row[1] for row in db.execute("SELECT level,max(position) FROM ninja_runs WHERE completed=0 GROUP BY level")}
        level = pending or (run["level"] if run else min(10,completed+1))
        return {"stage":stage,"level":level,"completed_level":completed,"pending_level":pending,
                "max_rank":MAX_RANK,"maxed":[branch for branch in BRANCHES if earned[branch]==MAX_RANK],
                "chapter_complete":len(rewards)==10,"next_level_unlocked":completed>0 and completed<10,"next_level_available":completed<10,
                "reward":rewards.get(level),"equipped":profile["equipped"],"loadout":loadout,"earned":earned,"upgrades":choices,"catalog":UPGRADES,
                "owned":["starter",*rewards.values()],"rewards":{str(k):v for k,v in rewards.items()},
                "levels":[{k:v for k,v in entry.items() if k!="questions"} | {"status":"completed" if entry["id"] in completions else "locked" if entry["id"]>completed+1 else "active" if entry["id"] in active_runs else "ready","solved":active_runs.get(entry["id"],0)} for entry in LEVELS],
                "run_id":run["id"] if run else None,"version":run["version"] if run else 0,"solved":run["position"] if run else 0,"total":5,"question":question}

    def start(self, level=None):
        if level is not None and (type(level) is not int or not 1<=level<=10): raise Problem("Choose a mission number from one to ten.")
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE");current = self.state(db)
            if current["stage"] == "reward": return current
            if level is None:
                if current["stage"] == "question": return current
                level = min(10,current["completed_level"]+1)
            if level>current["completed_level"]+1: raise Problem("Finish the glowing mission to unlock this one.",409,state=current)
            previous = db.execute("SELECT id FROM ninja_runs WHERE level=? AND completed=0 ORDER BY created DESC LIMIT 1", (level,)).fetchone()
            if previous: identifier = previous[0]
            else:
                identifier = str(uuid.uuid4())
                db.execute("INSERT INTO ninja_runs(id,questions,created,level) VALUES(?,?,?,?)", (identifier,json.dumps(questions_for(level,identifier)),now(),level))
            db.execute("UPDATE ninja_profile SET current_run=? WHERE id=1", (identifier,))
            return self.state(db)

    def _current(self, db, body):
        current = self.state(db)
        if (current["stage"]!="question" or body.get("run_id")!=current["run_id"] or body.get("question_id")!=current["question"]["id"] or type(body.get("version")) is not int or body["version"]!=current["version"]):
            raise Problem("Your mission has moved on. Your progress is safe.",409,state=current)
        return current

    def answer(self, body):
        if set(body)!={"run_id","question_id","version","answer","request_id"}: raise Problem("Choose one answer to check.")
        if type(body["answer"]) is not int or not 0<=body["answer"]<=10: raise Problem("Choose a whole number from zero to ten.")
        try: uuid.UUID(body["request_id"])
        except (TypeError,ValueError,AttributeError): raise Problem("That answer could not be saved. Please try again.")
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            receipt = db.execute("SELECT * FROM ninja_answers WHERE request_id=?", (body["request_id"],)).fetchone()
            if receipt:
                if any(receipt[k]!=body[k] for k in ("run_id","question_id","answer")): raise Problem("That answer has already been checked.",409,state=self.state(db))
                return {"state":self.state(db),"correct":bool(receipt["correct"]),"replayed":True}
            current = self._current(db,body);correct = body["answer"]==expected(current["question"])
            db.execute("INSERT INTO ninja_answers VALUES(?,?,?,?,?,?)", (body["request_id"],body["run_id"],body["question_id"],body["answer"],int(correct),now()))
            position = current["solved"]+int(correct);completed = position==5
            db.execute("UPDATE ninja_runs SET position=?,version=version+1,completed=? WHERE id=?", (position,int(completed),current["run_id"]))
            if completed:
                db.execute("INSERT OR IGNORE INTO ninja_completions VALUES(?,?,?)", (current["level"],current["run_id"],now()))
                db.execute("UPDATE ninja_profile SET completed_level=max(completed_level,?) WHERE id=1", (current["level"],))
            return {"state":self.state(db),"correct":correct,"replayed":False}

    def help(self, body):
        if set(body)!={"run_id","question_id","version"}: raise Problem("Choose the current puzzle for help.")
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE");current = self._current(db,body)
            row = db.execute("SELECT helped FROM ninja_runs WHERE id=?", (current["run_id"],)).fetchone();helped = json.loads(row[0])
            if body["question_id"] not in helped:
                helped.append(body["question_id"])
                db.execute("UPDATE ninja_runs SET helped=?,version=version+1 WHERE id=?", (json.dumps(helped),current["run_id"]))
            return self.state(db)

    def reward(self, body):
        if set(body) not in ({"upgrade"},{"upgrade","level"}) or not isinstance(body.get("upgrade"),str) or body["upgrade"] not in ITEMS: raise Problem("Choose one of your three upgrades.")
        level = body.get("level",1)  # Legacy preview tabs can only claim/retry level one.
        if type(level) is not int or not 1<=level<=10: raise Problem("Choose the completed mission.")
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE");current = self.state(db);previous = current["rewards"].get(str(level))
            if previous:
                if previous!=body["upgrade"]: raise Problem("This mission's upgrade is already saved.",409,state=current)
                return current
            if current["pending_level"]!=level: raise Problem("Finish this mission to earn its upgrade.",409,state=current)
            if body["upgrade"] not in {item["id"] for item in current["upgrades"]}: raise Problem("Choose one of the next upgrades shown.",409,state=current)
            item = ITEMS[body["upgrade"]]
            db.execute("INSERT INTO ninja_rewards VALUES(?,?,?)", (level,item["id"],now()))
            db.execute(f"UPDATE ninja_loadout SET {item['branch']}=? WHERE id=1", (item["rank"],))
            db.execute("UPDATE ninja_profile SET reward=?,equipped=? WHERE id=1", (item["id"],item["id"]))
            return self.state(db)

    def equip(self, body):
        if set(body)!={"upgrade"} or not isinstance(body["upgrade"],str): raise Problem("Choose an outfit you have earned.")
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE");current = self.state(db)
            if body["upgrade"] not in current["owned"]: raise Problem("That upgrade is waiting for a future mission.",403)
            if body["upgrade"]=="starter": db.execute("UPDATE ninja_loadout SET sword=0,armour=0,power=0 WHERE id=1")
            else:
                item = ITEMS[body["upgrade"]]
                db.execute(f"UPDATE ninja_loadout SET {item['branch']}=? WHERE id=1", (item["rank"],))
            db.execute("UPDATE ninja_profile SET equipped=? WHERE id=1", (body["upgrade"],))
            return self.state(db)
