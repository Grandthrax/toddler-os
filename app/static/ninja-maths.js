/* Ten offline missions. The local service checks answers, unlocks and rewards. */
(() => {
  'use strict';
  const root=document.getElementById('ninja-root');
  const $=selector=>root.querySelector(selector);
  const escape=text=>String(text).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const symbol=name=>`<svg aria-hidden="true"><use href="#icon-${name}"/></svg>`;
  const {icon,avatar}=window.NinjaVisuals;
  const crystal=(number=0,lit=false)=>`<svg viewBox="0 0 54 64" aria-hidden="true" class="ninja-crystal ${lit?'lit':''}"><path d="M27 3 46 18v28L27 61 8 46V18Z" fill="${lit?'#e8b45d':'#d1d6d5'}" stroke="${lit?'#b87c35':'#abb8b8'}" stroke-width="2"/><path d="m27 3 8 20-8 38-8-38Z" fill="${lit?'#fff0ba':'#eef0e9'}"/><path d="M8 18h38M8 46l11-23h16l11 23" fill="none" stroke="${lit?'#f3d58c':'#c4cccc'}" stroke-width="2"/>${number?`<text x="27" y="40" text-anchor="middle" fill="#6c452c" stroke="#fff7db" stroke-width="3" paint-order="stroke" font-size="23" font-weight="bold">${number}</text>`:''}</svg>`;
  const game={data:null,view:'home',active:false,busy:false,error:'',retry:null,feedback:null,wrong:false,
    typed:'',picked:null,counted:new Set(),preview:null,audio:null,audioId:0,muted:false};
  try {game.muted=localStorage.getItem('ninja-maths-muted')==='true';} catch {}
  const pendingKey='ninja-maths-pending-answer';
  const draftKey=()=>game.data?.question?`ninja-maths-draft:${game.data.question.id}`:null;
  function storeDraft() {try {if(draftKey()) localStorage.setItem(draftKey(),game.typed);}catch{}}
  function restoreDraft() {try {game.typed=localStorage.getItem(draftKey())||'';}catch {game.typed='';}}
  function rememberPending(body) {try {localStorage.setItem(pendingKey,JSON.stringify(body));}catch{}}
  function clearPending(body) {try {if(JSON.parse(localStorage.getItem(pendingKey)||'null')?.request_id===body.request_id) localStorage.removeItem(pendingKey);}catch{}}
  function stopAudio() {game.audioId++;if(game.audio) {game.audio.pause();game.audio=null;}}
  function speak(id) {
    stopAudio();if(game.muted || !game.active) return;
    const token=game.audioId,queue=Array.isArray(id)?[...id]:[id];
    const next=()=>{if(token!==game.audioId||!game.active||!queue.length) return;const audio=window.LearningAudio.create(`/ninja/audio/${queue.shift()}.wav`);game.audio=audio;audio.onended=next;audio.play().catch(()=>{});};next();
  }
  async function request(path,body) {
    const response=await fetch('/api/ninja'+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json','X-Little-Pages':'1'},
      ...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(12000)});
    const value=await response.json();
    if(!response.ok) throw Object.assign(new Error(value.error),{status:response.status,detail:value});
    return value;
  }
  function resetQuestion() {game.typed='';restoreDraft();game.picked=null;game.counted.clear();game.wrong=false;game.feedback=null;}
  function focus() {
    if(!game.active || game.busy) return;
    const target=$('[data-autofocus]')||$('button:not(:disabled)');target?.focus({preventScroll:true});
  }
  async function update(path,body,done) {
    if(game.busy) return;
    stopAudio();game.busy=true;game.error='';game.retry=null;render();
    try {
      const result=await request(path,body);game.data=result.state||result;done?.(result);
    } catch(error) {
      if(error.status===409 && error.detail.state) {
        game.data=error.detail.state;game.view=game.data.stage==='reward'?'reward':'home';
        if(path==='/answer') clearPending(body);
        game.error='Your saved progress is back. Continue your mission.';
      } else {
        game.error='Your mission has not finished saving. Try again when you are ready.';
        game.retry=()=>update(path,body,done);
      }
    } finally {game.busy=false;render();if(game.active) focus();}
  }
  function startMission(level=null) {
    update('/start',level===null?{}:{level},()=>{resetQuestion();game.view=game.data.stage==='reward'?'reward':'play';speak(game.data.stage==='reward'?'reward':[`mission-${game.data.level}`,questionAudio()]);});
  }
  const questionAudio=()=>game.data.question?.audio||game.data.question?.kind;
  function answer(number) {
    if(game.busy || !game.data.question) return;
    const oldQuestion=game.data.question;
    const body={run_id:game.data.run_id,question_id:oldQuestion.id,version:game.data.version,answer:number,request_id:crypto.randomUUID()};
    rememberPending(body);
    update('/answer',body,result=>{
      clearPending(body);
      if(result.correct) {
        try {localStorage.removeItem(`ninja-maths-draft:${oldQuestion.id}`);}catch{}
        game.feedback={question:oldQuestion,answer:number};game.view='feedback';game.wrong=false;speak('correct');
      } else {game.wrong=true;game.view='play';speak('try-again');}
    });
  }
  function help() {
    if(!game.data.question || game.busy) return;
    const q=game.data.question;
    update('/help',{run_id:game.data.run_id,question_id:q.id,version:game.data.version},()=>speak(q.help_audio||'help-'+q.quantity));
  }
  function continueMission() {
    resetQuestion();
    game.view=game.data.stage==='reward'?'reward':game.data.stage==='complete'?'complete':'play';
    game.preview=null;render();focus();
    if(game.view==='reward') speak('reward');else if(game.view==='play') speak(questionAudio());else speak(game.data.chapter_complete?'chapter-complete':'practice');
  }
  const itemFor=id=>game.data?.catalog.find(item=>item.id===id);
  const characterName=id=>itemFor(id)?.name||'Training outfit';
  const worn=()=>game.view==='reward'&&game.preview?game.data.upgrades.find(item=>item.id===game.preview).loadout:game.data.loadout;
  const pips=rank=>`<span class="ninja-power-pips" aria-label="Power ${rank} of 4">${Array.from({length:4},(_,i)=>`<i class="${i<rank?'filled':'empty'}"></i>`).join('')}</span>`;
  function hero() {
    const loadout=worn(),level=game.data.completed_level+1;
    return `<aside class="ninja-hero-panel"><div class="ninja-rank"><span class="ninja-rank-star">✦</span><strong class="ninja-big-level" aria-label="Ninja level ${level}">${level}</strong></div><div class="ninja-character-stage"><span class="ninja-sun" aria-hidden="true"></span>${avatar(loadout,'ninja-main-character','Your blonde ninja with her earned equipment')}<span class="ninja-character-shadow" aria-hidden="true"></span></div><div class="ninja-outfit-label ninja-loadout">${['sword','armour','power'].map(branch=>`<span class="${loadout[branch]?'earned':'unearned'}" title="${branch} power ${loadout[branch]}">${icon(branch)}${pips(loadout[branch])}</span>`).join('')}</div></aside>`;
  }
  function header() {
    return `<header class="ninja-header"><div class="ninja-brand"><img src="/ninja-maths.svg" width="43" height="43" alt=""><div><strong>NINJA MATHS</strong><span>Little numbers. Mighty adventures.</span></div></div><nav aria-label="Ninja Maths"><button class="ninja-small-button" data-action="home" data-safe title="Missions">${symbol('home')}<span>Missions</span></button><button class="ninja-small-button" data-action="equipment" title="Your equipment">${symbol('book')}<span>Your ninja</span></button><button class="ninja-small-button ninja-audio-toggle" data-action="sound" data-safe aria-label="${game.muted?'Turn game sound on':'Mute game sound'}" aria-pressed="${!game.muted}">${symbol(game.muted?'stop':'sound')}</button></nav></header>`;
  }
  function missionHome() {
    const pending=game.data.stage==='reward',resume=game.data.stage==='question';
    return `<div class="ninja-mission-home"><div class="ninja-home-heading"><h1>${game.data.chapter_complete?'Sunrise ninja!':'Choose a mission'}</h1><button class="ninja-hear" data-action="hear-home" aria-label="Hear how to choose a mission">${symbol('sound')}</button></div><div class="ninja-level-path ninja-chapter-map">${game.data.levels.map(level=>`<button class="ninja-map-level ${level.status}" data-level="${level.id}" ${level.status==='locked'?'disabled':''} aria-label="Mission ${level.id}: ${escape(level.name)}. ${level.status}"><span class="ninja-map-number">${level.id}</span>${icon(level.status==='locked'?'lock':level.icon)}${level.status==='completed'?`<span class="ninja-map-tick">${icon('check')}</span>`:level.status==='active'?`<span class="ninja-map-dots">${'●'.repeat(level.solved)}${'○'.repeat(5-level.solved)}</span>`:''}</button>`).join('')}</div><button class="ninja-primary ninja-icon-primary" data-action="start" data-autofocus aria-label="${pending?'Choose your upgrade':resume?'Continue mission':'Start next mission'}">${icon(pending?'trophy':'play')}<span>${pending?'Choose!':resume?'Continue':'Play'}</span>${icon('arrow')}</button></div>`;
  }
  function progress() {
    return `<div class="ninja-mission-progress"><span class="ninja-mission-number">${icon(game.data.levels[game.data.level-1].icon)}<strong>${game.data.level}</strong></span><div class="ninja-progress-crystals" aria-label="${game.data.solved} of 5 puzzles solved">${Array.from({length:5},(_,i)=>crystal(0,i<game.data.solved)).join('')}</div></div>`;
  }
  function counters(n,{start=0,ghost=false,cross=0,mini=false,label=false}={}) {
    return `<div class="ninja-counter-group ${ghost?'ghost':''} ${mini?'mini':''}">${n?Array.from({length:n},(_,i)=>`<${mini?'span':'button'} class="ninja-count-crystal ${cross&&i>=n-cross?'taken-away':''} ${game.counted.has(start+i)?'counted':''}" ${mini?'':`data-count="${start+i}" aria-label="Crystal ${start+i+1}" aria-pressed="${game.counted.has(start+i)}"`}>${crystal(label?i+1:0,true)}</${mini?'span':'button'}>`).join(''):'<span class="ninja-zero" aria-label="No crystals">0</span>'}</div>`;
  }
  function puzzleBoard(q) {
    if(q.task==='compare') {
      return `${q.relation==='equal'?`<div class="ninja-compare-reference">${counters(q.reference,{mini:true,label:q.hinted})}${icon('equal')}</div>`:''}<div class="ninja-group-choices" role="group" aria-label="${q.relation==='more'?'Choose the most':q.relation==='fewer'?'Choose the fewest':'Choose the same number'}">${q.numbers.map((n,i)=>`<button class="ninja-group-answer" data-answer="${i}" aria-label="Group ${i+1}" data-autofocus><span class="ninja-group-badge">${i+1}</span>${counters(n,{mini:true,label:q.hinted})}</button>`).join('')}</div>`;
    }
    if(q.task==='add') return `<div class="ninja-maths-board"><div class="ninja-picture-sum">${counters(q.a,{label:q.hinted})}${icon('plus')}${counters(q.b,{start:q.a,label:false})}</div><div class="ninja-equation">${q.a} + ${q.b} = <b>?</b></div>${q.hinted?`<div class="ninja-help-result">${Array.from({length:q.a+q.b},(_,i)=>`<span>${i+1}</span>`).join('')}</div>`:''}</div>`;
    if(q.task==='subtract') return `<div class="ninja-maths-board"><div class="ninja-subtraction-group">${counters(q.a,{cross:q.b,label:q.hinted})}</div><div class="ninja-equation">${q.a} − ${q.b} = <b>?</b></div>${q.hinted?`<div class="ninja-help-result">${q.a-q.b}</div>`:''}</div>`;
    if(q.task==='missing'||q.task==='bonds') return `<div class="ninja-maths-board"><div class="ninja-ten-frame frame-columns-${Math.min(5,q.b)}" aria-label="${q.a} filled spaces and ${q.b-q.a} empty spaces">${Array.from({length:q.b},(_,i)=>`<div class="ninja-frame-cell ${i<q.a?'filled':'empty'}">${i<q.a?crystal(0,true):q.hinted?`<span>${i-q.a+1}</span>`:'<span>?</span>'}</div>`).join('')}</div><div class="ninja-equation">${q.a} + <b>?</b> = ${q.b}</div></div>`;
    return `<div class="ninja-counting-board" role="group" aria-label="Crystals to count">${counters(q.quantity,{label:q.hinted})}</div>`;
  }
  function puzzle() {
    const q=game.data.question;if(!q) return missionHome();
    const title=q.task==='compare'?({more:'Which has more?',fewer:'Which has fewer?',equal:'Which is the same?'})[q.relation]:q.task==='add'?'How many altogether?':q.task==='subtract'?'How many are left?':['missing','bonds'].includes(q.task)?'How many more?':'How many crystals?';
    const hint=game.wrong?'Have another go.':q.kind==='number'?'⌨ → ✓':q.kind==='match'?'● → ⛩':'';
    const board=puzzleBoard(q);
    let controls;
    if(q.kind==='number') {
      controls=`<form id="ninja-number-form" class="ninja-number-controls"><label for="ninja-answer" class="sr-only">Your number</label><input id="ninja-answer" inputmode="numeric" autocomplete="off" pattern="[0-9]*" maxlength="2" placeholder="?" value="${escape(game.typed)}" data-autofocus><button class="ninja-primary" type="submit" aria-label="Check">${icon('check')}</button><div class="ninja-numberpad" aria-label="Number buttons">${[1,2,3,4,5,6,7,8,9,0].map(n=>`<button type="button" data-digit="${n}">${n}</button>`).join('')}<button type="button" data-action="backspace" aria-label="Remove last number">${symbol('backspace')}</button></div></form>`;
    } else if(q.kind==='groups') {controls='';} else {
      controls=`<div class="ninja-answer-choices" role="group" aria-label="Answer choices">${q.choices.map((n,i)=>`<button class="ninja-answer-choice ${game.picked===n?'picked':''}" data-answer="${n}" ${q.kind==='match'?'draggable="true"':''} aria-pressed="${game.picked===n}" ${i===0?'data-autofocus':''}>${n}</button>`).join('')}</div>`;
      if(q.kind==='match') controls+=`<button class="ninja-drop-zone ${game.picked!==null?'ready':''}" data-action="drop" aria-label="Dojo gate answer target"><span>${game.picked===null?'?':game.picked}</span>${icon('arrow')}${icon('gate')}</button>`;
    }
    return `${progress()}<div class="ninja-puzzle kind-${q.kind} task-${q.task}"><div class="ninja-puzzle-heading"><h1>${title}</h1><button class="ninja-hear" data-action="hear" aria-label="Hear the question">${symbol('sound')}</button></div><p id="ninja-puzzle-hint" class="ninja-puzzle-hint ${game.wrong?'try-again':''}" role="status">${hint}</p><div class="ninja-activity">${board}<div class="ninja-controls">${controls}</div></div><div class="ninja-puzzle-foot"><button class="ninja-help" data-action="help" aria-label="Count with me">${icon('hand')}${symbol('sound')}</button></div></div>`;
  }
  function feedback() {
    const final=game.data.stage!=='question';
    return `${progress()}<div class="ninja-feedback"><div class="ninja-success-star" aria-hidden="true">✦</div><h1>${final?'Mission complete!':'You did it!'}</h1><div class="ninja-gate ${final?'open':''}" aria-hidden="true"><span></span><span></span><i>✧</i></div><button class="ninja-primary ninja-icon-primary" data-action="continue" data-autofocus aria-label="${game.data.stage==='reward'?'Choose your upgrade':final?'Finish practice':'Next puzzle'}">${icon(game.data.stage==='reward'?'trophy':'arrow')}</button></div>`;
  }
  function rewards() {
    const cards=['sword','armour','power'].map(branch=>{
      const item=game.data.upgrades.find(choice=>choice.branch===branch);
      if(!item) {
        const outfit={...game.data.loadout,[branch]:4};
        return `<button class="ninja-upgrade-card maxed" disabled aria-label="${branch} path complete, four of four"><div class="ninja-upgrade-picture">${avatar(outfit,'',branch+' path complete')}</div><div class="ninja-upgrade-category">${icon(branch)}${pips(4)}${icon('check')}</div></button>`;
      }
      return `<button class="ninja-upgrade-card ${game.preview===item.id?'selected':''}" data-preview="${item.id}" aria-label="Try ${escape(item.name)}, ${item.branch} power ${item.rank} of four" aria-pressed="${game.preview===item.id}"><div class="ninja-upgrade-picture">${avatar(item.loadout,'',escape(item.name))}</div><div class="ninja-upgrade-category">${icon(item.branch)}${pips(item.rank)}${game.preview===item.id?icon('check'):''}</div></button>`;
    }).join('');
    return `<div class="ninja-reward"><div class="ninja-reward-heading">${icon('trophy')}<h1>Choose!</h1><button class="ninja-hear" data-action="hear-reward" aria-label="Hear how to choose an upgrade">${symbol('sound')}</button></div><div class="ninja-upgrade-choices" role="group" aria-label="Upgrade paths. A tick means a completed path.">${cards}</div><button class="ninja-primary ninja-choose-upgrade ninja-icon-primary" data-action="choose" ${!game.preview?'disabled':''} aria-label="Keep this upgrade">${icon('check')}</button></div>`;
  }
  function complete() {
    return `<div class="ninja-complete"><div class="ninja-success-star" aria-hidden="true">${game.data.chapter_complete?'🏆':'✦'}</div><h1>${game.data.chapter_complete?'Sunrise ninja!':'More powerful!'}</h1><div class="ninja-earned-icons">${icon(itemFor(game.data.reward)?.branch||'trophy')}${icon('check')}</div><button class="ninja-primary ninja-icon-primary" data-action="${game.data.chapter_complete?'home':'next-level'}" data-autofocus aria-label="${game.data.chapter_complete?'Back to missions':'Play next mission'}">${icon(game.data.chapter_complete?'trophy':'play')}${!game.data.chapter_complete?`<span>${Math.min(10,game.data.completed_level+1)}</span>`:''}${icon('arrow')}</button><button class="ninja-text-button" data-action="home" aria-label="Back to missions">${symbol('home')}</button></div>`;
  }
  function equipment() {
    return `<div class="ninja-equipment"><div class="ninja-home-heading"><h1>Your ninja</h1><button class="ninja-hear" data-action="hear-equipment" aria-label="Hear about your equipment">${symbol('sound')}</button></div><div class="ninja-owned-items">${game.data.owned.map(id=>{const item=itemFor(id),outfit=item?{...game.data.loadout,[item.branch]:item.rank}:{sword:0,armour:0,power:0},selected=item?game.data.loadout[item.branch]===item.rank:Object.values(game.data.loadout).every(n=>n===0);return `<button data-equip="${id}" class="ninja-owned ${selected?'selected':''}" aria-label="Wear ${escape(characterName(id))}" aria-pressed="${selected}"><div class="ninja-owned-picture">${avatar(outfit,'',escape(characterName(id)))}</div><div class="ninja-owned-category">${icon(item?.branch||'shirt')}${pips(item?.rank||0)}</div>${selected?symbol('check'):''}</button>`;}).join('')}</div><button class="ninja-primary ninja-icon-primary" data-action="home" data-autofocus aria-label="Back to missions">${icon('arrow')}</button></div>`;
  }
  function render() {
    if(!game.data) {
      root.innerHTML=`<div class="ninja-loading"><img src="/ninja-maths.svg" width="70" height="70" alt=""><p>${game.error||'Getting your mission ready…'}</p>${game.error?'<button class="ninja-primary" data-action="reload">Try again</button>':''}</div>`;
      $('[data-action=reload]')?.addEventListener('click',()=>open(true));return;
    }
    const content=game.view==='reward'?rewards():game.view==='play'?puzzle():game.view==='feedback'?feedback():game.view==='complete'?complete():game.view==='equipment'?equipment():missionHome();
    root.innerHTML=`${header()}${game.error?`<div class="ninja-error" role="alert"><span>${escape(game.error)}</span><button data-action="retry">Try again</button></div>`:''}<div class="ninja-layout">${hero()}<section class="ninja-content" aria-label="Ninja Maths mission">${content}</section></div><div class="ninja-save-indicator" role="status">${game.busy?'Saving…':game.retry?'Save needs a retry':'Progress saved on this computer'}</div>`;
    root.setAttribute('aria-busy',String(game.busy));
    if(game.busy) root.querySelectorAll('button:not([data-safe]),input').forEach(el=>el.disabled=true);
    bind();
  }
  function bind() {
    root.querySelectorAll('[data-action]').forEach(button=>button.onclick=()=>action(button.dataset.action));
    root.querySelectorAll('[data-level]').forEach(button=>button.onclick=()=>startMission(Number(button.dataset.level)));
    root.querySelectorAll('[data-answer]').forEach(button=>{
      button.onclick=()=>{const n=Number(button.dataset.answer);if(game.data.question.kind==='match'){game.picked=n;render();$('.ninja-drop-zone')?.focus();}else answer(n);};
      button.addEventListener('dragstart',event=>{game.picked=Number(button.dataset.answer);event.dataTransfer.setData('text/plain',button.dataset.answer);event.dataTransfer.effectAllowed='move';});
      button.addEventListener('dragend',()=>{$('.ninja-drop-zone')?.classList.remove('drag-over');});
    });
    const drop=$('.ninja-drop-zone');
    drop?.addEventListener('dragover',event=>{if(!game.busy){event.preventDefault();event.dataTransfer.dropEffect='move';drop.classList.add('drag-over');}});
    drop?.addEventListener('dragleave',()=>drop.classList.remove('drag-over'));
    drop?.addEventListener('drop',event=>{event.preventDefault();drop.classList.remove('drag-over');const raw=event.dataTransfer.getData('text/plain');if(/^\d{1,2}$/.test(raw)&&game.data.question.choices.includes(Number(raw))) answer(Number(raw));});
    root.querySelectorAll('[data-count]').forEach(button=>button.onclick=()=>{
      const n=Number(button.dataset.count);if(game.counted.has(n)) game.counted.delete(n);else game.counted.add(n);
      button.classList.toggle('counted',game.counted.has(n));button.setAttribute('aria-pressed',String(game.counted.has(n)));
    });
    root.querySelectorAll('[data-preview]').forEach(button=>button.onclick=()=>{game.preview=button.dataset.preview;render();$(`[data-preview="${game.preview}"]`)?.focus();speak('preview-'+game.preview);});
    root.querySelectorAll('[data-equip]').forEach(button=>button.onclick=()=>update('/equip',{upgrade:button.dataset.equip}));
    root.querySelectorAll('[data-digit]').forEach(button=>button.onclick=()=>{
      if(game.typed.length<2) game.typed+=button.dataset.digit;storeDraft();$('#ninja-answer').value=game.typed;$('#ninja-answer').focus();
    });
    $('#ninja-answer')?.addEventListener('input',event=>{game.typed=event.target.value.replace(/\D/g,'').slice(0,2);event.target.value=game.typed;storeDraft();});
    $('#ninja-number-form')?.addEventListener('submit',event=>{event.preventDefault();if(/^\d{1,2}$/.test(game.typed)&&Number(game.typed)<=10) answer(Number(game.typed));else {$('#ninja-answer').focus();$('#ninja-puzzle-hint').textContent='Choose a number from 0 to 10.';}});
  }
  function action(name) {
    if(name==='sound') {game.muted=!game.muted;stopAudio();try {localStorage.setItem('ninja-maths-muted',String(game.muted));}catch{}render();return;}
    if(game.busy) return;
    if(name==='home') {stopAudio();game.view='home';game.feedback=null;render();focus();}
    else if(name==='equipment') {stopAudio();game.view='equipment';render();focus();}
    else if(name==='start') startMission();
    else if(name==='next-level') startMission(Math.min(10,game.data.completed_level+1));
    else if(name==='continue') continueMission();
    else if(name==='help') help();
    else if(name==='hear') speak(questionAudio());
    else if(name==='hear-home') speak('home');
    else if(name==='hear-reward') speak('reward');
    else if(name==='hear-equipment') speak('equipment');
    else if(name==='drop'&&game.picked!==null) answer(game.picked);
    else if(name==='backspace') {game.typed=game.typed.slice(0,-1);storeDraft();$('#ninja-answer').value=game.typed;$('#ninja-answer').focus();}
    else if(name==='choose'&&game.preview) {
      const chosen=game.preview;
      update('/reward',{upgrade:chosen,level:game.data.pending_level},()=>{game.view=game.data.stage==='reward'?'reward':'complete';game.preview=null;speak(game.data.stage==='reward'?['earned-'+chosen,'reward']:game.data.chapter_complete?['earned-'+chosen,'chapter-complete']:'earned-'+chosen);});
    } else if(name==='retry') {if(game.retry) game.retry();else open(true);}
  }
  async function open(refresh=false) {
    game.active=true;
    if(!refresh&&game.data) {render();focus();return;}
    game.error='';game.retry=null;game.busy=true;render();
    try {
      game.data=await request('');
      let pending=null;try {pending=JSON.parse(localStorage.getItem(pendingKey)||'null');}catch{}
      if(pending) {
        try {const reply=await request('/answer',pending);game.data=reply.state;clearPending(pending);}
        catch(error) {if(error.status===409&&error.detail.state){game.data=error.detail.state;clearPending(pending);}else throw error;}
      }
      game.view=game.data.stage==='reward'?'reward':'home';game.preview=null;resetQuestion();
      for(const src of ['/ninja/gear-v2/body-'+game.data.loadout.armour+'.png',...game.data.upgrades.map(item=>item.image)]) {const img=new Image();img.src=src;}
    } catch {game.error='Your mission needs a moment. Your saved progress is still here.';}
    finally {game.busy=false;render();if(game.active) focus();}
  }
  document.addEventListener('visibilitychange',()=>{if(document.hidden) stopAudio();});
  window.NinjaMaths={open,focus,activate:()=>{game.active=true;},pause:()=>{game.active=false;stopAudio();},canHide:()=>!game.busy};
})();
