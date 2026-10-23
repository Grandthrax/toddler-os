"""The ten authored missions, visual equipment catalogue and offline speech text."""
import random

BRANCHES = ("sword", "armour", "power")
MAX_RANK = 4
NAMES = {
    "sword": ("Ruby Katana", "Crystal Cleaver", "Twin Storm Blades", "Sunrise Greatsword"),
    "armour": ("Shadow Suit", "Golden Guard", "Storm Samurai", "Sunrise Champion"),
    "power": ("Sun Cloak", "Lightning Halo", "Golden Wings", "Phoenix Flight"),
}
FIRST_IDS = {"sword":"spark-sword", "armour":"golden-guard", "power":"sun-cloak"}
UPGRADES = [
    {"id": FIRST_IDS[branch] if rank == 1 else f"{branch}-{rank}", "name": NAMES[branch][rank-1],
     "branch": branch, "kind": branch.upper(), "rank": rank,
     "image": f"/ninja/gear-v2/{'body' if branch == 'armour' else branch}-{rank}.png"}
    for branch in BRANCHES for rank in range(1, MAX_RANK + 1)
]
ITEMS = {item["id"]:item for item in UPGRADES}

def count(n, kind="choice"):
    return {"task":"count", "quantity":n, "kind":kind}

def compare(numbers, relation, reference=None):
    return {"task":"compare", "numbers":numbers, "relation":relation, "reference":reference, "kind":"groups"}

def maths(task, a, b, kind="choice"):
    return {"task":task, "a":a, "b":b, "kind":kind}

LEVELS = [
    {"id":1, "name":"Open the dojo", "icon":"gate", "questions":[count(n,k) for n,k in zip((4,6,5,8,10),("choice","number","match","number","choice"))]},
    {"id":2, "name":"Sort the supplies", "icon":"crystals", "questions":[count(n,"match") for n in (5,7,3,9,0)]},
    {"id":3, "name":"Balance the bridge", "icon":"bridge", "questions":[compare([5,2,3],"more"),compare([4,3,1],"fewer"),compare([3,4,6],"equal",4),compare([6,4,8],"more"),compare([5,7,9],"fewer")]},
    {"id":4, "name":"Charge the blade", "icon":"sword", "questions":[maths("add",a,b) for a,b in ((1,1),(1,2),(2,2),(3,1),(2,3))]},
    {"id":5, "name":"Open the mountain gate", "icon":"gate", "questions":[maths("add",a,b,"number") for a,b in ((0,3),(2,1),(1,4),(3,2),(2,2))]},
    {"id":6, "name":"Build the stepping stones", "icon":"bridge", "questions":[maths("add",a,b,"match") for a,b in ((3,3),(4,3),(5,3),(4,5),(5,5))]},
    {"id":7, "name":"Find the missing crystal", "icon":"missing", "questions":[maths("missing",a,b,"match") for a,b in ((1,3),(2,4),(1,5),(3,5),(4,4))]},
    {"id":8, "name":"Guard the dojo", "icon":"armour", "questions":[maths("subtract",a,b,k) for a,b,k in ((3,1,"choice"),(4,2,"number"),(5,1,"choice"),(2,2,"number"),(5,3,"choice"))]},
    {"id":9, "name":"Power pairs", "icon":"power", "questions":[maths("bonds",a,10,"match") for a in (5,2,7,0,9)]},
    {"id":10, "name":"The dojo trial", "icon":"trophy", "questions":[compare([6,9,7],"more"),maths("add",4,4,"number"),maths("missing",2,5,"match"),maths("subtract",5,2,"choice"),maths("bonds",6,10,"match")]},
]

def expected(q):
    task = q.get("task", "count")
    if task == "count": return q["quantity"]
    if task == "add": return q["a"] + q["b"]
    if task in ("missing", "bonds"): return q["b"] - q["a"]
    if task == "subtract": return q["a"] - q["b"]
    target = max(q["numbers"]) if q["relation"] == "more" else min(q["numbers"]) if q["relation"] == "fewer" else q["reference"]
    return q["numbers"].index(target)

