/* Original SVG garden art and four independent ranks on each mouse path. */
(() => {
 'use strict';
 const paths={forward:'M32 51V13m-14 15 14-15 14 15',left:'M47 50V30Q47 17 32 17H12m12-12L12 17l12 12',right:'M17 50V30Q17 17 32 17h20M40 5l12 12-12 12',
 pick:'M17 30c-9-12-1-20 5-9-2-17 9-18 10-2 5-15 14-9 9 4 12-5 16 5 5 12L35 50c-10 7-19 0-22-8-3-7-2-12 4-12Z',
 open:'M19 54V10h30v44M26 54V17l16-7v44m-9-20h2',run:'m23 10 31 22-31 22Z',pause:'M23 13v38m18-38v38',step:'m12 13 26 19-26 19Zm36 0v38',reset:'M15 22a23 23 0 1 1-3 23M15 8v16H2',
 home:'m8 29 24-21 24 21M16 26v28h32V26M27 54V38h10v16',sound:'M8 24h12l13-13v42L20 40H8Zm35-5q16 13 0 26m7-33q25 20 0 40',help:'M23 22a11 11 0 1 1 17 9q-8 3-8 13m0 7v2',
 tick:'m12 33 13 13 27-29',cross:'m17 17 30 30m0-30L17 47',plus:'M32 13v38M13 32h38',clear:'M13 17h38M24 17V9h16v8M19 17l3 37h20l3-37M28 26v19m9-19v19',
 cheese:'m10 46 7-29 36 14v20L10 46Zm7-29 25-8 11 22M31 32v1m10 9v1m-20-4v1',key:'M28 23a11 11 0 1 1-22 0 11 11 0 0 1 22 0Zm-1 0h29m-8 0v10m-10-10v7',
 path:'M15 54V13h34v41M26 42V23m-6 7 6-7 6 7',if:'M32 6 58 32 32 58 6 32ZM25 24a8 8 0 1 1 12 7q-5 3-5 8m0 7v1',
 lock:'M20 29V19a12 12 0 0 1 24 0v10M14 29h36v25H14Zm18 9v7',star:'m32 5 8 18 19 2-15 13 4 20-16-10-17 10 4-20L4 25l20-2Z',
 outfit:'m21 10 11 7 11-7 15 12-10 12-5-5v25H21V29l-5 5L6 22Z',gadgets:'M19 22V16a13 13 0 0 1 26 0v6M15 22h34v34H15Zm8 11h18v15H23Z',magic:'m15 52 31-31m-7-13 2-6 2 6 6 2-6 2-2 6-2-6-6-2Zm-23 9 2-6 2 6 6 2-6 2-2 6-2-6-6-2Zm30 27 2-6 2 6 6 2-6 2-2 6-2-6-6-2Z'};
 function icon(name){return `<svg viewBox="0 0 64 64" class="mm-icon" aria-hidden="true"><path d="${paths[name]||paths.if}" fill="${name==='run'?'currentColor':'none'}" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg>`;}
 function avatar(loadout={}) {
  const o=loadout.outfit||0,g=loadout.gadgets||0,m=loadout.magic||0;
  const coat=['#b7ac9b','#79b5a0','#57a18e','#4d7699','#754fb0'][o];
  return `<svg viewBox="0 0 240 250" class="mm-avatar" aria-hidden="true">
   ${m?`<circle cx="120" cy="130" r="${73+m*8}" fill="${['','#ffe9a9','#b8eee5','#ddd2ff','#f8d0f3'][m]}" opacity=".7"/>`:''}
   ${m>=3?'<path d="M87 120 39 223q80-26 159 0l-45-103Z" fill="#6748a6" stroke="#e8c972" stroke-width="3"/><path d="m65 196 8-19 7 19-15-10h16m95 4 6-16 6 16-13-9h14" fill="#ffdc76"/>':''}
   ${g>=3?`<path d="M88 139Q-12 73 21 191l62-18M152 139Q252 73 219 191l-62-18" fill="${g===4?'#e8c571':'#b7d7d5'}" stroke="#6d8a90" stroke-width="5"/><path d="M32 129 76 164m-49-14 43 23m138-44-44 35m49-13-43 22" stroke="#fff7df" stroke-width="5"/>`:''}
   <path d="M162 199q57 12 44-31" fill="none" stroke="${m>=2?'#e8a4ed':'#dcaaa4'}" stroke-width="9" stroke-linecap="round"/>
   ${g>0?`<rect x="${g>=3?67:153}" y="126" width="${g>=3?106:33}" height="67" rx="15" fill="${g===4?'#568f98':'#aa865b'}" stroke="#735c46" stroke-width="4"/>`:''}
   <ellipse cx="94" cy="224" rx="21" ry="11" fill="${m?'#f3c973':'#dbb6ad'}"/><ellipse cx="148" cy="224" rx="21" ry="11" fill="${m?'#f3c973':'#dbb6ad'}"/>
   <path d="M79 134Q58 165 72 213h95q17-52-13-81Z" fill="${coat}" stroke="#706958" stroke-width="3"/>
   ${o>=2?`<path d="M103 141v72m34-72v72" stroke="#f8e7ac" stroke-width="4"/><path d="M76 182h88" stroke="#725a48" stroke-width="8"/><rect x="111" y="176" width="20" height="13" rx="3" fill="#edcc7c"/>`:''}
   <ellipse cx="71" cy="172" rx="13" ry="23" transform="rotate(19 71 172)" fill="#b7ac9b"/><ellipse cx="168" cy="172" rx="13" ry="23" transform="rotate(-19 168 172)" fill="#b7ac9b"/>
   <circle cx="68" cy="67" r="34" fill="#b7ac9b" stroke="#706958" stroke-width="3"/><circle cx="68" cy="67" r="24" fill="#e9bbb0"/>
   <circle cx="171" cy="67" r="34" fill="#b7ac9b" stroke="#706958" stroke-width="3"/><circle cx="171" cy="67" r="24" fill="#e9bbb0"/>
   <path d="M65 100Q61 54 120 53q59 1 56 47l-10 40q-44 48-91-1Z" fill="#bdb2a1" stroke="#706958" stroke-width="3"/>
   <ellipse cx="120" cy="127" rx="36" ry="31" fill="#eee0c7"/><ellipse cx="95" cy="105" rx="6" ry="9" fill="#333d39"/><ellipse cx="145" cy="105" rx="6" ry="9" fill="#333d39"/>
   <circle cx="97" cy="102" r="2" fill="white"/><circle cx="147" cy="102" r="2" fill="white"/><path d="M112 122q8-9 16 0-8 12-16 0" fill="#b97579"/><path d="M120 130v7q-9 8-15-1m15 1q9 8 15-1" fill="none" stroke="#706958" stroke-width="2.5" stroke-linecap="round"/>
   <path d="m85 125-31-4m32 12-31 5m98-13 31-4m-32 12 31 5" stroke="#706958" stroke-width="2" stroke-linecap="round"/>
   ${o>=1?'<path d="M80 145q39 20 79-1l-5 13q-40 20-72-1Z" fill="#e6a260"/><path d="m145 151 18 39-23-5-5-31Z" fill="#e6a260"/>':''}
   ${o===2?'<path d="M69 75q-3-30 50-30 51 0 52 31-56 16-102-1" fill="#d7b673" stroke="#786942" stroke-width="3"/><path d="M90 65q7-34 32-34t28 35" fill="#c7a263"/>':''}
   ${o===3?'<path d="m67 71 8-34 44 11 43-11 11 34-53-9Z" fill="#365c82" stroke="#e4c679" stroke-width="4"/><circle cx="120" cy="48" r="9" fill="#e8cc7b"/>':''}
   ${o===4?'<path d="m78 58-4-34 24 15 21-29 23 29 25-15-5 34Z" fill="#efcb65" stroke="#99753b" stroke-width="3"/><path d="m118 24 6 13-6 13-6-13Z" fill="#ab75ba"/>':''}
   ${g===2?'<rect x="171" y="154" width="28" height="39" rx="6" fill="#fff1a6" stroke="#8b734c" stroke-width="4"/><path d="M176 153v-9h18v9" fill="none" stroke="#8b734c" stroke-width="4"/>':''}
   ${g===4?'<ellipse cx="120" cy="213" rx="75" ry="17" fill="#73aeb5" stroke="#476d7c" stroke-width="4"/><path d="M85 219v12m70-12v12" stroke="#8d7349" stroke-width="6"/><ellipse cx="120" cy="18" rx="61" ry="7" fill="#e8ce89"/><path d="M120 18v17" stroke="#826c52" stroke-width="4"/>':''}
   ${m?'<path d="m39 97 4-11 4 11 11 4-11 4-4 11-4-11-11-4Zm143 117 4-11 4 11 11 4-11 4-4 11-4-11-11-4Z" fill="#efbc58"/>':''}
   ${m===4?'<path d="M31 75q-24 60 4 115M208 75q24 60-4 115" fill="none" stroke="#f3c966" stroke-width="6" stroke-dasharray="3 15"/><circle cx="120" cy="30" r="9" fill="#fff7c5" stroke="#dfb251" stroke-width="3"/>':''}
  </svg>`;
 }
 function boardMouse(loadout={}){return `<g><path d="M-13 4q-23 21-26 3" fill="none" stroke="${loadout.magic>=2?'#c8a1ef':'#dca69e'}" stroke-width="5" stroke-linecap="round"/><ellipse cx="-3" cy="0" rx="21" ry="15" fill="${loadout.outfit?'#70a994':'#bcb09b'}" stroke="#766b58" stroke-width="2"/><circle cx="11" cy="-12" r="9" fill="#cdb69f" stroke="#766b58" stroke-width="2"/><circle cx="11" cy="-12" r="5" fill="#e8b4ac"/><circle cx="11" cy="12" r="9" fill="#cdb69f" stroke="#766b58" stroke-width="2"/><circle cx="11" cy="12" r="5" fill="#e8b4ac"/><path d="M5-11q15-4 25 11-10 15-25 11" fill="#c9baa2"/><circle cx="29" cy="0" r="3" fill="#b37578"/><circle cx="16" cy="-6" r="2.5" fill="#303c36"/><circle cx="16" cy="6" r="2.5" fill="#303c36"/>${loadout.gadgets?'<rect x="-17" y="-10" width="14" height="20" rx="5" fill="#d4ac6a" stroke="#806442" stroke-width="2"/>':''}${loadout.magic?'<path d="m-28-20 3-7 3 7 7 3-7 3-3 7-3-7-7-3Z" fill="#edba55"/>':''}</g>`;}
 window.MouseVisuals={icon,avatar,boardMouse};
})();
