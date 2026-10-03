const {before, after, test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const {execFileSync} = require('node:child_process');
const {chromium} = require('playwright');
let browser, server, origin, root, release, connected, config;
let prime = false, blocked = '', requests = [];
const types = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml'};
before(async () => {
  root = fs.mkdtempSync(path.join(os.tmpdir(), 'prawo-browser-'));
  release = path.join(root, 'static'); connected = path.join(root, 'connected');
  for (const [output, api] of [[release,''],[connected,'https://api.example.org']]) execFileSync('python3', ['-m','scripts.build_pages','--output',output,'--api-base-url',api]);
  config = JSON.parse(fs.readFileSync(path.join(release,'pages-data.json')));
  server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    const name = url.pathname.endsWith('/') ? 'index.html' : path.basename(url.pathname);
    requests.push(name);
    res.setHeader('Cache-Control', name === 'index.html' ? 'no-store' : 'public, max-age=3600');
    res.setHeader('Content-Type', types[path.extname(name)] || 'text/plain');
    if (prime) {
      const legacy = {'index.html':'<!doctype html><link rel="stylesheet" href="./style.css"><script src="./app.js" defer></script><h1>Earlier release</h1>', 'style.css':'.metric-grid{display:block}', 'app.js':'window.legacyLoaded=true;'};
      if (legacy[name]) return res.end(legacy[name]);
    }
    const folder = url.pathname.startsWith('/connected/') ? connected : release;
    if (blocked && name.startsWith(blocked + '.') || !fs.existsSync(path.join(folder, name))) { res.writeHead(404); return res.end('Unavailable test resource'); }
    res.end(fs.readFileSync(path.join(folder, name)));
  });
  await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
  origin = `http://127.0.0.1:${server.address().port}`;
  browser = await chromium.launch({headless:true, args:['--no-sandbox'], ...(process.env.PRAWO_TEST_BROWSER ? {executablePath:process.env.PRAWO_TEST_BROWSER} : {})});
});
after(async () => { if (browser) await browser.close(); if (server) { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); } if (root) fs.rmSync(root,{recursive:true,force:true}); });
const waitForText = (page, selector, text) => page.waitForFunction(({selector,text}) => document.querySelector(selector)?.textContent.includes(text), {selector,text});
const ready = page => page.waitForFunction(() => document.documentElement.dataset.appReady === 'true');

test('returning visitor loads a complete release despite cached unversioned scripts and CSS', async () => {
  const page = await browser.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});
  try {
    // No request interception: exercise the browser's real HTTP cache.
    prime = true; requests = [];
    await page.goto(origin + '/prawo-otwarte/');
    assert.equal(await page.evaluate(() => window.legacyLoaded), true);
    prime = false; requests = [];
    await page.goto(origin + '/prawo-otwarte/?update=1'); await ready(page);
    await waitForText(page,'#service-label','Tryb bez modelu');
    assert.equal(await page.locator('#benchmark-case option').count(),8);
    assert.equal(await page.locator('.metric-grid').evaluate(node => getComputedStyle(node).display),'grid');
    assert.equal(await page.locator('.hero-dossier').evaluate(node => getComputedStyle(node).display),'grid');
    assert.equal(await page.locator('#startup-problem').isHidden(),true);
    assert.ok(!requests.includes('app.js') && !requests.includes('style.css'));
    assert.ok(requests.some(name => /^pages-data\.[a-f0-9]{16}\.json$/.test(name)));
    assert.equal(await page.locator('#run-benchmark').isDisabled(),true);
    assert.ok((await page.locator('#lab-connection-status').textContent()).includes('bez modelu'));
    for (const width of [320,390,768,1440]) {
      await page.setViewportSize({width,height:900});
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth),false,`Overflow at ${width}`);
    }
    await page.locator('#open-example').click();
    await page.locator('#domain').selectOption('work');
    await page.locator('#intake-form button[type=submit]').click(); await waitForText(page,'#intake-feedback','Notatka gotowa');
    assert.equal(await page.locator('#metric-completed').textContent(),'0 / 0');
  } finally { prime = false; await page.close(); }
});

