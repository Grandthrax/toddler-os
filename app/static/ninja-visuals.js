/* Compose independently illustrated transparent equipment over a masked body. */
(() => {
  let serial=0;
  const drawings={
    sword:'<path d="m48 7 8 2 1 9-27 29-10-10Z" fill="#efb34e"/><path d="m48 7-2 14-22 22-4-6Z" fill="#fff0b9"/><path d="m14 34 17 17M12 53l10-10" stroke="#8e3d3d" stroke-width="6" stroke-linecap="round"/><circle cx="11" cy="54" r="4" fill="#d5a04b"/>',
    armour:'<path d="m20 8 12 6 12-6 14 13-10 9-5-4 3 29H18l3-29-5 4-10-9Z" fill="#b54a43" stroke="#d4a04d" stroke-width="4"/><path d="m35 20-12 17h9l-3 13 14-20H32Z" fill="#ffdc83"/>',
    power:'<path d="M30 48C15 47 6 30 4 10c12 5 22 10 28 22C38 20 48 15 60 10c-2 20-11 37-26 38" fill="#f6d178" stroke="#c79545" stroke-width="3"/><path d="M10 20 26 38M54 20 38 38M14 31l11 13m25-13L39 44" stroke="#fff3c0" stroke-width="3"/><path d="m34 20-12 19h9l-3 14 14-21h-9Z" fill="#aa4144"/>',
    gate:'<path d="M9 13h46M5 7h54M14 13v44m36-44v44M19 24h26v30H19Z" fill="none" stroke="#a44d43" stroke-width="5" stroke-linejoin="round"/><path d="M32 25v27" stroke="#d5a653" stroke-width="3"/>',
    crystals:'<path d="m20 8 12 10v24L20 55 8 42V18Zm27 6 10 8v20L47 53 37 42V22Z" fill="#e7b45e" stroke="#b87c35" stroke-width="3"/><path d="m20 8 4 24-4 23m27-41 3 20-3 19" fill="none" stroke="#fff1bc" stroke-width="4"/>',
    bridge:'<path d="M7 49h50M10 49V23m44 26V23M12 26q20 19 40 0M18 34v14m9-9v9m10-9v9m9-14v14" fill="none" stroke="#a85444" stroke-width="4" stroke-linecap="round"/><path d="M5 22h13m28 0h13" stroke="#d4a14c" stroke-width="5"/>',
    missing:'<rect x="8" y="13" width="20" height="37" rx="6" fill="#e6b45c"/><rect x="35" y="13" width="20" height="37" rx="6" fill="none" stroke="#bd9859" stroke-width="3" stroke-dasharray="5 4"/><path d="M42 25q0-8 7-4t-3 10v4" fill="none" stroke="#a44c42" stroke-width="4"/><circle cx="46" cy="41" r="2" fill="#a44c42"/>',
    trophy:'<path d="M18 8h28v18q0 15-14 18-14-3-14-18ZM18 15H8q-1 20 14 21m24-21h10q1 20-14 21M32 43v10m-12 4h24" fill="#e7b65a" stroke="#b07a38" stroke-width="4"/><path d="m32 16 3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1Z" fill="#fff2b7"/>',
    lock:'<rect x="14" y="28" width="36" height="28" rx="6" fill="#b9b0a0"/><path d="M22 29V19a10 10 0 0 1 20 0v10" fill="none" stroke="#a69d8b" stroke-width="6"/><circle cx="32" cy="40" r="4" fill="#f7f0df"/>',
    hand:'<path d="M16 37V22q0-7 6-5v17-21q0-8 7-4v25-24q0-7 7-3v27-19q0-6 7-2v25l3-8q5-8 10-1L45 51q-5 8-18 6T13 46l-6-9q-3-8 4-8Z" fill="#f6d59b" stroke="#ad7947" stroke-width="3" stroke-linejoin="round"/>',
    play:'<path d="m22 12 30 20-30 20Z" fill="#a64643"/>',
    check:'<path d="m12 32 13 13 28-29" fill="none" stroke="#a44b41" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>',
    plus:'<path d="M32 12v40M12 32h40" stroke="#a14c42" stroke-width="7" stroke-linecap="round"/>',
    minus:'<path d="M12 32h40" stroke="#a14c42" stroke-width="7" stroke-linecap="round"/>',
    equal:'<path d="M12 23h40M12 41h40" stroke="#a14c42" stroke-width="6" stroke-linecap="round"/>',
    arrow:'<path d="M9 32h44M37 16l16 16-16 16" fill="none" stroke="#a14c42" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>',
    shirt:'<path d="m20 10 12 6 12-6 14 15-11 9-6-5v26H23V29l-6 5-11-9Z" fill="#b54a43" stroke="#d4a04d" stroke-width="3"/>'
  };
  const icon=(name,cls='')=>`<svg class="ninja-picture-icon ${cls}" viewBox="0 0 64 64" aria-hidden="true">${drawings[name]||drawings.crystals}</svg>`;
  // Equipment uses separate transparent layers; the covered face is part of every body.
  function avatar(loadout={},className='',label='Your ninja') {
    const rank=value=>Math.max(0,Math.min(4,Math.trunc(Number(value)||0)));
    const sword=rank(loadout.sword),armour=rank(loadout.armour),power=rank(loadout.power);
    const id='ninja-art-'+serial++;
    const image=(file,layer,transform='')=>`<image data-layer="${layer}" href="/ninja/gear-v2/${file}.png" width="1024" height="1536"${transform?` transform="${transform}"`:''}/>`;
    const grips={1:[300,830],2:[300,830],3:[300,830],4:[300,830]};
    const [gx,gy]=grips[armour]||[300,830];
    let weapon='';
    if(sword===1) weapon=image('sword-1','sword',`translate(${gx} ${gy}) rotate(-3) scale(.46) translate(-680 -330)`);
    if(sword===2) weapon=image('sword-2','sword',`translate(${gx} ${gy}) rotate(-7) scale(.44) translate(-850 -190)`);
    if(sword===4) weapon=image('sword-4','sword',`translate(${gx} ${gy}) rotate(-4) scale(.48) translate(-830 -240)`);
    if(sword===3) weapon=`<defs><clipPath id="${id}-left"><rect width="535" height="1536"/></clipPath><clipPath id="${id}-right"><rect x="535" width="489" height="1536"/></clipPath></defs><g transform="translate(${gx} ${gy}) rotate(-5) scale(.51) translate(-411 -390)"><g clip-path="url(#${id}-left)">${image('sword-3','sword')}</g></g><g transform="translate(735 680) rotate(-3) scale(.55) translate(-620 -250)"><g clip-path="url(#${id}-right)">${image('sword-3','sword')}</g></g>`;
    const rear=power?image('power-'+power,'power',power===1?'translate(65 305) scale(.88)':power===3?'translate(30 -80) scale(.94)':''):'';
    return `<svg class="ninja-character ${className}" viewBox="-120 -40 1264 1616" role="img" aria-label="${label}" data-sword="${sword}" data-armour="${armour}" data-power="${power}">${rear}${weapon}${image('body-'+armour,'body')}</svg>`;
  }
  window.NinjaVisuals={icon,avatar};
})();
