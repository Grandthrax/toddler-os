"""Small programming missions; reference solutions stay on the server."""
from copy import deepcopy

ACTIONS = ('forward', 'left', 'right', 'pick', 'open')
CONDITIONS = ('cheese', 'path', 'key', 'left')
PATHS = ('outfit', 'gadgets', 'magic')
CHAPTERS = ('First footsteps', 'Garden practice', 'Mouse detective', 'Look before you leap', 'Choose your adventure')


def seq(code):
    return [{'action': {'F':'forward', 'L':'left', 'R':'right', 'P':'pick', 'O':'open'}[c]} for c in code if c != ' ']


def check(condition, yes, no=''):
    return {'if':condition, 'yes':seq(yes), 'no':seq(no)}


def scene(code, start=(1, 4, 0), cheese=(), keys=(), doors=(), collect=False):
    x,y,d=start; cells=[[x,y]]
    for c in code:
        if c=='L': d=(d-1)%4
        elif c=='R':d=(d+1)%4
        elif c=='F':
            dx,dy=((1,0),(0,1),(-1,0),(0,-1))[d];x+=dx;y+=dy
            if [x,y] not in cells:cells.append([x,y])
    assert all(0<=a<7 and 0<=b<7 for a,b in cells),cells
    return {'size':7,'cells':cells,'start':list(start),'goal':[x,y],
            'cheese':[list(p) for p in cheese], 'keys':[list(p) for p in keys],
            'doors':[list(p) for p in doors], 'collect':collect}


LEVELS=[]
def mission(title, instruction, solution, scenes, starter=None, conditions=()):
    number=len(LEVELS)+1
    allowed=list(ACTIONS[:3]) + (['pick'] if number>=15 else []) + (['open'] if number>=16 else [])
    LEVELS.append({'level':number,'chapter':(number-1)//9,'title':title,'instruction':instruction,
                   'solution':deepcopy(solution),'scenes':scenes,'starter':deepcopy(starter or []),
                   'actions':allowed,'conditions':list(conditions),'otherwise':number>=28,
                   'limit':max(8, min(28,len(solution)*2+6))})


for title,text,code,start in [
 ('A little nibble','Give Mouse one forward step to reach the cheese.','F',(1,4,0)),
 ('Two tiny steps','Put two forward steps in your programme.','FF',(1,4,0)),
 ('Across the bridge','Three steps will cross the bridge.','FFF',(1,4,0)),
 ('Look left','Turn left on the spot. Then move forward.','LF',(2,4,0)),
 ('Look right','Turn right on the spot. Then move forward.','RF',(2,2,0)),
 ('The flowerpot','Walk forward, turn, and go around the flowerpot.','FFLF',(1,4,0)),
 ('Two corners','Plan the two corners. The arrow shows where Mouse is looking.','FLFFRF',(1,4,0)),
 ('Garden zigzag','Left, then right, then left. Build a zigzag route.','FLFRFLF',(1,4,0)),
 ('Picnic adventure','Plan the whole route to the picnic. You can take one step at a time.','FFLFFRF',(1,4,0)),
]:mission(title,text,seq(code),[scene(code,start)])

for title,text,code,starter in [
 ('One wrong arrow','One arrow is wrong. Tap it to remove it, then put a forward step in its place.','FF','RF'),
 ('The missing step','Mouse needs another forward step before the corner. Tap a plus to choose where it goes.','FFLF','FLF'),
 ('Too far','There is one step too many. Remove the last arrow.','FFF','FFFF'),
 ('Wrong turning','Find the wrong turn. Replace it with a left turn.','FLFF','FRFF'),
 ('Mouse detective','Try one step at a time. Find the extra forward step.','FFLFRF','FFLFFRF'),
]:mission(title,text,seq(code),[scene(code)],seq(starter))
mission('Find the key','Stop on the key and use the little paw to pick it up. Then reach the cheese.',seq('FPF'),[scene('FF',keys=[(2,4)])])
mission('The cheese cupboard','Pick up the key. Stop before the door and open it. Then walk through.',seq('FPFOF'),[scene('FFF',keys=[(2,4)],doors=[(4,4)])])
mission('Two little treats','Pick up both little cheeses on your way to the picnic flag.',seq('FPFPF'),[scene('FFF',cheese=[(2,4),(3,4)],collect=True)])
mission('The garden delivery','Collect the key, open the door, and collect the cheese before the flag.',seq('FPFOFLFPF'),[scene('FFFLFF',keys=[(2,4)],doors=[(4,4)],cheese=[(4,3)],collect=True)])

