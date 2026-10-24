/* Optional Playwright integration check. Always starts with disposable data. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const os=require('node:os'),net=require('node:net'),{spawn,spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),qa=process.env.LITTLE_PAGES_QA_DIR||fs.mkdtempSync(path.join(os.tmpdir(),'toddler-books-'));
fs.mkdirSync(qa,{recursive:true});
const data=fs.mkdtempSync(path.join(qa,'data-')),log=fs.openSync(path.join(qa,'server.log'),'w');
let server,browser,page;
const availablePort=()=>new Promise(resolve=>{const socket=net.createServer();socket.listen(0,'127.0.0.1',()=>{const port=socket.address().port;socket.close(()=>resolve(port));});});
(async()=>{try{
  const port=await availablePort(),origin='http://127.0.0.1:'+port;
  server=spawn(process.env.LITTLE_PAGES_PYTHON||'python',['-B',path.join(root,'app/server.py'),'--port',String(port),'--data-dir',data],{stdio:['ignore',log,log],windowsHide:true});
  let ready=false;for(let i=0;i<100;i++){try{if((await fetch(origin+'/health')).ok){ready=true;break;}}catch{}await new Promise(resolve=>setTimeout(resolve,100));}assert.ok(ready,'Server did not start');
  const options={headless:true,args:['--mute-audio']};if(process.env.CHROME_PATH)options.executablePath=process.env.CHROME_PATH;
  browser=await chromium.launch(options);page=await browser.newPage({viewport:{width:1280,height:800}});
  const errors=[],missing=[],external=[],audio=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)missing.push(r.url());});
  page.on('request',r=>{if(r.url().includes('/audio/'))audio.push(r.url());});
  await page.route('**/*',route=>{const u=new URL(route.request().url());if(!['127.0.0.1','localhost'].includes(u.hostname)&&u.protocol!=='blob:'){external.push(u.origin);return route.abort();}return route.continue();});
  const api=async route=>await(await fetch(origin+'/api/storybooks'+route)).json();
  const savedBook=async template=>{const library=await api('');const books=await Promise.all(library.books.map(b=>api('/'+b.id)));return books.find(b=>b.template===template);};
  const home=async()=>{await page.locator('[data-action=home]').click();await page.locator('.sb-template-grid').first().waitFor();};
  const start=async template=>{await page.locator('[data-template="'+template+'"]').click();await page.locator('.sb-page-head').waitFor();};
  const next=async()=>{
    const before=(await page.locator('.sb-page-count').innerText()).split('/')[0].trim();
    await page.locator('[data-action=continue-story]').click();
    await page.waitForFunction(previous=>document.querySelector('.sb-page-count')?.textContent.split('/')[0].trim()!==previous,before);
  };
  const type=async(word,image)=>{
    await page.locator('[data-option="'+word+'"]').waitFor();await page.locator('#sb-writing').fill(word);await page.locator('#sb-writing').press('Enter');
    await page.locator('[data-action=continue-story]').waitFor();assert.ok((await page.locator('.sb-illustration img').getAttribute('src')).endsWith(image));
    assert.equal(await page.locator('#sb-writing').count(),0);
  };
  const shot=async name=>{await page.locator('.sb-stage img').evaluateAll(images=>Promise.all(images.map(i=>i.decode())));await page.screenshot({path:path.join(qa,name+'.png'),fullPage:true});};
  await page.goto(origin+'/?desktop-preview=1');await page.locator('#desktop-storybooks').dblclick();await page.locator('.sb-new-book').first().waitFor();
  assert.equal(await page.locator('.sb-new-book').count(),6);await shot('bookshelf');
  await start('come-back-cat-make');await next();
  await page.locator('#sb-writing').fill('dog');assert.equal(await page.locator('[data-action=next]').isDisabled(),true);
  await shot('cat-choices');await type('sit','come-02.jpg');
  await page.locator('.sb-credits summary').click();await page.getByText('Nicola Rijsdijk — writer',{exact:false}).waitFor();
  assert.equal(await page.locator('.sb-credits img').isVisible(),true);assert.ok((await page.locator('.sb-credits').innerText()).includes('CC BY 4.0'));
  await next();await type('snail','come-07.jpg');await next();await type('nap','come-12.jpg');await next();
  assert.equal((await savedBook('come-back-cat-make')).completed,true);await shot('cat-finished');
  await home();await start('wheres-that-cat-make');await next();await type('car','where-page15.jpg');
  await next();await type('bug','where-page7.jpg');await next();await type('sit','where-page7.jpg');await next();
  assert.equal((await savedBook('wheres-that-cat-make')).completed,true);
  await home();await start('come-back-cat-read');await next();
  assert.equal(await page.locator('.sb-read-text').innerText(),'Come back, cat! Play with me.');
  await next();await next();
  const contraction=page.locator('[data-read-word="that’s"]');assert.equal(await contraction.count(),1);
  const spoken=page.waitForRequest(r=>r.url().endsWith('/word-thats.wav'));await contraction.click();await spoken;
  assert.equal(await page.locator('.sb-illustration img').evaluate(el=>getComputedStyle(el).objectFit),'contain');await shot('original-reader');
  await home();const before=audio.length;await start('wheres-that-cat-look');
  assert.equal(await page.locator('.sb-read-text,[data-action=read-page]').count(),0);await shot('wordless');
  for(let i=0;i<12;i++)await next();
  await page.waitForFunction(async()=>{const library=await(await fetch('/api/storybooks')).json();return library.books.some(b=>b.title==='Where’s That Cat?'&&b.completed);});
  assert.equal((await savedBook('wheres-that-cat-look')).completed,true);
  assert.equal(audio.slice(before).some(url=>url.includes('/page-bd-where-look')||url.includes('/page-bd-where-cover')),false);
  for(const width of [390,320]){await page.setViewportSize({width,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await shot('wordless-'+width);}
  await page.reload();await page.locator('#desktop-storybooks').dblclick();
  assert.equal((await api('')).books.length,4);assert.equal((await savedBook('wheres-that-cat-make')).completed,true);
  assert.deepEqual(errors,[]);assert.deepEqual(missing,[]);assert.deepEqual(external,[]);
  const result={status:'passed',checks:['six editions','both typed adaptations completed','wrong word cannot continue','creators, logo and licence visible','original text and contracted word playback','wordless original has no invented text or story audio','saved progress survives reload','complete artwork fitted without cropping','mobile widths 390 and 320','no external requests or browser errors'],qa};
  fs.writeFileSync(path.join(qa,'result.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}finally{
  if(browser)await browser.close();
  if(server?.pid){if(process.platform==='win32')spawnSync('taskkill',['/PID',String(server.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});else server.kill();}
  fs.closeSync(log);
}})().catch(error=>{console.error(error);process.exitCode=1;});
