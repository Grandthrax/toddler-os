/* The child lock keeps the current apps and drafts in place underneath it. */
(() => {
  'use strict';
  const dialog=document.getElementById('child-lock'),form=document.getElementById('child-unlock');
  const input=document.getElementById('child-password'),message=document.getElementById('child-lock-message');
  let config={enabled:false,idle_seconds:300},locked=true,saver=false,starting=true,lastActivity=performance.now(),lastSent=0,busy=false,restoring=null,readyResolve,activityTimer,generation=0;
  const ready=new Promise(resolve=>readyResolve=resolve);
  window.ChildLock={ready,locked:()=>locked};
  async function request(path,body) {
    const response=await fetch('/api/lock/'+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json','X-Little-Pages':'1'},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(10000)});
    const data=await response.json();if(!response.ok)throw Object.assign(new Error(data.error),{status:response.status});return data;
  }
  function stopSounds(){window.LearningAudio?.suspend();window.ChildLockHooks?.pause();}
  function cover(asSaver=false) {
    generation++;
    restoring=document.activeElement;locked=true;saver=asSaver;
    dialog.classList.toggle('show-saver',saver);if(!dialog.open)dialog.showModal();
    stopSounds();input.value='';message.textContent='';if(!saver)input.focus();
  }
  function uncover() {
    generation++;
    locked=false;saver=false;starting=false;dialog.close();input.value='';lastActivity=performance.now();lastSent=0;
    window.LearningAudio?.resume();readyResolve();window.ChildLockHooks?.resume();
    if(restoring?.isConnected)restoring.focus({preventScroll:true});
  }
  function wake(){if(!saver)return;saver=false;dialog.classList.remove('show-saver');input.focus();}
  async function lock() {
    if(locked||busy||!config.enabled)return;
    busy=true;
    // Saving happens while the session is still valid; failed saves keep their drafts in the live app.
    try {await window.ChildLockHooks?.save();}catch{}
    cover(true);
    try {await request('lock',{});}catch{message.textContent='Your screen is resting. Try unlocking when it is ready.';}
    finally {busy=false;}
  }
  async function status() {
    const expectedGeneration=generation;
    try {
      config=await request('status');
      if(generation!==expectedGeneration)return;
      if(!config.enabled){if(locked)uncover();}
      else if(config.locked){if(!locked)cover(true);}
      else if(locked&&starting)uncover();
      else if(locked)request('lock',{}).catch(()=>{});
    }catch{if(starting){cover();message.textContent='Waiting for your learning computer…';}}
  }
  function sendActivity() {
    if(locked||!config.enabled)return;
    const expectedGeneration=generation;
    lastSent=performance.now();request('activity',{}).catch(error=>{if(error.status===423&&generation===expectedGeneration)cover(true);});
  }
  function activity(event) {
    if(locked){
      if(saver){if(event.type==='keydown')event.preventDefault();wake();}
      if(event.type==='keydown'){event.stopPropagation();if(!dialog.contains(event.target))event.preventDefault();}
      return;
    }
    lastActivity=performance.now();
    if(config.enabled&&(!lastSent||lastActivity-lastSent>20000))sendActivity();
    clearTimeout(activityTimer);activityTimer=setTimeout(sendActivity,800);
  }
  dialog.addEventListener('cancel',event=>event.preventDefault());
  for(const type of ['pointerdown','pointermove','keydown','wheel','touchstart'])document.addEventListener(type,activity,{capture:true,passive:type==='touchstart'});
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(busy)return;busy=true;message.textContent='';
    const button=document.getElementById('child-unlock-button');button.disabled=true;
    try {config=await request('unlock',{password:input.value});uncover();}
    catch(error){message.textContent=error.message;input.select();input.focus();}
    finally {busy=false;button.disabled=false;}
  });
  const keys=document.getElementById('child-lock-keys');
  for(const letters of ['qwertyuiop','asdfghjkl','zxcvbnm']){
    const row=document.createElement('div');row.className='child-key-row';
    for(const letter of letters){
      const button=document.createElement('button');button.type='button';button.textContent=letter;button.setAttribute('aria-label',letter);
      button.onclick=()=>{if(input.value.length<64)input.setRangeText(letter,input.selectionStart,input.selectionEnd,'end');input.focus();};row.append(button);
    }
    keys.append(row);
  }
  document.getElementById('child-lock-backspace').onclick=()=>{const start=input.selectionStart,end=input.selectionEnd;input.setRangeText('',start===end?Math.max(0,start-1):start,end,'end');input.focus();};
  document.getElementById('child-lock-eye').onclick=event=>{input.type=input.type==='password'?'text':'password';event.currentTarget.setAttribute('aria-pressed',String(input.type==='text'));input.focus();};
  document.getElementById('child-wake').onclick=wake;
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)status();});
  setInterval(()=>{if(!locked&&config.enabled&&performance.now()-lastActivity>=Math.max(0,config.idle_seconds*1000-1500))lock();},500);
  setInterval(status,10000);
  cover();status();
})();
