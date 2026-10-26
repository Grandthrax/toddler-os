'use strict';
const $ = id => document.getElementById(id);
const state = {settings:null, story:null, acknowledged:'', savePromise:null, timer:null,
  undo:[], redo:[], before:null, playing:false, playToken:0, audio:null, finishAudio:null,
  controller:null, sound:null, sounds:new Map(), toastTimer:null, conflictVersion:null,
  words:[], highlighted:null, highlightFrame:null, pointer:null,
  bookOpen:false, opening:false, windowDrag:null, backgroundsOpen:false,
  activeApp:null, desktopRestore:null, desktopPreferences:null, wallpaperSaving:false,
  archivedView:false, libraryBusy:false, ninjaOpen:false, storybooksOpen:false, mouseOpen:false, windowOrder:[]};
const apps={book:{window:'book-window',titlebar:'window-titlebar',maximise:'window-maximise',name:'The Book',
    launch:launchBook,focus:focusBookContent,pause:stopReading},
  backgrounds:{window:'backgrounds-window',titlebar:'backgrounds-titlebar',maximise:'backgrounds-maximise',name:'Backgrounds',
    launch:launchBackgrounds,focus:()=>$('background-choices').querySelector('[aria-pressed=true]')?.focus(),pause:()=>{}},
  ninja:{window:'ninja-window',titlebar:'ninja-titlebar',maximise:'ninja-maximise',name:'Ninja Maths',
    launch:launchNinja,focus:()=>window.NinjaMaths.focus(),pause:()=>window.NinjaMaths.pause(),activate:()=>window.NinjaMaths.activate()},
  storybooks:{window:'storybooks-window',titlebar:'storybooks-titlebar',maximise:'storybooks-maximise',name:'Storybooks',
    launch:launchStorybooks,focus:()=>window.Storybooks.focus(),pause:()=>window.Storybooks.pause(),activate:()=>window.Storybooks.activate()},
  mouse:{window:'mouse-window',titlebar:'mouse-titlebar',maximise:'mouse-maximise',name:'Mouse Missions',
    launch:launchMouse,focus:()=>window.MouseMissions.focus(),pause:()=>window.MouseMissions.pause(),activate:()=>window.MouseMissions.activate()}};
const editing = " \n.,!?'–-";
const alphabet='abcdefghijklmnopqrstuvwxyz';
const icon = name => `<svg aria-hidden="true"><use href="#icon-${name}"/></svg>`;

