/* Picture-block programming. The local interpreter checks every garden. */
(() => {
 'use strict';
 const root=document.getElementById('mouse-root'),{icon,avatar,boardMouse}=window.MouseVisuals;
 const $=s=>root.querySelector(s),esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const names={forward:'Move forward',left:'Turn left',right:'Turn right',pick:'Pick up',open:'Open door',cheese:'Cheese here?',path:'Path ahead clear?',key:'Key in backpack?'};
 const questionNames={cheese:'Cheese here?',path:'Path ahead clear?',key:'Key in backpack?',left:'Left path clear?'};
 const g={data:null,level:null,program:[],view:'home',active:false,busy:false,error:'',audio:null,audioToken:0,saveQueue:Promise.resolve(),saveTimer:null,
  target:{path:[],index:0},run:null,frames:[],cursor:0,frame:null,garden:0,playing:false,timer:null,help:false,highlight:null,preview:null,completing:false};
 const pendingKey=n=>`mouse-missions-draft:${n}`;
 const copy=v=>JSON.parse(JSON.stringify(v));
 const initial=s=>({x:s.start[0],y:s.start[1],direction:s.start[2],cheese:copy(s.cheese),keys:copy(s.keys),doors:copy(s.doors),bag:false});
 const crashed=f=>f?.event==='bump'||(f?.event==='finish'&&f.reason==='bump');
 const reducedMotion=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
 function cancelMotion(){for(const animation of root.getAnimations({subtree:true}))animation.cancel();}
 function stopAudio(){g.audioToken++;g.audio?.pause();g.audio=null;}
 function speak(id){stopAudio();if(!g.active||window.ChildLock?.locked())return;g.audio=LearningAudio.create(`/mouse/audio/${id}.wav`);g.audio.play().catch(()=>{});}
 async function request(path,body){const r=await fetch('/api/mouse'+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json','X-Little-Pages':'1'},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(12000)});const data=await r.json();if(!r.ok)throw new Error(data.error);return data;}
 function report(error){g.error=error.message||'Your programme is kept here. Try again.';render();}
 function pause(){g.active=false;g.playing=false;clearTimeout(g.timer);cancelMotion();stopAudio();if(g.level)saveDraft().catch(()=>{});syncPlayer();}
 function activate(){g.active=true;}
 function draft(){if(!g.level)return;try{localStorage.setItem(pendingKey(g.level.id),JSON.stringify(g.program));}catch{}clearTimeout(g.saveTimer);g.saveTimer=setTimeout(()=>saveDraft().catch(report),400);}
 function saveDraft(){clearTimeout(g.saveTimer);if(!g.level)return g.saveQueue;const body={level:g.level.level,program:copy(g.program)},encoded=JSON.stringify(body.program),key=pendingKey(g.level.id);
  g.saveQueue=g.saveQueue.catch(()=>{}).then(async()=>{await request('/draft',body);try{if(localStorage.getItem(key)===encoded)localStorage.removeItem(key);}catch{} });return g.saveQueue;
 }
 async function beforeHide(){try{await saveDraft();return true;}catch(error){report(error);return false;}}
 function header(title,extra=''){return `<header class="mm-header"><button data-act="home" class="mm-round" aria-label="Mission map">${icon('home')}</button><div><span class="mm-eyebrow">MOUSE MISSIONS</span><h1>${esc(title)}</h1></div><div class="mm-header-tools">${extra}<button data-act="wardrobe" class="mm-round" aria-label="Your mouse collection">${icon('outfit')}</button><button data-act="help" class="mm-round" aria-label="Hear instructions">${icon('sound')}</button></div></header>`;}
 function errorHTML(){return g.error?`<p class="mm-error" role="alert">${esc(g.error)} <button data-act="dismiss" aria-label="Dismiss message">×</button></p>`:'';}
 function home(){
  const completed=g.data.completed.length,next=g.data.next_level;
  return `${header('A little mouse. A big adventure.')}${errorHTML()}<div class="mm-map-layout"><aside class="mm-hero"><div class="mm-hero-avatar">${avatar(g.data.equipped)}</div><h2>${completed===g.data.levels.length?'Magnificent Mouse!':'Your little explorer'}</h2><div class="mm-success-pips" aria-label="${g.data.choices.length?completed%3+' of three missions towards an upgrade':'All upgrades earned'}">${[0,1,2].map(i=>`<span class="${!g.data.choices.length||i<completed%3?'lit':''}">${icon('cheese')}</span>`).join('')}</div><p>${completed} / ${g.data.levels.length}</p><button class="mm-big-play" data-act="${g.data.pending?'reward':'level'}" data-level="${next}" aria-label="${g.data.pending?'Choose your upgrade':'Play mission '+next}">${g.data.pending?icon('star'):icon('run')}<span>${g.data.pending?'★':next}</span></button></aside><div class="mm-chapters">${g.data.chapters.map((title,c)=>`<section class="mm-chapter chapter-${c}"><div class="mm-chapter-heading"><span>${[icon('forward'),icon('left'),icon('help'),icon('if'),icon('path')][c]}</span><div><p>${['FOLLOW THE ARROWS','MORE TURNS. MORE PRACTICE.','TRY. WATCH. FIX.','IF…','IF… OTHERWISE…'][c]}</p><h2>${esc(title)}</h2></div></div><div class="mm-level-grid">${g.data.levels.filter(l=>l.chapter===c).map(l=>`<button data-act="level" data-level="${l.level}" class="mm-level ${l.completed?'completed':''} ${l.level===next&&!l.completed?'next':''}" ${!l.unlocked?'disabled':''} aria-label="Mission ${l.level}: ${esc(l.title)}${!l.unlocked?', locked':''}"><b>${l.level}</b>${l.completed?icon('tick'):!l.unlocked?icon('lock'):icon('run')}${l.level%3===0&&g.data.choices.length?'<span class="mm-level-gift">★</span>':''}</button>`).join('')}</div></section>`).join('')}</div></div>`;
 }
 function tileIcon(type,x,y){
  if(type==='cheese')return `<g transform="translate(${x-20} ${y-20}) scale(.63)"><path d="m7 45 9-28 36 14v20L7 45Z" fill="#f7cf71" stroke="#ba8b43" stroke-width="2"/><path d="m16 17 25-8 11 22" fill="#ffe7a3" stroke="#ba8b43" stroke-width="2"/><circle cx="26" cy="33" r="3" fill="#dca453"/><circle cx="42" cy="41" r="3" fill="#dca453"/></g>`;
  if(type==='key')return `<g stroke="#b17d2e" stroke-width="5" fill="#ffdf82" transform="translate(${x} ${y})"><circle cx="-10" cy="0" r="8"/><path d="M-3 0h24m-7 0v9m-9-9v6" fill="none"/></g>`;
  return `<g transform="translate(${x-19} ${y-23})"><rect width="38" height="46" rx="5" fill="#aa7750" stroke="#715b41" stroke-width="3"/><path d="M10 3v40m18-40v40M2 11h34M2 35h34" stroke="#d5b27c" stroke-width="3"/><circle cx="29" cy="23" r="3" fill="#ffe4a1"/></g>`;
 }
 function board(){
  const s=g.level.scenes[g.garden],f=g.frame||initial(s),loadout=g.preview||g.data.equipped,open=new Set(s.cells.map(p=>p.join(','))),c=g.level.theme;
  let tiles='';for(let y=0;y<7;y++)for(let x=0;x<7;x++){
   const cx=x*70+35,cy=y*70+35,walk=open.has(`${x},${y}`);
   tiles+=`<g><rect x="${x*70+2}" y="${y*70+2}" width="66" height="66" rx="${walk?10:17}" fill="${walk?((x+y)%2?'#faf0d7':'#fff7e4'):['#b7d0a7','#b6cdd2','#d0c9a3','#c6bddd'][c]}"/>${!walk?`<path d="m${cx-11} ${cy+10}q-6-22 9-21 14-1 13 21" fill="${['#89ad7d','#82abb1','#b5ad7d','#ab9fc7'][c]}"/><circle cx="${cx+11}" cy="${cy-10}" r="4" fill="#e8e2ae"/>`:''}</g>`;
  }
  const at=(list,type)=>list.map(([x,y])=>tileIcon(type,x*70+35,y*70+35)).join('');
  const [gx,gy]=s.goal;
  const [dx,dy]=[[1,0],[0,1],[-1,0],[0,-1]][f.direction],hitX=Math.max(18,Math.min(472,f.x*70+35+dx*39)),hitY=Math.max(18,Math.min(472,f.y*70+35+dy*39));
  const impact=crashed(f)?`<g class="mm-crash-effect" aria-hidden="true"><rect class="mm-crash-wall" x="${(f.x+dx)*70+3}" y="${(f.y+dy)*70+3}" width="64" height="64" rx="16" fill="#e9a17d" opacity=".65"/><g class="mm-impact-burst" transform="translate(${hitX} ${hitY})"><path d="m0-26 7 14 16-9-5 17 20 3-17 9 8 17-18-6-7 17-6-17-18 6 9-18-18-8 19-4-5-17 16 10Z" fill="#ffe4a0" stroke="#cd8b52" stroke-width="2"/></g><g class="mm-crash-stars" transform="translate(${f.x*70+35} ${f.y*70+35-28})"><ellipse cx="0" cy="-8" rx="30" ry="9" fill="none" stroke="#d7ab57" stroke-width="2" stroke-dasharray="4 5"/><path class="mm-dizzy-star" d="m-22-17 3 6 7 1-5 4 1 7-6-4-6 4 2-7-5-4 7-1Z" fill="#e8ad4f"/><path class="mm-dizzy-star" d="m19-25 3 6 7 1-5 4 1 7-6-4-6 4 2-7-5-4 7-1Z" fill="#e8ad4f"/></g></g>`:'';
  let ghosts='';if(g.help&&!g.level.conditions.length)ghosts=s.cells.slice(1).map(([x,y])=>`<ellipse cx="${x*70+30}" cy="${y*70+31}" rx="6" ry="9" fill="#6f9b8790"/><ellipse cx="${x*70+43}" cy="${y*70+42}" rx="6" ry="9" fill="#6f9b8790"/>`).join('');
  return `<svg viewBox="0 0 490 490" role="img" aria-label="Garden ${g.garden+1}. Mouse at column ${f.x+1}, row ${f.y+1}, facing ${['right','down','left','up'][f.direction]}." class="mm-board">${tiles}<g transform="translate(${gx*70+21} ${gy*70+14})"><path d="M2 43V0m0 0 31 5-9 11L2 13" fill="#edc171" stroke="#a68245" stroke-width="3"/><path d="m8 6 4 4 7-5" fill="none" stroke="#fff9e7" stroke-width="3"/></g>${ghosts}${!s.collect?tileIcon('cheese',gx*70+35,gy*70+35):''}${at(f.cheese,'cheese')}${at(f.keys,'key')}${at(f.doors,'door')}<g class="mm-board-mouse ${f.event==='forward'?'is-walking':''}" transform="translate(${f.x*70+35} ${f.y*70+35}) rotate(${f.direction*90})"><path d="m34-9 12 9-12 9Z" fill="#39867a"/><g class="mm-mouse-body"><ellipse class="mm-foot mm-foot-one" cx="-8" cy="-15" rx="6" ry="3" fill="#d8a69f"/><ellipse class="mm-foot mm-foot-two" cx="-8" cy="15" rx="6" ry="3" fill="#d8a69f"/>${boardMouse(loadout)}</g></g>${impact}</svg>`;
 }
 const conditionIcon=c=>icon(c==='key'?'key':c==='left'?'left':c);
 function programList(list,path=[]){
  const slot=i=>`<button class="mm-slot ${JSON.stringify(g.target)===JSON.stringify({path,index:i})?'selected':''}" data-act="slot" data-path="${esc(JSON.stringify(path))}" data-index="${i}" aria-label="Add a block here">${icon('plus')}</button>`;
  return `${slot(0)}${list.map((n,i)=>{
   const nodePath=[...path,i],mark=JSON.stringify(g.highlight)===JSON.stringify(nodePath)?'executing'+(crashed(g.frame)?' mm-block-crashed':''):'';
   return `${n.action?`<button class="mm-block action-${n.action} ${mark}" data-act="remove" data-path="${esc(JSON.stringify(nodePath))}" aria-label="Remove ${names[n.action]}">${icon(n.action)}<span class="mm-block-remove">×</span></button>`:
    `<div class="mm-if-block ${mark}"><button class="mm-condition" data-act="remove" data-path="${esc(JSON.stringify(nodePath))}" aria-label="Remove question: ${esc(questionNames[n.if])}">${icon('if')}${conditionIcon(n.if)}<span>×</span></button><div class="mm-branch mm-yes"><button data-act="speak" data-audio="yes" aria-label="If yes">${icon('tick')}</button><div class="mm-block-list">${programList(n.yes,[...nodePath,'yes'])}</div></div>${g.level.otherwise?`<div class="mm-branch mm-no"><button data-act="speak" data-audio="no" aria-label="Otherwise">${icon('cross')}</button><div class="mm-block-list">${programList(n.no,[...nodePath,'no'])}</div></div>`:''}</div>`}${slot(i+1)}`;
  }).join('')}`;
 }
 function mission(){
  const level=g.level,n=level.level,finished=g.run&&g.cursor>=g.frames.length;
  return `${header(`${n}. ${level.title}`)}${errorHTML()}<div class="mm-mission-layout"><section class="mm-garden-panel chapter-${level.chapter}"><div class="mm-garden-top"><span class="mm-mission-number">${n}</span><div class="mm-garden-tabs">${level.scenes.map((s,i)=>`<button data-act="garden" data-index="${i}" aria-label="View garden ${i+1}" aria-pressed="${g.garden===i}">${i+1}</button>`).join('')}</div><span class="mm-bag" aria-label="${g.frame?.bag?'Key collected':'Backpack'}">${icon(g.frame?.bag?'key':'gadgets')}</span></div><div id="mm-board-holder">${board()}</div><div class="mm-player"><button data-act="reset" class="mm-round" aria-label="Reset mouse, keep programme">${icon('reset')}</button><button data-act="run" class="mm-run" aria-label="${g.playing?'Pause programme':'Run programme'}">${icon(g.playing?'pause':'run')}</button><button data-act="step" class="mm-round" aria-label="One step">${icon('step')}</button><button data-act="hint" class="mm-round ${g.help?'selected':''}" aria-label="Show a hint">${icon('help')}</button></div><div id="mm-feedback" class="mm-feedback" role="status">${finished?g.run.success?`${icon('star')}<span>Well done!</span><button data-act="continue" class="mm-round" aria-label="Continue">${icon('right')}</button>`:`${icon('reset')}<span>Try a little change.</span>`:'<span>Mouse follows your arrows.</span>'}</div></section><section class="mm-code-panel"><div class="mm-code-heading"><h2>Your programme</h2><button data-act="clear" class="mm-round mm-small" aria-label="Clear programme">${icon('clear')}</button></div><div class="mm-palette" aria-label="Instruction blocks">${level.actions.map(a=>`<button data-act="add" data-action="${a}" class="action-${a}" aria-label="${names[a]}">${icon(a)}</button>`).join('')}</div>${level.conditions.length?`<div class="mm-question-palette" aria-label="Question blocks">${level.conditions.map(c=>`<button data-act="add-if" data-condition="${c}" aria-label="If ${esc(questionNames[c])}">${icon('if')}${conditionIcon(c)}</button>`).join('')}</div>`:''}<div class="mm-program" aria-label="Your programme blocks"><span class="mm-program-start">▶</span><div class="mm-block-list">${programList(g.program)}</div><span class="mm-program-end">⚑</span></div><p class="mm-editor-tip">${icon('plus')} add here <span>·</span> tap a block to remove</p></section></div>`;
 }
 function reward(){const loadout=g.preview||g.data.equipped;return `${header('Mouse levelled up!')}${errorHTML()}<div class="mm-reward"><div class="mm-reward-sparkles">✦ ✧ ✦</div><div class="mm-reward-mouse">${avatar(loadout)}</div><div class="mm-upgrade-choices">${g.data.choices.map(c=>`<button data-act="preview" data-branch="${c.branch}" class="mm-upgrade ${g.preview?.[c.branch]===c.rank?'selected':''}" aria-label="Preview ${esc(c.name)}">${avatar({...g.data.equipped,[c.branch]:c.rank})}<span class="mm-rank-pips">${Array.from({length:4},(_,i)=>`<i class="${i<c.rank?'lit':''}"></i>`).join('')}</span></button>`).join('')}</div><button data-act="confirm-reward" class="mm-confirm" aria-label="Choose this upgrade" ${!g.preview?'disabled':''}>${icon('tick')}</button></div>`;}
 function wardrobe(){return `${header('Your mouse collection')}${errorHTML()}<div class="mm-wardrobe"><div class="mm-wardrobe-mouse">${avatar(g.data.equipped)}</div><div>${['outfit','gadgets','magic'].map(b=>`<section class="mm-wardrobe-row" aria-label="${b}"><span>${icon(b)}</span>${[0,1,2,3,4].map(rank=>`<button data-act="equip" data-branch="${b}" data-rank="${rank}" ${rank>g.data.earned[b]?'disabled':''} aria-label="${b} rank ${rank}" aria-pressed="${g.data.equipped[b]===rank}">${rank<=g.data.earned[b]?avatar({...g.data.equipped,[b]:rank}):icon('lock')}</button>`).join('')}</section>`).join('')}</div></div>`;}
 function render(){if(!g.data){root.innerHTML='<p class="mm-loading">Opening the garden…</p>';return;}root.classList.toggle('mm-busy',g.busy);root.innerHTML=g.view==='play'?mission():g.view==='reward'?reward():g.view==='wardrobe'?wardrobe():home();root.setAttribute('aria-busy',String(g.busy));}
 function reset(){clearTimeout(g.timer);cancelMotion();g.playing=false;g.run=null;g.frames=[];g.cursor=0;g.garden=0;g.frame=null;g.highlight=null;stopAudio();}
 function getList(path){let list=g.program;for(let i=0;i<path.length;i+=2){list=list[path[i]][path[i+1]];}return list;}
 function changed(){reset();g.error='';draft();render();}
 async function loadLevel(n){if(g.busy)return;g.busy=true;render();try{await saveDraft();const level=await request('/levels/'+n);reset();g.level=level;g.program=level.program;try{const saved=JSON.parse(localStorage.getItem(pendingKey(level.id))||'null');if(Array.isArray(saved))g.program=saved;}catch{}g.target={path:[],index:g.program.length};g.view='play';g.help=n<=3;g.error='';render();speak('level-'+n);}catch(error){report(error);}finally{g.busy=false;render();}}
 function syncPlayer(){if(g.view==='play'&&$('[data-act=run]')){$('[data-act=run]').innerHTML=icon(g.playing?'pause':'run');$('[data-act=run]').setAttribute('aria-label',g.playing?'Pause programme':'Run programme');}}
 function drawFrame(previous){if(g.view!=='play')return;cancelMotion();$('#mm-board-holder').innerHTML=board();animateMouse(previous);root.querySelectorAll('.executing,.mm-block-crashed').forEach(el=>el.classList.remove('executing','mm-block-crashed'));
  root.querySelectorAll('.branch-active').forEach(el=>el.classList.remove('branch-active'));
  if(g.highlight){const wanted=JSON.stringify(g.highlight);root.querySelectorAll('[data-act=remove]').forEach(b=>{if(b.dataset.path===wanted){const block=b.classList.contains('mm-condition')?b.closest('.mm-if-block'):b;block.classList.add('executing');if(crashed(g.frame))block.classList.add('mm-block-crashed');
   const branch=b.closest('.mm-branch');if(branch)branch.classList.add('branch-active');
   else if(g.frame.event==='check')b.closest('.mm-if-block')?.querySelector(g.frame.result?'.mm-yes':'.mm-no')?.classList.add('branch-active');
  }});}
  root.querySelectorAll('[data-act=garden]').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.index===g.garden)));
  const bag=$('.mm-bag');bag.innerHTML=icon(g.frame?.bag?'key':'gadgets');bag.setAttribute('aria-label',g.frame?.bag?'Key collected':'Backpack');
  if(g.frame?.event==='check')$('#mm-feedback').innerHTML=`${conditionIcon(g.frame.condition)} ${icon(g.frame.result?'tick':'cross')}`;
  if(g.frame?.event==='bump')$('#mm-feedback').innerHTML=`${icon('star')}<span>Bump! Let’s fix that arrow.</span>`;
 }
 function animateMouse(previous){
  if(!previous||reducedMotion())return;
  const f=g.frame,mouse=$('.mm-board-mouse'),pose=(x,y,d)=>`translate(${x*70+35}px, ${y*70+35}px) rotate(${d*90}deg)`;
  if(f.event==='forward')mouse.animate([{transform:pose(previous.x,previous.y,f.direction)},{transform:pose(f.x,f.y,f.direction)}],{duration:390,easing:'ease-in-out'});
  else if(f.event==='left'||f.event==='right'){
   const from=f.event==='left'?f.direction+1:f.direction-1;
   mouse.animate([{transform:pose(f.x,f.y,from)},{transform:pose(f.x,f.y,f.direction)}],{duration:270,easing:'ease-in-out'});
  }else if(f.event==='bump'){
   const body=$('.mm-mouse-body');
   body.animate([{transform:'translateX(0)'},{transform:'translateX(12px) scaleX(.83) scaleY(1.14)',offset:.24},{transform:'translateX(-9px) rotate(-10deg)',offset:.52},{transform:'translateX(-3px) rotate(6deg)',offset:.76},{transform:'translateX(0) rotate(0deg)'}],{duration:850,easing:'ease-out'});
  }
 }
 async function prepare(){if(g.run&&g.cursor<g.frames.length)return true;if(!g.program.length){speak('slot');return false;}g.busy=true;render();try{await saveDraft();g.run=await request('/run',{level:g.level.level,program:g.program});g.frames=g.run.gardens.flatMap((result,garden)=>result.trace.filter(f=>f.event!=='start').map(frame=>({garden,frame})));g.cursor=0;g.frame=null;g.garden=0;g.highlight=null;g.error='';return true;}catch(error){report(error);return false;}finally{g.busy=false;render();}}
 async function finish(){g.playing=false;syncPlayer();if(g.completing)return;g.completing=true;
  try{if(g.run.success){g.busy=true;g.data=await request('/complete',{run_id:g.run.id});speak(g.data.completed.length===g.data.levels.length?'complete':'win');}else speak(g.run.needs_question?'conditions':g.frame.reason||'unfinished');}
  catch(error){g.error=error.message;}
  finally{g.busy=false;g.completing=false;render();}
 }
 async function advance(){if(!g.active||!g.run)return;const next=g.frames[g.cursor++];if(!next)return finish();const previous=g.garden===next.garden?(g.frame||initial(g.level.scenes[next.garden])):initial(g.level.scenes[next.garden]);if(g.garden!==next.garden)speak('next-garden');g.garden=next.garden;g.frame=next.frame;if(!(g.frame.event==='finish'&&crashed(g.frame)))g.highlight=next.frame.node;drawFrame(previous);if(g.cursor>=g.frames.length)await finish();}
 async function tick(){if(!g.playing||!g.active)return;await advance();if(g.playing)g.timer=setTimeout(tick,g.frame?.event==='bump'?(reducedMotion()?450:1150):(reducedMotion()?220:720));}
 async function play(single=false){if(g.playing){g.playing=false;clearTimeout(g.timer);cancelMotion();syncPlayer();return;}stopAudio();if(!await prepare()||!g.active)return;g.playing=!single;syncPlayer();if(single)await advance();else tick();}
 async function navigate(view){if(!await beforeHide())return;reset();g.view=view;g.preview=null;g.error='';render();speak(view==='reward'?'reward':view==='wardrobe'?'wardrobe':'choose');}
 root.addEventListener('click',async event=>{
  const button=event.target.closest('button[data-act]');if(!button||button.disabled||g.busy||!g.active)return;const act=button.dataset.act;
  try{
   if(act==='home')return navigate('home');if(act==='wardrobe')return navigate('wardrobe');if(act==='reward')return navigate('reward');
   if(act==='level')return loadLevel(+button.dataset.level);
   if(act==='dismiss'){g.error='';render();return;}
   if(act==='help'){speak(g.view==='play'?'level-'+g.level.level:g.view==='reward'?'reward':g.view==='wardrobe'?'wardrobe':'welcome');return;}
   if(act==='speak'){speak(button.dataset.audio);return;}
   if(act==='continue'){if(g.run?.success){await navigate(g.data.pending?'reward':'home');}return;}
   if(act==='preview'){const c=g.data.choices.find(c=>c.branch===button.dataset.branch);g.preview={...g.data.equipped,[c.branch]:c.rank};g.previewBranch=c.branch;render();speak(`${c.branch}-${c.rank}`);return;}
   if(act==='confirm-reward'){g.busy=true;render();try{g.data=await request('/reward',{level:g.data.pending,branch:g.previewBranch});g.preview=null;g.view='home';speak(g.data.completed.length===g.data.levels.length?'complete':'choose');}finally{g.busy=false;render();}return;}
   if(act==='equip'){g.busy=true;render();try{g.data=await request('/equip',{...g.data.equipped,[button.dataset.branch]:+button.dataset.rank});if(+button.dataset.rank)speak(`${button.dataset.branch}-${button.dataset.rank}`);}finally{g.busy=false;render();}return;}
   if(act==='run'||act==='step')return await play(act==='step');
   if(act==='reset'){reset();render();speak('retry');return;}
   if(act==='hint'){g.help=!g.help;render();speak(g.level.conditions.length?'conditions':'help');return;}
   if(g.playing)return;
   if(act==='garden'){g.garden=+button.dataset.index;g.frame=null;g.highlight=null;render();return;}
   if(act==='slot'){g.target={path:JSON.parse(button.dataset.path),index:+button.dataset.index};render();speak('slot');return;}
   if(act==='clear'){g.program=[];g.target={path:[],index:0};changed();speak('clear');return;}
   if(act==='remove'){const p=JSON.parse(button.dataset.path),i=p.pop();getList(p).splice(i,1);g.target={path:p,index:i};changed();return;}
   if(act==='add'||act==='add-if'){
    const count=JSON.stringify(g.program).match(/"action"|"if"/g)?.length||0;
    if(count>=40||(!g.target.path.length&&g.program.length>=g.level.limit)){g.error='Try removing a block before adding another.';render();return;}
    const list=getList(g.target.path);if(g.target.path.length&&list.length>=12){g.error='Try a shorter question branch.';render();return;}
    if(act==='add-if'&&g.target.path.length){g.error='Put questions on the main path. Put arrows and paws inside them.';render();return;}
    const n=act==='add'?{action:button.dataset.action}:{if:button.dataset.condition,yes:[],no:[]};list.splice(g.target.index,0,n);g.target.index++;changed();speak(act==='add'?button.dataset.action:'if-'+button.dataset.condition);
   }
  }catch(error){report(error);}
 });
 window.MouseMissions={open:async(refresh=false)=>{g.active=true;if(!g.data||refresh){g.data=await request('');if(!g.level)g.view=g.data.pending?'reward':'home';}render();speak(g.view==='play'?'level-'+g.level.level:g.data.pending?'reward':'welcome');},pause,activate,beforeHide,
  focus:()=>{if(g.active)root.querySelector('button:not(:disabled)')?.focus({preventScroll:true});}};
})();