test('missing application or stylesheet shows an actionable startup message', async () => {
  for (const resource of ['app','style']) {
    const page = await browser.newPage();
    try {
      blocked = resource; await page.goto(origin + '/prawo-otwarte/');
      assert.equal(await page.locator('#startup-problem').isVisible(),true);
      assert.equal(await page.locator('#reload-application').isVisible(),true);
      if (resource === 'app') assert.equal(await page.locator('#intake-form button[type=submit]').isDisabled(),true);
      blocked = ''; await page.locator('#reload-application').click(); await ready(page);
      assert.equal(await page.locator('#startup-problem').isHidden(),true);
      assert.equal(await page.locator('#benchmark-case option').count(),8);
    } finally { blocked = ''; await page.close(); }
  }
});

test('connected laboratory handles recovery, abstention, confirmation, ratings and private exports', async () => {
  const page = await browser.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});
  const errors=[]; page.on('pageerror', error => errors.push(error.message));
  let statusFails = true, method = 'basal', calls = 0;
  await page.route('https://api.example.org/api/**', async route => {
    const endpoint = new URL(route.request().url()).pathname;
    const headers = {'Access-Control-Allow-Origin':origin, 'Access-Control-Allow-Methods':'GET, POST','Access-Control-Allow-Headers':'Content-Type'};
    if (route.request().method() === 'OPTIONS') return route.fulfill({status:204,headers});
    if (endpoint === '/api/status') return route.fulfill({status:statusFails ? 503 : 200,headers,json:statusFails ? {error:'Synthetic outage'} : {domains:Object.fromEntries(Object.entries(config.domains).map(([k,v])=>[k,v.label])),sources:config.sources,corpus:{metadata_count:3,text_count:2,last_import:null},basal:{enabled:true},eli_enabled:true}});
    calls++;
    if (method === 'error') return route.fulfill({status:503,headers,json:{error:'Synthetic API outage'}});
    const body = route.request().postDataJSON();
    const actualMethod = body.domain === 'unknown' ? method : 'user';
    const domain = actualMethod === 'basal_abstained' ? 'unknown' : 'work';
    return route.fulfill({headers,json:{kind:'intake_only',legal_answer:null,domain_label:config.domains[domain].label,questions:config.domains[domain].questions,suggested_query:config.domains[domain].query,event_date:'',routing:{method:actualMethod,domain,reason:'Synthetic test'},note:'Not a legal opinion.'}});
  });
  try {
    await page.goto(origin + '/connected/'); await ready(page); await waitForText(page,'#service-label','Nie udało');
    await page.locator('#intake-tab').click(); const secret='SYNTHETIC_PRIVATE_CASE_523: pytanie o umowę o pracę.'; await page.locator('#description').fill(secret);
    statusFails = false; await page.locator('#lab-refresh').click(); await waitForText(page,'#service-label','Połączono');
    assert.equal(await page.locator('#description').inputValue(),secret);
    await page.locator('#lab-refresh').click(); await waitForText(page,'#service-label','Połączono'); assert.equal(await page.locator('#domain option').count(),9);
    await page.locator('#intake-form button[type=submit]').click(); await waitForText(page,'#intake-feedback','Notatka gotowa');
    await page.getByRole('button',{name:'Potwierdź dziedzinę',exact:true}).click(); assert.equal(calls,1);
    await page.locator('.rating-controls button').filter({hasText:/^Tak$/}).click(); assert.equal(await page.locator('#metric-rating').textContent(),'1 / 1');
    await page.locator('.rating-controls button').filter({hasText:/Nie oceniam/}).click(); assert.equal(await page.locator('#metric-rating').textContent(),'—');
    method='basal_abstained'; await page.locator('#run-benchmark').click(); await waitForText(page,'#benchmark-feedback','Brak rozstrzygnięcia'); assert.equal(await page.locator('#benchmark-score').textContent(),'0 / 1');
    method='error'; await page.locator('#run-benchmark').click(); await waitForText(page,'#benchmark-feedback','Synthetic API outage'); assert.equal(await page.locator('#benchmark-score').textContent(),'0 / 1');
    const [download] = await Promise.all([page.waitForEvent('download'), page.locator('#download-metrics').click()]);
    const exported = fs.readFileSync(await download.path(),'utf8'); assert.ok(!exported.includes(secret)); assert.equal(JSON.parse(exported).summary.attempts,3);
    assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length),0); assert.deepEqual(errors,[]);
  } finally { await page.close(); }
});

