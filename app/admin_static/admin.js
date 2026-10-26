(() => {
  'use strict';
  const $=id=>document.getElementById(id),message=$('message');
  async function request(path,body,method='POST') {
    const response=await fetch('/api/'+path,{method:body?method:'GET',headers:{'Content-Type':'application/json','X-Little-Pages':'1'},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(10000)});
    const data=await response.json();if(!response.ok)throw new Error(data.error);return data;
  }
  function show(config){$('access').hidden=true;$('settings').hidden=false;$('enabled').checked=config.enabled;const minutes=config.idle_seconds/60;if(![...$('minutes').options].some(o=>Number(o.value)===minutes))$('minutes').add(new Option(minutes+' minutes',String(minutes)));$('minutes').value=String(minutes);$('password').value='';$('password-hint').textContent=config.password_set?'Leave blank to keep the current password.':'Choose a password before enabling the screen lock.';}
  $('access-form').onsubmit=async event=>{event.preventDefault();try{await request('session',{token:$('parent-key').value});$('parent-key').value='';show(await request('config'));message.textContent='';}catch(error){message.textContent=error.message;}};
  $('settings-form').onsubmit=async event=>{event.preventDefault();$('save').disabled=true;try{show(await request('config',{enabled:$('enabled').checked,idle_minutes:Number($('minutes').value),password:$('password').value},'PUT'));message.textContent='Saved. The child screen will pick up these settings shortly.';}catch(error){message.textContent=error.message;}finally{$('save').disabled=false;}};
  (async()=>{
    const token=new URLSearchParams(location.hash.slice(1)).get('key');
    if(token)history.replaceState(null,'',location.pathname);
    try{if(token)await request('session',{token});show(await request('config'));}
    catch(error){$('access').hidden=false;message.textContent=token?error.message:'';}
  })();
})();
