/* Picture choices, copied words, letter sounds and durable illustrated books. */
(() => {
  'use strict';
  const root=document.getElementById('storybooks-root'),$=selector=>root.querySelector(selector);
  const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const icon=name=>`<svg aria-hidden="true"><use href="#icon-${name}"/></svg>`;
  const state={active:false,view:'home',library:null,book:null,index:0,typed:'',choice:null,pending:null,timer:null,
    error:'',conflict:null,failedSave:null,manifest:null,settings:null,audio:null,token:0,frame:null,controller:null,working:false,newFlow:false};
  const page=()=>state.book?.pages[state.index];
  const selectedAnswer=()=>page()?.choices.find(item=>JSON.stringify(words(state.typed))===JSON.stringify(words(item.answer)));
  const decision=()=>!!page()?.decision;
  const words=text=>(text.toLowerCase().match(/[a-z]+/g)||[]);
  const matches=()=>!!selectedAnswer();
  const savedAnswer=current=>current.answer??current.choices.find(item=>item.id===current.choice)?.answer??'';
  const key=()=>state.book?`storybook-draft:${state.book.id}:${state.index}`:null;
  function preserveCopyDraft(){try{const raw=localStorage.getItem(key()),draft=JSON.parse(raw||'null');if(draft?.input_mode==='copy')localStorage.setItem(key()+':copy-archive:'+draft.version,raw);return true;}catch{return false;}}
  function remember(){if(!key()||!preserveCopyDraft())return;try{localStorage.setItem(key(),JSON.stringify({version:page().version,choice:state.choice,text:state.typed,input_mode:state.newFlow?'answer':'copy'}));}catch{status('Save needs a retry',true);}}
  function forget(){if(!preserveCopyDraft())return;try{localStorage.removeItem(key());}catch{}}
  function status(text='Saved on this computer',error=false){const el=$('.sb-save');if(el){el.textContent=text;el.classList.toggle('error',error);}}
  function stop(){state.token++;state.controller?.abort();state.controller=null;if(state.audio){state.audio.pause();state.audio=null;}cancelAnimationFrame(state.frame);state.frame=null;root.querySelectorAll('.reading').forEach(el=>el.classList.remove('reading'));}
  async function request(path,body,method='POST'){
    const response=await fetch('/api/storybooks'+path,{method:body?method:'GET',headers:{'Content-Type':'application/json','X-Little-Pages':'1'},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(12000)});
    const result=await response.json();if(!response.ok)throw Object.assign(new Error(result.error),{status:response.status,detail:result});return result;
  }
  function play(source,{timings=[],done=()=>{},token=state.token}={}){
    if(!state.active||token!==state.token)return;
    const audio=window.LearningAudio.create(source);state.audio=audio;
    const highlight=()=>{if(token!==state.token||state.audio!==audio)return;const current=timings.findIndex(item=>audio.currentTime>=item[2]&&audio.currentTime<item[3]);root.querySelectorAll('[data-read-word]').forEach((el,index)=>el.classList.toggle('reading',index===current));state.frame=requestAnimationFrame(highlight);};
    audio.onended=()=>{if(token!==state.token)return;cancelAnimationFrame(state.frame);root.querySelectorAll('.reading').forEach(el=>el.classList.remove('reading'));state.audio=null;done();};
    audio.onerror=()=>status('Sound needs a retry',true);
    audio.play().then(()=>{if(timings.length)highlight();}).catch(error=>{if(error.name!=='AbortError')status('Tap the speaker to hear it',true);});
  }
  function say(id,options={}){stop();const prompt=state.manifest?.prompts[id];if(!prompt){options.done?.();return;}play('/storybooks/audio/'+id+'.wav',{...options,timings:prompt.words||[]});}
  function letterSound(letter){stop();if(state.settings?.phonics_enabled&&state.settings.phonics_available.includes(letter))play('/phonics/'+letter);}
  async function sayWord(word,done=()=>{}){
    word=word.toLowerCase().replace(/[^a-z]/g,'');if(!word||word.length>40)return;
    const id='word-'+word;if(state.manifest?.prompts[id]){say(id,{done});return;}
    stop();const token=state.token,controller=new AbortController();state.controller=controller;
    try{
      const response=await fetch('/api/read',{method:'POST',headers:{'Content-Type':'application/json','X-Little-Pages':'1'},body:JSON.stringify({text:word}),signal:controller.signal});
      if(!response.ok)throw Error('speech');const blob=await response.blob();if(token!==state.token||!state.active)return;
      const url=URL.createObjectURL(blob);play(url,{token,done:()=>{URL.revokeObjectURL(url);done();}});setTimeout(()=>URL.revokeObjectURL(url),60000);
    }catch(error){if(error.name!=='AbortError')status('Tap the speaker to try the word again',true);}
  }
  async function save(overrides={}){
    clearTimeout(state.timer);
    if(state.pending&&!(await state.pending))return false;
    if(state.view!=='write'||!state.book||(!state.newFlow&&!state.choice))return true;
    if(state.conflict)return false;
    const bookId=state.book.id,index=state.index,snapshot={...(state.newFlow?{answer:state.typed}:{choice:state.choice,text:state.typed}),
      version:page().version,finished:page().finished&&(decision()?state.typed===page().answer:matches()),...overrides};
    if(Object.keys(snapshot).filter(name=>name!=='version').every(name=>page()[name]===snapshot[name])){forget();status();return true;}
    remember();status('Saving…');setBusy(true);
    const operation=(async()=>{
      try{
        const result=await request('/'+bookId+'/pages/'+index,snapshot,'PUT');
        state.book=result;
        if(state.index===index&&state.typed===(snapshot.answer??snapshot.text)&&(state.newFlow||state.choice===snapshot.choice)){forget();status();}
        else{remember();status('Saving your next words…');}
        state.error='';state.failedSave=null;$('.sb-error')?.remove();return true;
      }catch(error){
        state.failedSave=snapshot;
        state.error='Your words are safe here. Tap Retry to save.';
        if(error.status===409&&error.detail.book){state.conflict={text:state.typed,choice:state.choice,newFlow:state.newFlow};state.book=error.detail.book;say('conflict');render();}
        else{status('Save needs a retry',true);showError();}
        return false;
      }finally{setBusy(false);}
    })();
    state.pending=operation;const result=await operation;state.pending=null;return result;
  }
  function showError(){let bar=$('.sb-error');if(!bar){bar=document.createElement('div');bar.className='sb-error';bar.innerHTML='<span></span><button data-action="retry">Retry</button>';root.insertBefore(bar,$('.sb-stage'));bar.querySelector('button').onclick=()=>act('retry');}bar.querySelector('span').textContent=state.error;}
  async function loadBook(id){
    if(!(await save()))return;
    state.book=await request('/'+id);state.error='';state.conflict=null;
    state.index=Math.max(0,state.book.pages.findIndex(item=>!item.finished));
    if(state.book.completed){state.index=0;state.view='read';render();focus();return;}
    await loadPage();
  }
  async function finishFixed(){
    if(state.pending)return state.pending;
    const current=page(),body={version:current.version,finished:true};
    setBusy(true);
    const operation=(async()=>{
      try{state.book=await request('/'+state.book.id+'/pages/'+state.index,body,'PUT');state.error='';render();focus();say('page-'+page().choice);return true;}
      catch(error){if(error.status===409&&error.detail.book)state.book=error.detail.book;state.error='Your page needs a retry. Your saved book is safe.';showError();return false;}
      finally{setBusy(false);}
    })();
    state.pending=operation;const result=await operation;state.pending=null;return result;
  }
  async function loadPage(){
    const current=page();state.newFlow=true;state.choice=current.choice;state.conflict=null;
    state.typed=savedAnswer(current);
    if(!current.decision){
      state.view='reveal';render();focus();
      if(!current.finished)await finishFixed();else say('page-'+current.choice);
      return;
    }
    state.view='write';
    try{
      const draft=JSON.parse(localStorage.getItem(key())||'null');
      // Old sentence drafts stay archived locally; saved sentences/revisions
      // stay in the database while the child returns to a short word choice.
      if(draft?.input_mode==='copy')preserveCopyDraft();
      else if(draft&&typeof draft.text==='string'){
        if(draft.version===current.version){state.typed=draft.text;state.choice=draft.choice;}
        else if(draft.text!==savedAnswer(current))state.conflict={text:draft.text,choice:draft.choice,newFlow:true};
        else forget();
      }
    }catch{}
    render();focus();say(state.conflict?'conflict':current.instruction);
  }
  function setBusy(busy){root.setAttribute('aria-busy',String(busy));root.querySelectorAll('[data-action=continue-story]').forEach(button=>{button.disabled=busy;});}
  function header(){return `<header class="sb-bar"><div class="sb-brand"><img src="/storybooks.svg" alt=""><strong>Storybooks</strong></div><nav aria-label="Storybooks"><button class="sb-small" data-action="home" aria-label="Bookshelf">${icon('book')}<span>My books</span></button><button class="sb-round" data-action="help" aria-label="Hear what to do">${icon('sound')}</button><button class="sb-round" data-action="stop" aria-label="Stop reading">${icon('stop')}</button></nav></header>`;}
  const dots=(done,total)=>`<span class="sb-dots" aria-label="${done} of ${total} pages">${'●'.repeat(done)}${'○'.repeat(total-done)}${done===total?icon('check'):''}</span>`;
  const readingEdition=()=>['original','wordless'].includes(state.book?.edition);
  const endPrompt=()=>state.book?.edition==='wordless'?'picture-finished':readingEdition()?'read-finished':'finished';
  function templateCard(template){
    const reading=['original','wordless'].includes(template.edition);
    return `<button class="sb-new-book" data-action="new" data-template="${escape(template.id)}"><img src="${template.image}" alt="${escape(template.title)}"><span><strong>${escape(template.title.replace(' · My story',''))}</strong><small>${escape(template.description)}</small><span class="sb-primary">${icon(reading?'book':'pencil')}${reading?template.edition==='wordless'?'Look and tell':'Read a book':'Make a book'}</span>${template.licensed?'<img class="sb-publisher-mark" src="/storybooks/bookdash/book-dash-logo.png" alt="Book Dash">':''}</span></button>`;
  }
  function credits(){
    const credit=state.book?.credits;if(!credit)return '';
    return `<details class="sb-credits"><summary><img src="/storybooks/bookdash/book-dash-logo.png" alt="Book Dash"><span>Book credits · ${escape(credit.license)}</span></summary><p>Originally published by Book Dash. Created by ${credit.creators.map(escape).join('; ')}.</p><p>${escape(credit.changes)}</p><p>Original: ${escape(credit.source)}<br>Licence: ${escape(credit.license_url)}</p><p>No endorsement by the original creators is implied.</p></details>`;
  }
  function home(){
    const templates=state.library.templates;
    return `<div class="sb-home"><div class="sb-intro"><div><h1>My storybooks</h1><p>Make a story, read a book, or tell a picture story.</p></div><button class="sb-round" data-action="welcome" aria-label="Hear about the books">${icon('sound')}</button></div><div class="sb-template-grid">${templates.map(templateCard).join('')}</div>${state.library.books.length?`<h2 class="sb-shelf-title">Your books</h2><div class="sb-shelf">${state.library.books.map(book=>`<button class="sb-book-card" data-book="${book.id}"><img src="${book.image}" alt=""><span><strong>${escape(book.title)}</strong>${dots(book.done,book.total)}</span></button>`).join('')}</div>`:''}</div>`;
  }
  function pageHead(){return `<div class="sb-page-head"><h1>${escape(state.book.title)}</h1><div class="sb-page-count">${state.index+1} / ${state.book.total}${dots(state.book.done,state.book.total)}</div></div>`;}
  function conflict(){return state.conflict?`<div class="sb-conflict" role="alert"><p>This page has newer saved words. Your typing is safe too.</p><button data-action="keep-draft">${icon('pencil')}Keep my typing</button><button data-action="keep-saved">${icon('book')}Use saved words</button></div>`:'';}
  function writer(){return decisionWriter();}
  function decisionWriter(){
    const previous=state.book.pages[state.index-1],letters=[...new Set(page().choices.map(item=>item.answer).join('').replace(/[^a-z]/g,''))].sort();
    return `${pageHead()}${conflict()}<div class="sb-spread sb-decision"><div class="sb-illustration"><img src="${previous?.image||state.book.image}" alt="${escape(previous?.target||state.book.title)}"><div class="sb-context-caption"><span>${escape(previous?.target||state.book.title)}</span>${previous?`<button class="sb-round" data-action="hear-context" aria-label="Hear the story so far">${icon('sound')}</button>`:''}</div></div><div class="sb-writing-page"><div class="sb-copy-head"><span class="sb-copy-label">What happens next?</span><button class="sb-round" data-action="help" aria-label="Hear your word choices">${icon('sound')}</button></div><h2 class="sb-choice-stem">${escape(page().stem)}</h2><div class="sb-word-options" aria-label="Words you can type">${page().choices.map(item=>`<div class="sb-word-option" data-option="${item.answer}"><strong>${item.answer}</strong><button class="sb-round" data-hear-word="${item.answer}" aria-label="Hear ${item.answer}">${icon('sound')}</button></div>`).join('')}</div><label class="sr-only" for="sb-writing">Type one of the word choices</label><textarea id="sb-writing" spellcheck="false" autocomplete="off" autocorrect="off" autocapitalize="off" maxlength="500" ${state.conflict?'disabled':''} placeholder="Type a word…">${escape(state.typed)}</textarea><div class="sb-matching" role="status"></div><div class="sb-letter-keys" aria-label="Letters for your choices">${letters.map(letter=>`<button data-letter="${letter}" aria-label="Write ${letter}">${letter}</button>`).join('')}</div><div class="sb-editing-keys"><button data-action="space">${icon('space')}Space</button><button data-action="backspace" aria-label="Backspace">${icon('backspace')}</button><button data-action="enter" aria-label="Enter. Reveal your choice">${icon('enter')}Enter</button></div><div class="sb-write-footer"><button class="sb-small" data-action="back" ${state.index===0?'disabled':''} aria-label="Previous page">${icon('arrow')}<span>Back</span></button><button class="sb-primary" data-action="next" aria-label="Reveal your story choice">${icon('check')}</button></div></div></div>`;
  }
  function reader(){
    const current=page(),hasText=!!current.target,reading=readingEdition();
    const tokens=current.target.match(/[a-z]+(?:['’–-][a-z]+)*|[^a-z]+/gi)||[];
    const text=tokens.map(part=>/[a-z]/i.test(part)?`<button data-read-word="${escape(part.toLowerCase())}" aria-label="Hear ${escape(part)}">${escape(part)}</button>`:escape(part)).join('');
    const label=reading?state.book.edition==='wordless'?'A picture story':'Original story':'My own storybook';
    return `${pageHead()}<div class="sb-spread sb-read-spread ${!hasText?'sb-picture-only':''}"><div class="sb-illustration"><img src="${current.image}" alt="${escape(current.target||state.book.title+' — picture '+(state.index+1))}"></div><div class="sb-read-page"><div class="sb-copy-label">${label}</div>${hasText?`<div class="sb-read-text">${text}</div>`:'<p class="sb-picture-invitation">Look at the picture.<br>Tell your story.</p>'}<div class="sb-read-controls">${state.view==='reveal'?`${hasText?`<button class="sb-round" data-action="read-page" aria-label="Hear this page">${icon('sound')}</button>`:''}<button class="sb-primary" data-action="continue-story" aria-label="${state.book.completed?'Finish the book':'Next page'}">${icon('arrow')}<span>${state.book.completed?'My book':'Next page'}</span></button>`:`<button class="sb-round" data-action="read-back" ${state.index===0?'disabled':''} aria-label="Previous page">${icon('undo')}</button>${hasText?`<button class="sb-primary" data-action="read-page" aria-label="Read this page">${icon('sound')}<span>Read to me</span></button>`:''}<button class="sb-round" data-action="read-next" ${state.index===state.book.total-1?'disabled':''} aria-label="Next page">${icon('arrow')}</button>`}</div>${current.decision?`<button class="sb-small" data-action="edit">${icon('pencil')}Change my word</button>`:''}${hasText?'<p class="sb-saved-note">Tap any word to hear it.</p>':''}</div></div><div class="sb-book-finish">${state.book.completed?`<span>${reading?'Your book is on the shelf.':'You made a book!'}</span>${state.book.pages.some(p=>p.target)?`<button class="sb-small" data-action="read-all">${icon('sound')}Read my book</button>`:''}`:`<span>${reading?'Turn the page when you are ready.':'Your words made this happen.'}</span>`}</div>`;
  }
  function updateCopy(){
    if(decision()){
      const typed=state.typed.toLowerCase().trim();
      root.querySelectorAll('[data-option]').forEach(card=>{
        const target=card.dataset.option;let prefix=0;while(prefix<Math.min(typed.length,target.length)&&typed[prefix]===target[prefix])prefix++;
        card.classList.toggle('matched',typed===target);
        card.querySelector('strong').innerHTML=[...target].map((char,index)=>`<span class="${index<prefix?'done':index===prefix?typed.length>prefix&&prefix>0?'wrong':typed&&prefix===0?'':'next':''}">${char}</span>`).join('');
      });
      $('[data-action=next]').disabled=!matches()||!!state.conflict;
      $('.sb-matching').textContent=matches()?'✓ Space or Enter reveals your story':'Type one of the words above.';return;
    }

  }
  function render(){
    if(!state.library){root.innerHTML=`<p class="sb-loading">Opening your bookshelf…</p>`;return;}
    root.classList.toggle('sb-licensed',!!state.book?.credits);
    root.innerHTML=header()+`<section class="sb-stage">${state.view==='home'?home():['read','reveal'].includes(state.view)?reader():writer()}${credits()}</section><div class="sb-save" role="status">Saved on this computer</div>`;
    setBusy(root.getAttribute('aria-busy')==='true');
    if(state.error)showError();
    root.querySelectorAll('[data-action]').forEach(button=>button.onclick=()=>act(button.dataset.action,button.dataset.template));
    root.querySelectorAll('[data-book]').forEach(button=>button.onclick=()=>navigate(()=>loadBook(button.dataset.book)));
    root.querySelectorAll('[data-hear-word]').forEach(button=>button.onclick=()=>sayWord(button.dataset.hearWord));
    root.querySelectorAll('[data-hear]').forEach(button=>button.onclick=()=>say(button.dataset.hear));
    root.querySelectorAll('[data-letter]').forEach(button=>button.onclick=()=>insert(button.dataset.letter));
    root.querySelectorAll('[data-read-word]').forEach(button=>button.onclick=()=>sayWord(button.dataset.readWord));
    const input=$('#sb-writing');if(input){input.addEventListener('input',event=>onInput(event));input.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();act('next');}});input.setSelectionRange(state.typed.length,state.typed.length);updateCopy();}
  }
  function onInput(event){
    const input=$('#sb-writing'),caret=input.selectionStart,raw=input.value;
    const clean=text=>text.toLowerCase().replace(/[^a-z \n.,!?'-]/g,'').replace(/\n/g,' ');
    input.value=clean(raw).slice(0,500);const position=clean(raw.slice(0,caret)).length;input.setSelectionRange(position,position);state.typed=input.value;
    remember();status('Saving…');updateCopy();clearTimeout(state.timer);state.timer=setTimeout(()=>save(),350);
    if(event.inputType==='insertText'&&/^[a-z]$/i.test(event.data||''))letterSound(event.data.toLowerCase());
    else if(event.inputType==='insertText'&&event.data===' '){const match=input.value.slice(0,position).match(/([a-z]+)[.,!?]* $/);if(match)sayWord(match[1],state.newFlow&&matches()?()=>act('next'):()=>{});}
  }
  function insert(text){const input=$('#sb-writing');if(!input||state.conflict)return;input.focus();input.setRangeText(text,input.selectionStart,input.selectionEnd,'end');onInput({inputType:'insertText',data:text});}
  async function navigate(callback){if(state.working)return;state.working=true;try{await callback();}catch{state.error='Your book needs a moment. Your typing is still safe.';showError();}finally{state.working=false;}}
  function focus(){if(state.active)($('#sb-writing')||$('[data-action=continue-story]')||$('[data-action=new]')||$('button'))?.focus({preventScroll:true});}
  async function act(name,template){
    if(name==='stop'){stop();return;}if(name==='help'){say(state.conflict?'conflict':state.view==='write'?page().instruction:state.view==='read'?endPrompt():'welcome');return;}
    if(name==='hear-context'){say('page-'+state.book.pages[state.index-1].choice);return;}
    if(name==='welcome'){say('welcome');return;}if(name==='hear-page'){say('page-'+state.choice);return;}
    if(name==='space'){insert(' ');return;}if(name==='period'){insert('.');return;}
    if(name==='backspace'){const input=$('#sb-writing');if(!input||state.conflict)return;const end=input.selectionEnd,start=input.selectionStart;input.setRangeText('',start===end?Math.max(0,start-1):start,end,'end');onInput({inputType:'deleteContentBackward'});input.focus();return;}
    if(name==='read-page'){say('page-'+page().choice);return;}if(name==='read-all'&&state.book.completed){readAll(0);return;}
    await navigate(async()=>{
      if(name==='keep-draft'){const draft=state.conflict;state.conflict=null;state.typed=draft.text;state.choice=draft.choice;state.newFlow=draft.newFlow;remember();await save();render();focus();return;}
      if(name==='keep-saved'){state.conflict=null;state.choice=page().choice;state.newFlow=true;state.typed=savedAnswer(page());forget();state.error='';render();focus();return;}
      if(name==='retry'){if(!state.manifest||!state.settings){await open(true);return;}if(state.view==='reveal'&&!page().finished){await finishFixed();return;}const completing=state.failedSave?.finished&&state.failedSave.answer===state.typed;if(await save(completing?{finished:true}:{})){state.error='';if(completing){state.view='reveal';state.choice=page().choice;}render();focus();if(completing)say('page-'+page().choice);}return;}
      if(name==='next'||name==='enter'){
        if(!matches()||state.conflict){say(decision()?page().instruction:'help');return;}
        stop();
        if(page().finished&&state.typed!==page().answer&&!(await save({finished:false})))return;
        if(!(await save({finished:true})))return;
        state.view='reveal';state.choice=page().choice;render();focus();say('page-'+page().choice);return;
      }
      if(name==='continue-story'){
        stop();if(!page().finished){if(!(await finishFixed()))return;}if(state.book.completed){state.view='read';state.index=0;render();say(endPrompt());}
        else{state.index=state.book.pages.findIndex(item=>!item.finished);await loadPage();}focus();return;
      }
      if(!(await save()))return;stop();
      if(name==='home'){state.library=await request('');state.book=null;state.view='home';state.error='';state.conflict=null;render();focus();}
      else if(name==='new'){state.book=await request('',{template});state.index=0;await loadPage();}
      else if(name==='change-word'){state.newFlow=true;state.typed='';state.choice=null;state.view='write';render();focus();say(page().instruction);}
      else if(name==='back'){state.index=Math.max(0,state.index-1);await loadPage();}
      else if(name==='edit'){await loadPage();}
      else if(name==='read-back'||name==='read-next'){state.index+=name==='read-back'?-1:1;render();}
    });
  }
  function readAll(index){stop();if(!state.active||index>=state.book.total||!state.book.pages[index].finished)return;state.view='read';state.index=index;render();say('page-'+page().choice,{done:()=>readAll(index+1)});}
  async function open(refresh=false){
    state.active=true;if(state.library&&!refresh){render();focus();return;}
    try{
      [state.library,state.manifest,state.settings]=await Promise.all([request(''),fetch('/storybooks/audio/manifest.json').then(r=>r.json()),fetch('/api/settings').then(r=>r.json())]);
      if(state.book){await loadBook(state.book.id);}else{state.view='home';render();focus();}
    }catch{state.library=state.library||{books:[]};state.error='Your bookshelf needs a moment. Tap Retry.';render();}
  }
  document.addEventListener('visibilitychange',()=>{if(document.hidden){stop();save();}});
  window.addEventListener('pagehide',()=>{if(state.view==='write')remember();});
  window.Storybooks={open,focus,activate:()=>{state.active=true;},pause:()=>{state.active=false;stop();},beforeHide:()=>save()};
})();
