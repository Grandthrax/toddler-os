/* One remembered volume control for every sound in the learning desktop. */
(() => {
  'use strict';
  const key='little-pages-audio',sounds=new Set();
  let volume=100,muted=false,lastNonzero=100,suspended=false;
  try {
    const saved=JSON.parse(localStorage.getItem(key)||'null');
    if(saved&&Number.isInteger(saved.volume)&&saved.volume>=0&&saved.volume<=100&&typeof saved.muted==='boolean') {
      volume=saved.volume;muted=saved.muted;if(volume)lastNonzero=volume;
    }
  } catch {}
  const button=document.getElementById('desktop-volume');
  const panel=document.getElementById('volume-panel');
  const slider=document.getElementById('volume-slider');
  const muteButton=document.getElementById('volume-mute');
  const silent=()=>muted||volume===0;
  function apply(save=false) {
    for(const reference of sounds){const sound=reference.deref();if(sound){sound.volume=silent()?0:volume/100;sound.muted=suspended;}else sounds.delete(reference);}
    slider.value=String(volume);slider.setAttribute('aria-valuetext',`${volume} percent${muted?', muted':''}`);
    document.getElementById('volume-percent').textContent=volume+'%';
    button.setAttribute('aria-label',`Speaker volume, ${silent()?'muted':volume+' percent'}`);
    button.querySelector('use').setAttribute('href',silent()?'#icon-volume-muted':'#icon-sound');
    muteButton.setAttribute('aria-pressed',String(silent()));
    muteButton.setAttribute('aria-label',silent()?'Turn sound on':'Mute sound');
    muteButton.querySelector('use').setAttribute('href',silent()?'#icon-volume-muted':'#icon-sound');
    if(save)try{localStorage.setItem(key,JSON.stringify({volume,muted}));}catch{}
  }
  function close(restoreFocus=false){panel.hidden=true;button.setAttribute('aria-expanded','false');if(restoreFocus)button.focus();}
  button.addEventListener('click',()=>{const opening=panel.hidden;panel.hidden=!opening;button.setAttribute('aria-expanded',String(opening));if(opening)slider.focus();});
  document.getElementById('volume-close').addEventListener('click',()=>close(true));
  document.addEventListener('pointerdown',event=>{if(!panel.hidden&&!panel.contains(event.target)&&!button.contains(event.target))close();});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!panel.hidden){event.preventDefault();close(true);}});
  slider.addEventListener('input',()=>{volume=Math.max(0,Math.min(100,Number(slider.value)));if(volume){muted=false;lastNonzero=volume;}apply(true);});
  muteButton.addEventListener('click',()=>{if(volume===0){volume=lastNonzero;muted=false;}else muted=!muted;apply(true);});
  window.addEventListener('storage',event=>{
    if(event.key!==key)return;
    try{const saved=JSON.parse(event.newValue);if(saved&&Number.isInteger(saved.volume)&&saved.volume>=0&&saved.volume<=100&&typeof saved.muted==='boolean'){volume=saved.volume;muted=saved.muted;apply();}}catch{}
  });
  window.LearningAudio={
    create:source=>{const sound=new Audio(source);sound.volume=silent()?0:volume/100;sound.muted=suspended;sounds.add(new WeakRef(sound));return sound;},
    state:()=>({volume,muted}),
    suspend:()=>{suspended=true;for(const reference of sounds){const sound=reference.deref();if(sound){sound.pause();sound.muted=true;}}},
    resume:()=>{suspended=false;for(const reference of sounds){const sound=reference.deref();if(sound)sound.muted=false;}}
  };
  apply();
})();