async function api(path, options={}) {
  const response = await fetch(path, {...options, headers:{'Content-Type':'application/json',
    'X-Little-Pages':'1',...options.headers}});
  if (!response.ok) {
    const detail = await response.json().catch(()=>({error:'We could not reach your pages.'}));
    throw Object.assign(new Error(detail.error), {status:response.status,detail});
  }
  return response.json();
}
function notice(text) {
  $('toast').textContent=text; $('toast').hidden=false;
  clearTimeout(state.toastTimer);
  state.toastTimer=setTimeout(()=>$('toast').hidden=true,4500);
}
function savedStatus(text='Saved', pending=false) {
  $('save-status').querySelector('span').textContent=text;
  $('save-status').classList.toggle('pending',pending);
}
function bufferKey(id) { return `little-pages-draft:${id}`; }
function rememberDraft() {
  if (!state.story) return false;
  try {
    localStorage.setItem(bufferKey(state.story.id),JSON.stringify({text:$('writing').value,
      version:state.conflictVersion??state.story.version,at:Date.now()}));
    return true;
  } catch { return false; }
}
function discardDraft(id) { try {localStorage.removeItem(bufferKey(id));} catch {} }
function updateUndo() { $('undo').disabled=!state.undo.length; }
function snapshot() { const el=$('writing'); return {text:el.value,start:el.selectionStart,end:el.selectionEnd}; }
function addUndo(item=snapshot()) {
  if (!state.undo.length || state.undo.at(-1).text!==item.text) state.undo.push(item);
  if (state.undo.length>500) state.undo.shift();
  state.redo=[]; updateUndo();
}
function changed() {
  if (!state.story) return;
  syncWords();
  const kept=rememberDraft();
  savedStatus(kept?'Saving…':'Keep this page open',true);
  clearTimeout(state.timer); state.timer=setTimeout(saveNow,550);
  updateUndo();
}
async function saveNow() {
  clearTimeout(state.timer);
  if (!state.story) return true;
  if (state.conflictVersion!==null) return false;
  if (state.savePromise) return state.savePromise;
  state.savePromise=(async()=>{
    const id=state.story.id;
    while (state.story?.id===id && $('writing').value!==state.acknowledged) {
      const text=$('writing').value;
      try {
        const saved=await api(`/api/stories/${id}`, {method:'PUT',body:JSON.stringify({text,version:state.story.version})});
        state.story=saved; state.acknowledged=saved.text;
        rememberDraft();
      } catch (error) {
        savedStatus('Writing kept here',true);
        if(error.status===409) {
          state.conflictVersion=state.story.version;$('keep-copy').hidden=false;
          notice(error.detail.story?.archived?'This story was put away. Tap Keep a copy to save your new words.':
            'There is newer writing on another page. Tap Keep a copy to save these words too.');
        }
        else if(error.status===422) { notice(error.message); await refreshSettings(); }
        else notice('Keep this page open. We’ll try saving your writing again.');
        return false;
      }
    }
    if(state.story?.id===id && $('writing').value===state.acknowledged) {
      discardDraft(id); savedStatus();
    }
    return true;
  })();
  try {return await state.savePromise;} finally {state.savePromise=null;}
}
function titleFor(text) {return text.trim().split('\n')[0].slice(0,32)||'A new little story';}
function dateLabel(date) {
  const value=new Date(date),today=new Date();
  return value.toDateString()===today.toDateString()?'Today':value.toLocaleDateString('en-GB',{day:'numeric',month:'short'});
}
function closeStartMenu() {
  $('start-menu').hidden=true;$('start-button').setAttribute('aria-expanded','false');
}
function activateApp(name) {
  if(state.activeApp && state.activeApp!==name) apps[state.activeApp].pause();
  state.activeApp=name;
  if(name) apps[name].activate?.();
  if(name) state.windowOrder=[...state.windowOrder.filter(id=>id!==name),name];
  for(const [id,app] of Object.entries(apps)) {
    $(app.window).style.zIndex=id===name?'12':'10';
    $(app.window).classList.toggle('inactive',id!==name);
    $('taskbar-'+id).setAttribute('aria-pressed',String(id===name));
  }
}
function focusRemainingApp() {
  const visible=[...state.windowOrder].reverse().find(id=>!$(apps[id].window).hidden);
  activateApp(visible||null);
  if(visible) apps[visible].focus();
}
function focusBookContent() {
  if(state.story && !$('write-view').hidden) $('writing').focus();
  else $(state.archivedView?'show-archive':'new-story').focus();
}
function showBookWindow() {
  closeStartMenu();state.desktopRestore=null;$('book-window').hidden=false;activateApp('book');
  $('taskbar-book').classList.add('running');
  requestAnimationFrame(()=>{
    syncWordLayout();
    focusBookContent();
  });
}
async function launchBook() {
  if(state.opening) return;
  if(state.bookOpen) {showBookWindow();return;}
  state.opening=true;
  try {
    await refreshSettings();await home();state.bookOpen=true;showBookWindow();
  } finally {state.opening=false;}
}
async function desktop(close=false) {
  stopReading();
  if(!(await saveNow())) {notice('Keep this window open until your writing is saved.');return;}
  closeStartMenu();$('book-window').hidden=true;
  if(close) {state.bookOpen=false;state.story=null;$('taskbar-book').classList.remove('running');}
  focusRemainingApp();if(!state.activeApp) $('desktop-book').focus();
}
function maximiseApp(name) {
  const app=apps[name],button=$(app.maximise),maximised=$(app.window).classList.toggle('maximised');
  activateApp(name);
  button.setAttribute('aria-label',maximised?`Restore ${app.name} window`:`Maximise ${app.name}`);
  button.setAttribute('title',maximised?'Restore':'Maximise');
  button.setAttribute('aria-pressed',String(maximised));
  button.querySelector('use').setAttribute('href',maximised?'#icon-restore':'#icon-maximise');
  requestAnimationFrame(syncWordLayout);
}
function applyWallpaper(id) {
  const choice=state.desktopPreferences.choices.find(w=>w.id===id);
  if(!choice) return;
  $('desktop-view').style.backgroundImage=`url("${choice.image}")`;
  $('background-preview-image').src=choice.image;
  $('background-preview-image').alt=choice.name+' background';
  $('background-current-name').textContent=choice.name;
  for(const button of $('background-choices').children) button.setAttribute('aria-pressed',String(button.dataset.wallpaper===id));
}
function renderBackgrounds() {
  $('background-choices').replaceChildren();
  for(const choice of state.desktopPreferences.choices) {
    const button=document.createElement('button');button.className='background-choice';button.dataset.wallpaper=choice.id;
    button.setAttribute('aria-label',choice.name+' background');
    const image=document.createElement('img');image.src=choice.image;image.alt='';image.draggable=false;
    const name=document.createElement('span');name.textContent=choice.name;button.append(image,name);
    button.onclick=()=>chooseWallpaper(choice.id);$('background-choices').append(button);
  }
  applyWallpaper(state.desktopPreferences.wallpaper);
}
async function chooseWallpaper(id) {
  if(state.wallpaperSaving || id===state.desktopPreferences.wallpaper) return;
  state.wallpaperSaving=true;applyWallpaper(id);
  for(const button of $('background-choices').children) button.disabled=true;
  $('background-save-status').textContent='Saving your picture…';$('backgrounds-done').disabled=true;
  try {
    state.desktopPreferences=await api('/api/desktop',{method:'PUT',body:JSON.stringify({wallpaper:id})});
    applyWallpaper(state.desktopPreferences.wallpaper);$('background-save-status').textContent='Your picture is saved.';
  } catch(error) {
    applyWallpaper(state.desktopPreferences.wallpaper);
    $('background-save-status').textContent='That picture could not be saved. Please try again.';
    notice('Your previous picture is still here. Choose a picture to try again.');
  } finally {
    state.wallpaperSaving=false;$('backgrounds-done').disabled=false;
    for(const button of $('background-choices').children) button.disabled=false;
  }
}
function launchBackgrounds() {
  stopReading();closeStartMenu();state.desktopRestore=null;state.backgroundsOpen=true;
  $('backgrounds-window').hidden=false;$('taskbar-backgrounds').classList.add('running');activateApp('backgrounds');
  $('background-choices').querySelector('[aria-pressed=true]')?.focus();
}
function hideBackgrounds(close=false) {
  if(state.wallpaperSaving) {notice('Your picture is saving. Just a moment.');return;}
  $('backgrounds-window').hidden=true;
  if(close) {state.backgroundsOpen=false;$('taskbar-backgrounds').classList.remove('running');}
  focusRemainingApp();if(!state.activeApp) $('desktop-backgrounds').focus();
}
async function launchNinja() {
  closeStartMenu();state.desktopRestore=null;
  const refresh=!state.ninjaOpen;state.ninjaOpen=true;
  $('ninja-window').hidden=false;$('taskbar-ninja').classList.add('running');activateApp('ninja');
  await window.NinjaMaths.open(refresh);
}
function hideNinja(close=false) {
  if(!window.NinjaMaths.canHide()) {notice('Your mission is saving. Just a moment.');return;}
  window.NinjaMaths.pause();$('ninja-window').hidden=true;
  if(close) {state.ninjaOpen=false;$('taskbar-ninja').classList.remove('running');}
  focusRemainingApp();if(!state.activeApp) $('desktop-ninja').focus();
}
async function launchMouse() {
  closeStartMenu();state.desktopRestore=null;
  const refresh=!state.mouseOpen;state.mouseOpen=true;
  $('mouse-window').hidden=false;$('taskbar-mouse').classList.add('running');activateApp('mouse');
  await window.MouseMissions.open(refresh);
}
async function hideMouse(close=false) {
  if(!(await window.MouseMissions.beforeHide())) {notice('Keep your programme open until it is saved.');return;}
  window.MouseMissions.pause();$('mouse-window').hidden=true;
  if(close) {state.mouseOpen=false;$('taskbar-mouse').classList.remove('running');}
  focusRemainingApp();if(!state.activeApp) $('desktop-mouse').focus();
}
async function launchStorybooks() {
  closeStartMenu();state.desktopRestore=null;
  const refresh=!state.storybooksOpen;state.storybooksOpen=true;
  $('storybooks-window').hidden=false;$('taskbar-storybooks').classList.add('running');activateApp('storybooks');
  await window.Storybooks.open(refresh);
}
async function hideStorybooks(close=false) {
  if(!(await window.Storybooks.beforeHide())) {notice('Keep your book open until your words are saved.');return;}
  window.Storybooks.pause();$('storybooks-window').hidden=true;
  if(close) {state.storybooksOpen=false;$('taskbar-storybooks').classList.remove('running');}
  focusRemainingApp();if(!state.activeApp) $('desktop-storybooks').focus();
}
async function showDesktop() {
  if(!(await window.MouseMissions.beforeHide())) {notice('Your mouse programme needs to save first.');return;}
  if(!(await window.Storybooks.beforeHide())) {notice('Your storybook needs to save first.');return;}
  if(!window.NinjaMaths.canHide()) {notice('Your mission is saving. Just a moment.');return;}
  closeStartMenu();stopReading();
  const visible=Object.keys(apps).filter(id=>!$(apps[id].window).hidden);
  if(visible.length) {
    if(!(await saveNow())) {notice('Keep this window open until your writing is saved.');showBookWindow();return;}
    state.desktopRestore={visible,active:state.activeApp};
    for(const id of visible) $(apps[id].window).hidden=true;
    activateApp(null);$('desktop-book').focus();
  } else if(state.desktopRestore) {
    const restore=state.desktopRestore;state.desktopRestore=null;
    for(const id of restore.visible) $(apps[id].window).hidden=false;
    activateApp(restore.active);requestAnimationFrame(syncWordLayout);
    if(restore.active) apps[restore.active].focus();
  }
}
async function backgroundsDone() {
  if(state.wallpaperSaving) return;
  await showDesktop();
  if(!state.activeApp) {state.desktopRestore=null;state.backgroundsOpen=false;$('taskbar-backgrounds').classList.remove('running');}
}
function updateClock() {
  const date=new Date();
  $('desktop-time').dateTime=date.toISOString();
  $('desktop-time').textContent=date.toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'});
  $('desktop-date').textContent=date.toLocaleDateString('en-GB',{day:'2-digit',month:'2-digit',year:'numeric'});
}
async function home(archived=false) {
  stopReading();
  if (!(await saveNow())) return;
  const {stories}=await api('/api/stories'+(archived?'?archived=1':''));
  $('write-view').hidden=true; $('home-view').hidden=false; $('loading-view').hidden=true;
  state.story=null;state.archivedView=archived;$('story-list').replaceChildren();
  $('home-heading').textContent=archived?'Put-away stories':'My stories';
  $('library-caption').textContent=archived?'Safe here, whenever you want them again.':'A fresh page, or a story to come back to.';
  $('library-subheading').textContent=archived?'Stories to bring back':'Your writing';
  $('new-story').hidden=archived;
  $('show-archive').setAttribute('aria-pressed',String(archived));
  $('show-archive').querySelector('span').textContent=archived?'My stories':'Put-away stories';
  $('show-archive').querySelector('use').setAttribute('href',archived?'#icon-book':'#icon-archive');
  for(const story of stories) {
    const tile=document.createElement('article');tile.className='story-tile';tile.dataset.story=story.id;
    const card=document.createElement(archived?'div':'button');card.className='story-card';
    card.innerHTML=icon('book')+'<strong></strong><small></small>'+(archived?'':icon('arrow'));
    card.querySelector('svg').classList.add('card-icon');
    if(!archived) {card.querySelector('svg:last-child').classList.add('card-arrow');card.onclick=()=>openStory(story.id).catch(showError);}
    card.querySelector('strong').textContent=titleFor(story.preview);
    card.querySelector('small').textContent=dateLabel(story.updated)+' · Your writing';
    const action=document.createElement('button');action.className='story-archive-action';
    action.innerHTML=icon(archived?'undo':'archive')+(archived?'Bring back':'Put away');
    action.setAttribute('aria-label',`${archived?'Bring back':'Put away'}: ${titleFor(story.preview)}`);
    action.onclick=()=>archiveStory(story,!archived).catch(showError);
    tile.append(card,action);$('story-list').append(tile);
  }
  if(!archived) {
    const newCard=document.createElement('button'); newCard.className='story-card new-card';
    newCard.innerHTML=icon('plus')+'<strong>A fresh little page</strong>';
    newCard.onclick=()=>createStory().catch(showError); $('story-list').append(newCard);
  } else if(!stories.length) {
    const empty=document.createElement('p');empty.className='archive-empty';
    empty.innerHTML=icon('archive')+'<strong>No stories put away yet.</strong><span>Your writing is in My stories.</span>';
    $('story-list').append(empty);
  }
  $('story-count').textContent=stories.length?`${stories.length} ${stories.length===1?'story':'stories'}${archived?' put away':''}`:'';
}
async function archiveStory(story, archived) {
  if(state.libraryBusy) return;
  state.libraryBusy=true;$('story-list').setAttribute('aria-busy','true');
  for(const button of $('home-view').querySelectorAll('button')) button.disabled=true;
  const view=state.archivedView;
  try {
    await api(`/api/stories/${story.id}/archive`,{method:'POST',body:JSON.stringify({archived,version:story.version})});
    await home(view);
    notice(archived?'Story put away. You can bring it back from Put-away stories.':'Your story is back in My stories.');
  } catch(error) {
    if(error.status===409) await home(view);
    if(error.status) showError(error);
    else notice(archived?'We could not put this story away. Your writing is still here. Try again.':
      'We could not bring this story back yet. It is still safe here. Try again.');
  } finally {
    state.libraryBusy=false;$('story-list').removeAttribute('aria-busy');
    for(const button of $('home-view').querySelectorAll('button')) button.disabled=false;
    $('show-archive').focus();
  }
}
async function createStory() {
  if(!(await saveNow())) return;
  const story=await api('/api/stories',{method:'POST',body:'{}'});
  await openStory(story.id);
}
async function openStory(id) {
  if(!(await saveNow())) return;
  await refreshSettings();
  const story=await api(`/api/stories/${id}`);
  if(story.archived) {await home(true);notice('Bring this story back to write in it.');return;}
  state.story=story; state.acknowledged=story.text; state.undo=[]; state.redo=[];state.conflictVersion=null;$('keep-copy').hidden=true;
  $('writing').value=story.text;
  $('write-view').hidden=false; $('home-view').hidden=true;
  $('writing').maxLength=state.settings.max_text;
  savedStatus(); updateUndo();
  try {
    const draft=JSON.parse(localStorage.getItem(bufferKey(id))||'null');
    if(draft && typeof draft.text==='string' && draft.text!==story.text) {
      if(draft.version===story.version) {
        $('writing').value=draft.text; changed(); notice('Your last little words are back.');
      } else {
        $('writing').value=draft.text;state.conflictVersion=draft.version;$('keep-copy').hidden=false;
        savedStatus('Keep a copy to save',true);
        notice('Your unfinished words are here. Tap Keep a copy to save them on a fresh page.');
      }
    }
  } catch {}
  syncWords();
  $('writing').focus(); $('writing').setSelectionRange($('writing').value.length,$('writing').value.length);
}
async function refreshSettings() {
  state.settings=await api('/api/settings');
  const letters=state.settings.letters;
  $('home-letters').replaceChildren(); $('letter-buttons').replaceChildren();
  for(const letter of letters) {
    const small=document.createElement('span'); small.textContent=letter; $('home-letters').append(small);
    const button=document.createElement('button'); button.className='letter-button'; button.textContent=letter;
    button.setAttribute('aria-label',`Write ${letter} and hear its sound`);
    button.dataset.letter=letter;
    button.addEventListener('mousedown',e=>e.preventDefault());
    button.onclick=()=>insert(letter,true); $('letter-buttons').append(button);
    if(!state.sounds.has(letter) && state.settings.phonics_available.includes(letter)) {
      const audio=window.LearningAudio.create(`/phonics/${letter}`); audio.preload='auto'; state.sounds.set(letter,audio);
    }
  }
  for(const id of ['read-all','read-word','read-sentence']) $(id).disabled=!state.settings.voice_ready;
  const word=['mat','sat','dad','am','at','in','pin','dog','cat','sun'].find(w=>[...w].every(c=>letters.includes(c)));
  $('writing-hint').textContent=word?`Try a little word: ${word}`:'One little sound at a time.';
}
function cleanInsert(text) {
  return [...text.toLowerCase().replaceAll('\r\n','\n').replaceAll('\r','\n')]
    .filter(c=>alphabet.includes(c)||editing.includes(c)).join('');
}
function sound(letter) {
  if(!state.settings.phonics_enabled) return;
  if(state.sound) {state.sound.pause();state.sound.currentTime=0;}
  if(!state.sounds.has(letter) && state.settings.phonics_available.includes(letter)) {
    const audio=window.LearningAudio.create(`/phonics/${letter}`);audio.preload='auto';state.sounds.set(letter,audio);
  }
  const audio=state.sounds.get(letter); if(!audio) return;
  state.sound=audio; audio.currentTime=0;
  const button=$('letter-buttons').querySelector(`[data-letter="${letter}"]`);
  button?.classList.add('sounding'); setTimeout(()=>button?.classList.remove('sounding'),260);
  audio.play().catch(()=>{});
}
function insert(text, feedback=false) {
  const el=$('writing'),filtered=cleanInsert(text);
  if(filtered!==text.toLowerCase().replaceAll('\r\n','\n').replaceAll('\r','\n')) notice('Try letters, spaces and simple punctuation.');
  if(!filtered) return;
  const room=state.settings.max_text-(el.value.length-(el.selectionEnd-el.selectionStart));
  if(filtered.length>room) {notice('This page is full. Start a fresh little story.');return;}
  stopReading(); addUndo();
  el.setRangeText(filtered,el.selectionStart,el.selectionEnd,'end'); el.focus(); changed();
  if(feedback && filtered.length===1 && alphabet.includes(filtered)) sound(filtered);
  else if(filtered===' ' && state.settings.auto_read_words) read('word').catch(showError);
}
function backspace() {
  const el=$('writing'),start=el.selectionStart,end=el.selectionEnd;
  stopReading();
  if(start===0 && end===0) {el.focus();return;}
  const from=start===end?start-[...el.value.slice(0,start)].at(-1).length:start;
  addUndo();el.setRangeText('',from,end,'end');el.focus();changed();
}
function undo(redo=false) {
  const source=redo?state.redo:state.undo,target=redo?state.undo:state.redo;
  if(!source.length) return;
  stopReading(); const item=source.pop();target.push(snapshot());
  $('writing').value=item.text; $('writing').focus(); $('writing').setSelectionRange(item.start,item.end);
  changed(); updateUndo();
}
function syncWordLayout() {
  const el=$('writing'),layer=$('word-layer'),style=getComputedStyle(el);
  for(const property of ['fontFamily','fontSize','fontWeight','fontStyle','lineHeight','letterSpacing','wordSpacing',
    'paddingTop','paddingRight','paddingBottom','paddingLeft','textAlign','textIndent']) layer.style[property]=style[property];
  layer.style.width=el.clientWidth+'px';
  layer.style.transform=`translate(${-el.scrollLeft}px,${-el.scrollTop}px)`;
}
function syncWords() {
  const text=$('writing').value,layer=$('word-layer');
  layer.replaceChildren();state.words=[];state.highlighted=null;
  let end=0;
  for(const match of text.matchAll(/[A-Za-z]+(?:['’–-][A-Za-z]+)*/g)) {
    layer.append(document.createTextNode(text.slice(end,match.index)));
    const node=document.createElement('span');node.textContent=match[0];
    layer.append(node);
    end=match.index+match[0].length;
    state.words.push({start:match.index,end,node});
  }
  layer.append(document.createTextNode(text.slice(end)+'\u200b'));
  syncWordLayout();
}
function highlightWord(start=null,end=null) {
  const word=start===null?null:state.words.find(w=>w.start<end && w.end>start);
  if(state.highlighted===word) return;
  state.highlighted?.node.classList.remove('spoken-word');
  state.highlighted=word||null;
  if(!word) return;
  word.node.classList.add('spoken-word');
  const el=$('writing'),bounds=el.getBoundingClientRect(),rect=word.node.getBoundingClientRect();
  if(rect.bottom>bounds.bottom-10) el.scrollTop+=rect.bottom-bounds.bottom+10;
  else if(rect.top<bounds.top+10) el.scrollTop+=rect.top-bounds.top-10;
  syncWordLayout();
  const content=$('book-content'),visible=content.getBoundingClientRect(),highlight=word.node.getBoundingClientRect();
  if(highlight.bottom>visible.bottom-12) content.scrollTop+=highlight.bottom-visible.bottom+12;
  else if(highlight.top<visible.top+12) content.scrollTop+=highlight.top-visible.top-12;
}
function stopReading() {
  state.playToken++; state.controller?.abort(); state.controller=null;
  cancelAnimationFrame(state.highlightFrame);state.highlightFrame=null;highlightWord();
  if(state.audio) {state.audio.pause();state.audio=null;}
  if(state.sound) {state.sound.pause();state.sound.currentTime=0;state.sound=null;}
  state.finishAudio?.(); state.finishAudio=null;
  state.playing=false; $('stop-reading').hidden=true; $('read-all').hidden=false; $('read-status').textContent='';
}
function readingRange(mode) {
  const el=$('writing'),text=el.value,caret=el.selectionStart;
  if(el.selectionEnd>caret) return {start:caret,end:el.selectionEnd};
  if(mode==='all') return {start:0,end:text.length};
  if(mode==='word') {
    return state.words.find(w=>w.start<=caret && w.end>=caret)||state.words.findLast(w=>w.end<=caret)||{start:caret,end:caret};
  }
  let position=caret;
  while(position>0 && /[\s.!?]/.test(text[position-1])) position--;
  const start=Math.max(text.lastIndexOf('.',position-1),text.lastIndexOf('!',position-1),text.lastIndexOf('?',position-1),text.lastIndexOf('\n',position-1))+1;
  const rest=text.slice(start),end=rest.search(/[.!?\n]/);
  return {start,end:end<0?text.length:start+end+1};
}
async function read(mode,range=readingRange(mode)) {
  const fullText=$('writing').value,selected=fullText.slice(range.start,range.end);
  const leading=selected.length-selected.trimStart().length,text=selected.trim(),offset=range.start+leading;
  stopReading(); if(!text) {notice('Write a little something first.');return;}
  const token=state.playToken;
  state.playing=true; $('stop-reading').hidden=false; $('read-all').hidden=true;
  // Bounded chunks keep the stop button responsive for long stories.
  const chunks=[...text.matchAll(/.{1,350}(?:\s|$)|\S{1,350}/gs)];
  try {
    for(const match of chunks) {
      const chunk=match[0],chunkStart=offset+match.index;
      if(token!==state.playToken) break;
      $('read-status').textContent='Getting your words ready…';
      state.controller=new AbortController();
      const response=await fetch('/api/read',{method:'POST',headers:{'Content-Type':'application/json','X-Little-Pages':'1'},
        body:JSON.stringify({text:chunk}),signal:state.controller.signal});
      if(!response.ok) throw new Error('The reading voice needs a moment. Try again.');
      const timings=JSON.parse(response.headers.get('X-Little-Pages-Words')||'[]');
      const blob=await response.blob(); if(token!==state.playToken) break;
      const url=URL.createObjectURL(blob),audio=window.LearningAudio.create(url); state.audio=audio;
      $('read-status').textContent='Listening to your words…';
      const follow=()=>{
        if(token!==state.playToken) return;
        const current=timings.find(([, ,start,end])=>audio.currentTime>=start && audio.currentTime<end);
        if(current) highlightWord(chunkStart+current[0],chunkStart+current[1]);else highlightWord();
        state.highlightFrame=requestAnimationFrame(follow);
      };
      let finish;
      try {
        await new Promise((resolve,reject)=>{
          finish=resolve;state.finishAudio=finish;
          audio.onplaying=()=>{cancelAnimationFrame(state.highlightFrame);follow();};
          audio.onended=resolve; audio.onerror=()=>reject(new Error('Let’s try reading again.'));
          audio.play().catch(reject);
        });
      } finally {
        URL.revokeObjectURL(url);audio.onplaying=null;
        if(state.finishAudio===finish) state.finishAudio=null;
        if(token===state.playToken) {cancelAnimationFrame(state.highlightFrame);state.highlightFrame=null;highlightWord();}
      }
    }
  } catch(error) {if(error.name!=='AbortError' && token===state.playToken) notice(error.message);}
  finally {if(token===state.playToken) stopReading();}
}
async function history() {
  stopReading();
  if(!(await saveNow())) return;
  const {revisions}=await api(`/api/stories/${state.story.id}/revisions`);
  $('revision-list').replaceChildren();
  for(const revision of revisions) {
    const row=document.createElement('div');row.className='revision';
    row.innerHTML='<div><p></p><small></small></div><button class="button"></button>';
    row.querySelector('p').textContent=revision.preview||'A fresh, empty page';
    row.querySelector('small').textContent=dateLabel(revision.created)+' · '+new Date(revision.created).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'});
    const button=row.querySelector('button');button.textContent=revision.version===state.story.version?'Your page now':'Bring this back';
    button.disabled=revision.version===state.story.version;
    button.onclick=async()=>{
      try {
        const restored=await api(`/api/stories/${state.story.id}/restore`,{method:'POST',body:JSON.stringify({version:state.story.version,revision:revision.id})});
        addUndo();state.story=restored;state.acknowledged=restored.text;$('writing').value=restored.text;
        syncWords();
        discardDraft(restored.id);savedStatus();$('history-dialog').close();$('writing').focus();notice('Your earlier words are back.');
      } catch(error) {showError(error);}
    };
    $('revision-list').append(row);
  }
  $('history-dialog').showModal();
}
function showError(error) {notice(error.message||'Let’s try that again.');}

$('new-story').onclick=()=>createStory().catch(showError);
$('go-home').onclick=()=>home().then(()=>$('new-story').focus()).catch(showError);
$('show-archive').onclick=()=>home(!state.archivedView).then(()=>$('show-archive').focus()).catch(showError);
function selectDesktopIcon(name) {
  for(const id of Object.keys(apps)) {
    $('desktop-'+id).classList.toggle('selected',id===name);
    $('desktop-'+id).setAttribute('aria-pressed',String(id===name));
  }
}
for(const name of Object.keys(apps)) {
  const launch=()=>Promise.resolve(apps[name].launch()).catch(showError);
  $('desktop-'+name).onclick=e=>{selectDesktopIcon(name);if(e.detail===0 || e.pointerType==='touch') launch();};
  $('desktop-'+name).addEventListener('keydown',e=>{if(e.key===' ') {e.preventDefault();selectDesktopIcon(name);}});
  $('desktop-'+name).ondblclick=launch;
}
$('start-book').onclick=()=>launchBook().catch(showError);
$('start-backgrounds').onclick=launchBackgrounds;
$('start-ninja').onclick=()=>launchNinja().catch(showError);
$('start-storybooks').onclick=()=>launchStorybooks().catch(showError);
$('start-mouse').onclick=()=>launchMouse().catch(showError);
$('taskbar-mouse').onclick=()=>{if(state.activeApp==='mouse')hideMouse().catch(showError);else launchMouse().catch(showError);};
$('taskbar-storybooks').onclick=()=>{if(state.activeApp==='storybooks')hideStorybooks();else launchStorybooks().catch(showError);};
$('taskbar-book').onclick=()=>{
  if(state.activeApp==='book') desktop().catch(showError);else launchBook().catch(showError);
};
$('taskbar-backgrounds').onclick=()=>{if(state.activeApp==='backgrounds') hideBackgrounds();else launchBackgrounds();};
$('taskbar-ninja').onclick=()=>{if(state.activeApp==='ninja') hideNinja();else launchNinja().catch(showError);};
$('start-button').onclick=()=>{
  const opening=$('start-menu').hidden;$('start-menu').hidden=!opening;
  $('start-button').setAttribute('aria-expanded',String(opening));
  if(opening) $('start-book').focus();
};
$('window-minimise').onclick=()=>desktop().catch(showError);
$('window-close').onclick=()=>desktop(true).catch(showError);
$('window-maximise').onclick=()=>maximiseApp('book');
$('backgrounds-minimise').onclick=()=>hideBackgrounds();
$('backgrounds-close').onclick=()=>hideBackgrounds(true);
$('backgrounds-maximise').onclick=()=>maximiseApp('backgrounds');
$('backgrounds-done').onclick=()=>backgroundsDone().catch(showError);
$('ninja-minimise').onclick=()=>hideNinja();
$('ninja-close').onclick=()=>hideNinja(true);
$('ninja-maximise').onclick=()=>maximiseApp('ninja');
$('storybooks-minimise').onclick=()=>hideStorybooks();
$('storybooks-close').onclick=()=>hideStorybooks(true);
$('storybooks-maximise').onclick=()=>maximiseApp('storybooks');
$('mouse-minimise').onclick=()=>hideMouse().catch(showError);
$('mouse-close').onclick=()=>hideMouse(true).catch(showError);
$('mouse-maximise').onclick=()=>maximiseApp('mouse');
$('show-desktop').onclick=()=>showDesktop().catch(showError);
$('desktop-view').addEventListener('click',e=>{
  if(!e.target.closest('.desktop-icon,.book-window,.taskbar,.start-menu')) {
    closeStartMenu();selectDesktopIcon(null);
  }
});
document.addEventListener('keydown',e=>{
  if(e.key==='Escape' && !$('start-menu').hidden) {closeStartMenu();$('start-button').focus();}
});
for(const [name,app] of Object.entries(apps)) {
  const titlebar=$(app.titlebar),windowEl=$(app.window);
  windowEl.addEventListener('pointerdown',()=>activateApp(name),true);
  windowEl.addEventListener('focusin',()=>activateApp(name));
  titlebar.addEventListener('dblclick',e=>{if(!e.target.closest('button')) maximiseApp(name);});
  titlebar.addEventListener('pointerdown',e=>{
    if(e.button!==0 || e.target.closest('button') || windowEl.classList.contains('maximised') || innerWidth<=620) return;
    const rect=windowEl.getBoundingClientRect();
    state.windowDrag={app:name,x:e.clientX,y:e.clientY,left:rect.left,top:rect.top};titlebar.setPointerCapture(e.pointerId);
  });
  titlebar.addEventListener('pointermove',e=>{
    const drag=state.windowDrag;if(!drag || drag.app!==name) return;
    const bounds=windowEl.getBoundingClientRect();
    const left=Math.max(0,Math.min(innerWidth-bounds.width,drag.left+e.clientX-drag.x));
    const top=Math.max(0,Math.min(innerHeight-74-bounds.height,drag.top+e.clientY-drag.y));
    windowEl.style.setProperty('--window-left',left+'px');windowEl.style.setProperty('--window-top',top+'px');windowEl.classList.add('window-moved');
  });
  for(const event of ['pointerup','pointercancel','lostpointercapture']) titlebar.addEventListener(event,()=>{state.windowDrag=null;});
  window.addEventListener('resize',()=>windowEl.classList.remove('window-moved'));
}
updateClock();setInterval(updateClock,30000);
$('undo').onclick=()=>undo();
for(const id of ['insert-space','insert-enter','delete-backward']) $(id).addEventListener('mousedown',e=>e.preventDefault());
$('insert-space').onclick=()=>insert(' ');
$('insert-enter').onclick=()=>insert('\n');
$('delete-backward').onclick=backspace;
$('keep-copy').onclick=async()=>{
  try {
    const oldId=state.story.id;
    const copy=await api(`/api/stories/${oldId}/fork`,{method:'POST',body:JSON.stringify({text:$('writing').value,version:state.conflictVersion})});
    discardDraft(oldId);state.story=copy;state.acknowledged=copy.text;state.conflictVersion=null;
    $('keep-copy').hidden=true;savedStatus();notice('Both toddler os are safe.');
  } catch(error) {showError(error);}
};
$('history').onclick=()=>history().catch(showError);
$('close-history').onclick=()=>$('history-dialog').close();
for(const [id,mode] of [['read-all','all'],['read-word','word'],['read-sentence','sentence']]) $(id).onclick=()=>read(mode).catch(showError);
$('stop-reading').onclick=stopReading;
$('writing').addEventListener('scroll',syncWordLayout);
new ResizeObserver(syncWordLayout).observe($('writing'));
window.addEventListener('resize',syncWordLayout);
document.fonts.ready.then(syncWordLayout);
$('writing').addEventListener('pointerdown',e=>{
  stopReading();state.pointer={x:e.clientX,y:e.clientY,dragged:false};
});
$('writing').addEventListener('pointermove',e=>{
  if(state.pointer && Math.hypot(e.clientX-state.pointer.x,e.clientY-state.pointer.y)>6) state.pointer.dragged=true;
});
$('writing').addEventListener('pointercancel',()=>{state.pointer=null;});
$('writing').addEventListener('click',e=>{
  const pointer=state.pointer;state.pointer=null;
  if(!pointer || pointer.dragged || e.detail!==1 || e.shiftKey || e.ctrlKey || e.metaKey || e.altKey ||
    $('writing').selectionStart!==$('writing').selectionEnd || !state.settings.voice_ready) return;
  const word=state.words.find(w=>[...w.node.getClientRects()].some(r=>
    e.clientX>=r.left && e.clientX<=r.right && e.clientY>=r.top && e.clientY<=r.bottom));
  if(word) read('word',word).catch(showError);
});
$('writing').addEventListener('beforeinput',e=>{
  if(e.inputType==='historyUndo'||e.inputType==='historyRedo') {e.preventDefault();undo(e.inputType==='historyRedo');return;}
  if(e.inputType.startsWith('insert')) {
    e.preventDefault();
    const text=e.inputType==='insertLineBreak'||e.inputType==='insertParagraph'?'\n':e.data;
    if(typeof text==='string') insert(text,true);
  } else {stopReading();state.before=snapshot();addUndo();}
});
$('writing').addEventListener('input',()=>changed());
$('writing').addEventListener('paste',e=>{e.preventDefault();insert(e.clipboardData.getData('text/plain'));});
$('writing').addEventListener('drop',e=>e.preventDefault());
$('writing').addEventListener('keydown',e=>{
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z') {e.preventDefault();undo(e.shiftKey);}
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='y') {e.preventDefault();undo(true);}
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s') {e.preventDefault();saveNow();}
  if(e.key==='Escape') stopReading();
});
document.addEventListener('visibilitychange',()=>{if(document.hidden){stopReading();saveNow();}});
window.addEventListener('beforeunload',e=>{
  if(state.story && $('writing').value!==state.acknowledged) {rememberDraft();e.preventDefault();e.returnValue='';}
});
window.addEventListener('online',()=>saveNow());
setInterval(()=>{if(state.story && !state.savePromise && $('writing').value!==state.acknowledged) saveNow();},5000);
async function start() {
  try {
    state.desktopPreferences=await api('/api/desktop');renderBackgrounds();
    await refreshSettings();await home();$('desktop-view').hidden=false;
  }
  catch(error) {$('desktop-view').hidden=true;$('loading-view').hidden=false;showError(error);}
}
$('retry').onclick=start;
window.ChildLockHooks={
  save:async()=>{await Promise.allSettled([saveNow(),window.Storybooks.beforeHide(),window.MouseMissions.beforeHide()]);},
  pause:()=>{stopReading();window.NinjaMaths.pause();window.Storybooks.pause();window.MouseMissions.pause();},
  resume:()=>{if(state.activeApp)apps[state.activeApp].activate?.();}
};
window.ChildLock.ready.then(start);