def questions_for(level, run_id):
    rng = random.SystemRandom()
    result = []
    for index, original in enumerate(LEVELS[level-1]["questions"]):
        q = original.copy();correct = expected(q)
        if q["kind"] != "groups":
            candidates = [n for n in range(max(0,correct-3),min(10,correct+3)+1) if n != correct]
            q["choices"] = [correct, *rng.sample(candidates, 2)]
            rng.shuffle(q["choices"])
        q.update(id=f"{run_id}:{index}", audio=f"l{level}-q{index+1}", help_audio=f"l{level}-q{index+1}-help")
        result.append(q)
    return result

WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")
def count_words(n):
    return ", ".join(WORDS[1:n+1]) if n else "No crystals. That means zero."

def spoken_question(q):
    task=q.get("task","count")
    ending={"choice":"Tap the number.","number":"Write the number, then tap the tick.","match":"Drag the number to the gate, or tap the number, then the gate.","groups":"Tap a group."}[q["kind"]]
    if task == "count": text="How many crystals can you see?" if q["quantity"] else "There are no crystals here. Which number means none?"
    elif task == "compare":
        text={"more":"Which group has the most crystals?", "fewer":"Which group has the fewest crystals?", "equal":f"Which group has the same number as the group at the top? There are {WORDS[q['reference']]} at the top." if q["reference"] is not None else ""}[q["relation"]]
    elif task == "add": text=f"{WORDS[q['a']]} crystals and {WORDS[q['b']]} more. How many altogether?"
    elif task == "subtract": text=f"Start with {WORDS[q['a']]} crystals. Take away {WORDS[q['b']]}. How many are left?"
    else: text=f"You have {WORDS[q['a']]} crystals. How many more do you need to make {WORDS[q['b']]}?"
    return text+" "+ending

def spoken_help(q):
    task=q.get("task","count"); answer=expected(q)
    if task == "count": return "Let's count together. "+count_words(answer)+"."
    if task == "compare":
        text="Let's count the groups. "+". ".join(f"Group {WORDS[i+1]}: {count_words(n)}" for i,n in enumerate(q["numbers"]))+". "
        return text+f"Tap group {WORDS[answer+1]}."
    if task == "add": return f"Count both groups together. {count_words(answer)}. There are {WORDS[answer]} altogether."
    if task == "subtract": return f"The crossed out crystals have gone. Count the crystals left. {count_words(answer)}. The answer is {WORDS[answer]}."
    return f"The empty spaces show what is missing. Count them. {count_words(answer)}. You need {WORDS[answer]} more."

def prompts():
    text={"welcome":"Welcome to Ninja Maths. Tap the glowing mission to play.",
          "choice":"How many crystals can you see? Tap the number.",
          "number":"How many crystals can you see? Write the number, then tap the tick.",
          "match":"How many crystals can you see? Drag the number to the gate, or tap a number, then the gate.",
          "try-again":"Have another go. Tap the helping hand if you would like some help.",
          "correct":"Well done! A crystal is charged.",
          "reward":"Mission complete! Choose an upgrade. Tap a picture to see it on your ninja. Then tap the big tick to keep it.",
          "practice":"Well done! You have finished this practice mission.",
          "chapter-complete":"You did it! All ten missions are complete. You are a sunrise ninja! You can play any mission again.",
          "equipment":"These are your upgrades. Tap a picture to wear it. You can wear a sword, armour and a power together.",
          "home":"Tap a glowing mission number to play. A tick means you have finished it. A padlock means it is waiting for you."}
    for item in UPGRADES:
        text["preview-"+item["id"]]=item["name"]+f". {item['branch']} power {item['rank']}. Tap the tick to choose this upgrade."
        text["earned-"+item["id"]]="You chose "+item["name"]+". Your ninja is more powerful!"
    for level in LEVELS:
        text[f"mission-{level['id']}"]=f"Mission {WORDS[level['id']]}. {level['name']}. Solve five puzzles to earn an upgrade."
        for index,q in enumerate(level["questions"]):
            key=f"l{level['id']}-q{index+1}"
            text[key]=spoken_question(q);text[key+"-help"]=spoken_help(q)
    for n in range(11): text[f"help-{n}"]="Let's count together. "+count_words(n)+"."
    return text