test('answers show evidence, remain compatible with older API and export only anonymous metrics', async () => {
  const page = await browser.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});
  let enabled=false, mode='draft', answerCalls=0;
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const source={id:'S1',eli:'DU/2026/1',label:'Art. 1.',title:'Syntetyczny akt testowy',text:'Syntetyczny fragment do testu interfejsu, nie jest prawdziwym przepisem.',source_url:'https://eli.gov.pl/eli/DU/2026/1/ogl',text_fetched_at:'2026-10-03',text_sha256:'a'.repeat(64),legal_status_date:'2026-01-01'};
  await page.route('https://api.example.org/api/**',async route=>{
    const headers={'Access-Control-Allow-Origin':origin,'Access-Control-Allow-Methods':'GET, POST','Access-Control-Allow-Headers':'Content-Type'};
    if(route.request().method()==='OPTIONS')return route.fulfill({status:204,headers});
    if(route.request().url().endsWith('/status'))return route.fulfill({headers,json:{domains:Object.fromEntries(Object.entries(config.domains).map(([k,v])=>[k,v.label])),sources:config.sources,corpus:{metadata_count:15,text_count:15,last_import:null},basal:{enabled:true},eli_enabled:true,source_answers:enabled,generative_answers:enabled,core_sources:[{eli:'DU/2026/1',name:'Syntetyczny akt',state:'text',text_fetched_at:'2026-10-03'}]}});
    answerCalls++;
    if(mode==='error')return route.fulfill({status:503,headers,json:{error:'Synthetic outage'}});
    return route.fulfill({headers,json:{kind:'source_answer',mode,sources:mode==='no_sources'?[]:[source],claims:mode==='draft'?[{source_id:'S1',quote:source.text,explanation:'<script>window.UNSAFE=true</script> Testowe objaśnienie.'}]:[],message:'Syntetyczna odpowiedź testowa.',limitation:'Wersja prawa wymaga sprawdzenia.',generation:{status:'completed',elapsed_ms:120},evidence_check:{verdict:'supported'}}});
  });
  try {
    await page.goto(origin+'/connected/');await ready(page);await waitForText(page,'#service-label','Połączono');
    await page.locator('#answer-tab').click();assert.equal(await page.locator('#answer-submit').isDisabled(),true);
    enabled=true;await page.locator('#refresh-status').click();await waitForText(page,'#answer-capability','generowanie');
    const secret='SYNTHETIC_PRIVATE_ANSWER_874: konkretne pytanie o przepis';
    await page.locator('#answer-question').fill(secret);await page.locator('#answer-submit').click();await waitForText(page,'#answer-feedback','Gotowe');
    assert.equal(answerCalls,1);assert.equal(await page.locator('.answer-claim').count(),1);
    assert.equal(await page.evaluate(()=>window.UNSAFE),undefined);
    assert.equal(await page.locator('#evidence-S1').count(),1);
    for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:900});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Answer overflow '+width);}
    if(process.env.PRAWO_TEST_SCREENSHOT) {await page.setViewportSize({width:390,height:844});await page.locator('#answer-panel').screenshot({path:process.env.PRAWO_TEST_SCREENSHOT});}
    const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#download-answer-metrics').click()]);
    const exported=fs.readFileSync(await download.path(),'utf8');assert.ok(!exported.includes(secret));assert.ok(!exported.includes(source.text));assert.equal(JSON.parse(exported).rows.length,1);
    mode='no_sources';await page.locator('#answer-submit').click();await waitForText(page,'#answer-feedback','Gotowe');assert.equal(await page.locator('.evidence-source').count(),0);
    mode='error';await page.locator('#answer-submit').click();await waitForText(page,'#answer-feedback','Synthetic outage');assert.equal(await page.locator('#answer-question').inputValue(),secret);
    assert.deepEqual(errors,[]);assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
  }finally{await page.close();}
});