mission('Is there cheese?','The question block looks for cheese here. Put a paw inside its tick side, then move forward.',[check('cheese','P'),*seq('F')],[scene('F',cheese=[(1,4)],collect=True)],conditions=['cheese'])
mission('An empty picnic','The same question works when there is no cheese. It skips the paw and carries on.',[check('cheese','P'),*seq('F')],[scene('F',collect=True)],conditions=['cheese'])
mission('Two picnic gardens','Use one programme for both gardens. Pick up cheese only when it is there.',[check('cheese','P'),*seq('F')],[scene('F',cheese=[(1,4)],collect=True),scene('F',collect=True)],conditions=['cheese'])
mission('Can I go forward?','The open path picture asks if the square ahead is clear. Move only when it is.',[check('path','F')],[scene('F')],conditions=['path'])
mission('Mind the flowerpot','Check ahead first. If it is blocked, skip that step. Then turn right and walk.',[check('path','F'),*seq('RF')],[scene('RF',(2,2,0))],conditions=['path'])
mission('The changing bridge','Try both gardens. Sometimes there is an extra clear square before the right turn.',[check('path','F'),*seq('RF')],[scene('FRF',(2,2,0)),scene('RF',(2,2,0))],conditions=['path'])
mission('Have I got a key?','Collect the key. The key question checks your backpack before opening the door.',[*seq('FPF'),check('key','O'),*seq('F')],[scene('FFF',keys=[(2,4)],doors=[(4,4)])],conditions=['key'])
mission('Cheese and keys','Use a cheese question at the start, and a backpack key question at the door.',[check('cheese','P'),*seq('FPF'),check('key','O'),*seq('F')],[scene('FFF',cheese=[(1,4)],keys=[(2,4)],doors=[(4,4)],collect=True)],conditions=['cheese','key'])
mission('Clever mouse','Check for cheese. Check the path. Then turn right. Your programme must work in both gardens.',[check('cheese','P'),check('path','F'),*seq('RF')],[scene('FRF',(2,2,0),cheese=[(2,2)],collect=True),scene('RF',(2,2,0),collect=True)],conditions=['cheese','path'])

mission('Walk or turn','The fork has two sides. Clear ahead? Follow the tick. Otherwise, follow the cross.',[check('path','F','R'),*seq('F')],[scene('FF',(2,2,0)),scene('RF',(2,2,0))],conditions=['path'])
mission('Open or closed','The same decision works even when Mouse starts facing a different way.',[check('path','F','R'),*seq('F')],[scene('FF',(3,4,3)),scene('RF',(3,4,3))],conditions=['path'])
mission('The clever corner','Put two forward steps in the clear side. In the other side, turn right and walk.',[check('path','FF','RF')],[scene('FF',(2,2,0)),scene('RF',(2,2,0))],conditions=['path'])
mission('Which way is open?','Look to the left. If it is clear, turn left. Otherwise, turn right. Then walk.',[check('left','L','R'),*seq('F')],[scene('LF',(3,3,0)),scene('RF',(3,3,0))],conditions=['left'])
mission('The changing junction','Choose the open side, then walk two squares to the picnic.',[check('left','L','R'),*seq('FF')],[scene('LFF',(3,3,0)),scene('RFF',(3,3,0))],conditions=['left'])
mission('Collect or continue','If cheese is here, collect it. Otherwise, take a forward step. Then walk to the flag.',[check('cheese','P','F'),*seq('F')],[scene('F',cheese=[(1,4)],collect=True),scene('FF',collect=True)],conditions=['cheese'])
mission('Repair a decision','The two sides of the decision are mixed up. Swap the actions to help Mouse.',[check('path','F','R'),*seq('F')],[scene('FF',(2,2,0)),scene('RF',(2,2,0))],[check('path','R','F'),*seq('F')],conditions=['path'])
mission('Two decisions','First check for cheese. Then check the path. Watch each question light up in all three gardens.',[check('cheese','P','R'),check('path','F','L'),*seq('F')],[scene('FF',(2,3,0),cheese=[(2,3)],collect=True),scene('RFF',(2,3,0),collect=True),scene('LF',(2,3,0),cheese=[(2,3)],collect=True)],conditions=['cheese','path'])
mission('The grand cheese rescue','Use all your skills. Check for cheese, collect the key, open the door, then choose the clear route.',[check('cheese','P'),*seq('FPF'),check('key','O'),*seq('F'),check('path','F','LF')],[scene('FFFF',cheese=[(1,4)],keys=[(2,4)],doors=[(4,4)],collect=True),scene('FFFLF',keys=[(2,4)],doors=[(4,4)],collect=True)],conditions=['cheese','key','path'])

