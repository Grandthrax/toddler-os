/* Read-only parent art review. Uses the same layered renderer as the game. */
(async()=>{
  const state=await(await fetch('/api/ninja')).json(),branches=['sword','armour','power'];
  const labels={sword:'Swords',armour:'Armour',power:'Powers'},outfit={sword:4,armour:4,power:4};
  const draw=()=>document.querySelector('#combined').innerHTML=NinjaVisuals.avatar(outfit,'','Combined ninja equipment preview');
  for(const branch of branches){
    const label=document.createElement('label');label.textContent=labels[branch];
    const select=document.createElement('select');select.id='preview-'+branch;select.setAttribute('aria-label',labels[branch]);
    for(let rank=0;rank<=4;rank++){const item=state.catalog.find(item=>item.branch===branch&&item.rank===rank);select.add(new Option(rank?rank+' · '+item.name:'0 · Training',String(rank)));}
    select.value='4';select.onchange=()=>{outfit[branch]=Number(select.value);draw();};label.append(select);document.querySelector('#pickers').append(label);
    const section=document.createElement('section');section.className='path';
    section.innerHTML=`<div class="path-heading">${NinjaVisuals.icon(branch)}<h2>${labels[branch]}</h2></div><div class="cards">${state.catalog.filter(item=>item.branch===branch).map(item=>`<article class="card" data-branch="${branch}" data-rank="${item.rank}"><div class="picture">${NinjaVisuals.avatar({[branch]:item.rank},'',item.name)}</div><div class="caption"><small>STEP ${item.rank} OF 4</small><strong>${item.name}</strong><span class="dots" aria-hidden="true">${'●'.repeat(item.rank)}${'○'.repeat(4-item.rank)}</span></div></article>`).join('')}</div>`;
    document.querySelector('#paths').append(section);
  }
  draw();
})();