# Keep the original missions' teaching metadata and draft identities independent
# of display numbering. New practice sits before the remaining detective puzzles.
original=LEVELS[:]
for level in original:
    old=level['level']
    level.update(id=str(old),theme=level['chapter'],chapter=0 if old<=10 else 2 if old<=18 else 3 if old<=27 else 4)
LEVELS=[]
for title,text,code,start,starter in [
 ('Around the daisies','Walk two steps, turn left on the spot, then walk to the cheese.','FFLFF',(1,5,0),''),
 ('The sunny corner','This time the corner turns right. Watch the arrow on Mouse.','FFRFF',(1,1,0),''),
 ('Two garden corners','Plan a left turn and a right turn. Count the steps between the corners.','FLFFRFF',(1,5,0),''),
 ('The winding path','Follow the winding path. Turn right, then left, to reach the cheese.','FRFFLFF',(1,1,0),''),
 ('Facing the flowers','Mouse starts looking up. Forward means the way Mouse is looking.','FFRFF',(1,5,3),''),
 ('The picnic zigzag','Take your time with three corners. You can try one step at a time.','FLFRFFLF',(1,5,0),''),
 ('Fix the garden turn','One turn points the wrong way. Watch Mouse, then replace that turn.','FFLFF','', 'FFRFF'),
 ('A missing garden step','One forward step is missing before the corner. Choose a plus and add it.','FFLFRF','', 'FLFRF'),
 ('The long way to lunch','There is one forward step too many after the second turn. Remove it and try again.','FLFFRFF','', 'FLFFRFFF'),
]:
    mission(title,text,seq(code),[scene(code,start or (1,5,0))],seq(starter))
    LEVELS[-1].update(id=f'practice-{len(LEVELS)}',chapter=1,theme=0,actions=list(ACTIONS[:3]),otherwise=False)
LEVELS=original[:10]+LEVELS+original[10:]
for number,level in enumerate(LEVELS,1):level['level']=number

UPGRADE_NAMES={
 'outfit':('A little scarf','Explorer','Captain','Royal adventurer'),
 'gadgets':('Cheese backpack','Lantern pack','Clockwork wings','Flying machine'),
 'magic':('Sparkling paws','Glowing tail','Starry cape','Mouse guardian'),
}


def prompts():
    result={'welcome':'Welcome to Mouse Missions. Help your little mouse find the cheese.',
     'forward':'Move forward one square.','left':'Turn left on the spot.','right':'Turn right on the spot.',
     'pick':'Pick up the cheese or key on this square.','open':'Open the door in front of you with your key.',
     'if-cheese':'Is there cheese on this square?','if-path':'Is the path ahead clear?',
     'if-key':'Is there a key in my backpack?','if-left':'Is the path to my left clear?',
     'yes':'If yes, do these steps.','no':'Otherwise, do these steps.',
     'slot':'Add the next block here. Tap a block to remove it.',
     'run':'Watch Mouse follow your programme.','step':'Show just the next step.',
     'retry':'Reset Mouse. Your programme stays here.','clear':'Start a fresh programme.',
     'win':'You did it! Your programme worked in every garden.',
     'bump':'A gentle bump! Check which way Mouse is looking. Change a block and try again.',
     'unfinished':'Nearly there. Look at where Mouse stopped. You can change your programme and try again.',
     'empty':'There is nothing to pick up here. Try the paw on a cheese or key square.',
     'door':'Mouse needs a key and a door just ahead to open it.',
     'reward':'Mouse has levelled up! Choose something new. Tap a picture to see it, then tap the tick.',
     'wardrobe':'Your mouse collection. Choose anything you have earned.',
     'saved':'Your programme is saved.','help':'Follow the pale footprints. The arrow shows which way Mouse is looking.',
     'conditions':'Use the pictured question in your programme. Watch the tick or cross to see what Mouse finds.',
     'next-garden':'Now let us try the same programme in the next garden.',
     'locked':'Finish the earlier mission first.','choose':'Choose a numbered mission.',
     'complete':'You finished every mission! You are a magnificent mouse programmer.'}
    result.update({f'level-{level["level"]}':f'Mission {level["level"]}. '+level['instruction'] for level in LEVELS})
    result.update({f'{branch}-{rank}':name for branch,names in UPGRADE_NAMES.items() for rank,name in enumerate(names,1)})
    return result
