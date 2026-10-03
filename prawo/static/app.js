'use strict';
const $ = (selector) => document.querySelector(selector);
const element = (tag, text, cls) => {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (cls) node.className = cls;
  return node;
};
function externalLink(label, url) {
  const parsed = new URL(url);
  const allowed = ['eli.gov.pl', 'api.sejm.gov.pl', 'www.gov.pl', 'eur-lex.europa.eu', 'orzeczenia.ms.gov.pl', 'prawakonsumenta.uokik.gov.pl'];
  if (parsed.protocol !== 'https:' || !allowed.includes(parsed.hostname)) throw new Error('Niedozwolony adres źródła.');
  const a = element('a', label);
  a.href = parsed.href; a.target = '_blank'; a.rel = 'noopener noreferrer';
  return a;
}
async function request(path, body) {
  if (window.PrawoPages) return window.PrawoPages.request(path, body);
  const options = {signal: AbortSignal.timeout(25000), credentials: 'same-origin'};
  if (body) Object.assign(options, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  let response;
  try { response = await fetch(path, options); }
  catch { throw new Error('Nie udało się połączyć z aplikacją. Sprawdź połączenie i spróbuj ponownie.'); }
  const type = response.headers.get('content-type') || '';
  if (!type.includes('application/json')) throw new Error('Serwer aplikacji jest niedostępny. Sam podgląd strony nie uruchamia wyszukiwarki.');
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Nie udało się wykonać zapytania.');
  return data;
}
function feedback(id, message, error = false) {
  const node = $(id); node.textContent = message; node.classList.toggle('error', error);
}
const tabs = ['search', 'intake', 'saved'];
function setTab(name, focus = false) {
  for (const key of tabs) {
    const active = key === name;
    $(`#${key}-tab`).classList.toggle('active', active);
    $(`#${key}-tab`).setAttribute('aria-selected', String(active));
    $(`#${key}-tab`).tabIndex = active ? 0 : -1;
    $(`#${key}-panel`).hidden = !active;
  }
  if (focus) $(`#${name}-tab`).focus();
}
for (const name of tabs) {
  $(`#${name}-tab`).addEventListener('click', () => setTab(name));
  $(`#${name}-tab`).addEventListener('keydown', (event) => {
    if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
      event.preventDefault();
      const direction = event.key === 'ArrowLeft' ? -1 : 1;
      setTab(event.key === 'Home' ? tabs[0] : event.key === 'End' ? tabs.at(-1) : tabs[(tabs.indexOf(name) + direction + tabs.length) % tabs.length], true);
    }
  });
}
const sourceFallback = [
  {id:'eli-du', name:'Dziennik Ustaw', provider:'ELI · Kancelaria Sejmu', stage:'unknown', url:'https://eli.gov.pl/eli/DU', scope:'Stan podłączenia będzie widoczny po połączeniu z aplikacją.'},
  {id:'eli-mp', name:'Monitor Polski', provider:'ELI · Kancelaria Sejmu', stage:'unknown', url:'https://eli.gov.pl/eli/MP', scope:'Stan podłączenia będzie widoczny po połączeniu z aplikacją.'}
];
function renderSources(sources) {
  const grid = $('#source-grid'); grid.replaceChildren();
  const stages = {connected:'DOSTĘPNE', planned:'W PLANIE', reference:'ODNOŚNIKI', unknown:'NIEZWERYFIKOWANE'};
  for (const [index, source] of sources.entries()) {
    const card = element('article', undefined, 'source-card');
    const top = element('div', undefined, 'source-card-top');
    top.append(element('span', String(index + 1).padStart(2, '0')), element('span', stages[source.stage], `status-badge ${source.stage === 'connected' ? 'connected' : ''}`));
    card.append(top, element('h3', source.name), element('small', source.provider), element('p', source.scope), externalLink('Otwórz źródło ↗', source.url));
    grid.append(card);
  }
}
function dateText(value) { return value ? new Date(value).toLocaleDateString('pl-PL') : 'Jeszcze brak'; }
async function loadStatus() {
  try {
    const status = await request('/api/status');
    if (status.site_mode === 'static') {
      const stats = [['2', 'dzienniki w wyszukiwaniu'], ['Bez konta', 'dostęp do narzędzi'], ['U Ciebie', 'powstaje notatka sprawy']];
      ['metadata-count','text-count','import-date'].forEach((id, index) => {
        const node = $('#' + id); node.textContent = stats[index][0]; node.nextElementSibling.textContent = stats[index][1];
      });
      $('#connection-status').textContent = 'Wyszukiwarka łączy się bezpośrednio z oficjalnym katalogiem Sejmu. Lokalna baza projektu i automatyczna analiza spraw nie są jeszcze podłączone do tej strony.';
      $('input[value="local"]').disabled = true; $('input[value="local"]').closest('label').hidden = true;
      $('#search-panel .panel-intro').textContent = 'Wpisz tytuł lub fragment tytułu aktu. Otrzymasz odnośniki do oficjalnych publikacji.';
      $('#search-tab small').textContent = 'Oficjalne tytuły i publikacje';
      $('#intake-form .micro').textContent = 'Opis i notatka pozostają na Twoim urządzeniu. W tej wersji dziedzinę wybierasz samodzielnie; opis nie trafia do modelu ani na serwer projektu.';
      $('#domain option[value="unknown"]').textContent = 'Wybierz dziedzinę (opcjonalnie)';
      $('#method-privacy-copy').textContent = 'Nie wymagamy konta ani nie zapisujemy opisu sprawy. Notatka powstaje w pamięci przeglądarki. Pobranie jej na urządzenie jest Twoją decyzją.';
      $('#method-model-copy').textContent = 'Projekt rozwijamy w oparciu o BASAL. W tej publicznej wersji samodzielnie wybierasz dziedzinę; podłączenie modelu jest kolejnym etapem. Narzędzie nie rozstrzyga uprawnień ani nie oblicza terminów.';
    } else {
      $('#metadata-count').textContent = status.corpus.metadata_count.toLocaleString('pl-PL');
      $('#text-count').textContent = status.corpus.text_count.toLocaleString('pl-PL');
      $('#import-date').textContent = dateText(status.corpus.last_import);
      $('#connection-status').textContent = 'Dane pochodzą z działającej aplikacji. Pokrycie prawa i poprawność historycznych wersji nie są jeszcze potwierdzone.';
    }
    renderSources(status.sources);
    for (const [key, label] of Object.entries(status.domains)) {
      if (key !== 'unknown') { const option = element('option', label); option.value = key; $('#domain').append(option); }
    }
    if (!status.eli_enabled) {
      $('input[value="eli"]').disabled = true; $('input[value="local"]').checked = true; updateSearchPrivacy();
    }
  } catch (error) {
    $('#connection-status').textContent = error.message;
    renderSources(sourceFallback);
  }
}
function updateSearchPrivacy() {
  const mode = $('input[name="mode"]:checked').value;
  $('#search-filters').hidden = mode !== 'eli';
  $('#publisher').disabled = mode !== 'eli';
  $('#publication-year').disabled = mode !== 'eli';
  $('#search-privacy').textContent = mode === 'eli'
    ? 'Fraza wyszukiwania trafi do API Sejmu. Wpisz temat lub tytuł aktu, bez danych osobowych.'
    : 'Wyszukiwanie obejmuje wyłącznie dokumenty zaimportowane do tej instalacji. Brak wyniku nie oznacza braku odpowiedniego przepisu.';
}
document.querySelectorAll('input[name="mode"]').forEach(node => node.addEventListener('change', updateSearchPrivacy));
document.querySelectorAll('[data-query]').forEach(button => button.addEventListener('click', () => {
  $('#query').value = button.dataset.query; $('#search-form').requestSubmit();
}));
const selectedSources = new Map();
function downloadText(name, text) {
  const url = URL.createObjectURL(new Blob([text], {type:'text/plain;charset=utf-8'}));
  const a = element('a'); a.href = url; a.download = name; document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function renderSelectedSources() {
  $('#saved-count').textContent = String(selectedSources.size);
  $('#download-sources').disabled = !selectedSources.size;
  $('#clear-sources').disabled = !selectedSources.size;
  const list = $('#saved-list'); list.replaceChildren();
  if (!selectedSources.size) list.append(element('p', 'Jeszcze pusto. Wyszukaj akt i wybierz „Dodaj do źródeł”.', 'notice'));
  for (const act of selectedSources.values()) {
    const card = element('article', undefined, 'result-card');
    const actions = element('div', undefined, 'result-actions');
    const remove = element('button', 'Usuń z listy'); remove.type = 'button';
    remove.setAttribute('aria-label', 'Usuń z listy: ' + act.eli);
    remove.addEventListener('click', () => { selectedSources.delete(act.eli); renderSelectedSources(); feedback('#saved-feedback', 'Usunięto źródło ' + act.eli + '.'); });
    actions.append(externalLink('Oficjalna publikacja ↗', act.source_url), remove);
    card.append(element('span', act.eli, 'result-meta'), element('h4', act.title, 'result-title'), actions);
    list.append(card);
  }
  document.querySelectorAll('[data-save-eli]').forEach(button => {
    const saved = selectedSources.has(button.dataset.saveEli);
    button.textContent = saved ? 'Na Twojej liście ✓' : 'Dodaj do źródeł +';
    button.disabled = saved;
  });
}
$('#download-sources').addEventListener('click', () => {
  const body = [...selectedSources.values()].map((act,index) => `${index+1}. ${act.title}\nELI: ${act.eli}\nStatus podany przez źródło: ${act.status}\nOdczytano: ${act.fetched_at}\nOficjalna publikacja: ${act.source_url}`).join('\n\n');
  downloadText('prawo-otwarte-zrodla.txt', `PRAWO OTWARTE — LISTA ŹRÓDEŁ\nPrzygotowano: ${new Date().toISOString()}\n\n${body}\n\nLista do dalszej analizy, nie opinia prawna. Należy zweryfikować nowelizacje, przepisy przejściowe i wersję właściwą dla daty sprawy.\n`);
});
$('#clear-sources').addEventListener('click', () => { selectedSources.clear(); renderSelectedSources(); feedback('#saved-feedback', 'Lista została wyczyszczona.'); });
let currentSearch = null;
function renderResults(data) {
  const results = $('#search-results'); results.replaceChildren();
  $('#search-empty').hidden = true;
  for (const act of data.items) {
    const card = element('article', undefined, 'result-card');
    const meta = element('div', undefined, 'result-meta');
    meta.append(element('span', act.display_address), element('span', `ELI: ${act.eli}`));
    const actions = element('div', undefined, 'result-actions');
    actions.append(externalLink('Oficjalna publikacja ↗', act.source_url));
    const save = element('button', 'Dodaj do źródeł +'); save.type = 'button'; save.dataset.saveEli = act.eli;
    save.addEventListener('click', () => {
      if (selectedSources.size >= 30) { feedback('#search-feedback', 'Na liście jest już 30 źródeł. Pobierz ją lub usuń wybrane pozycje.', true); return; }
      selectedSources.set(act.eli, {...act}); renderSelectedSources();
      feedback('#search-feedback', `Dodano ${act.eli}. Otwórz zakładkę „Twoje źródła”, aby pobrać listę.`);
    });
    actions.append(save);
    if (data.mode === 'local') {
      const open = element('button', 'Kopia i pochodzenie →'); open.type = 'button';
      open.addEventListener('click', () => showAct(act.eli)); actions.append(open);
    }
    card.append(meta, element('h4', act.title, 'result-title'), element('span', `Status źródła: ${act.status}`, 'status-badge'),
      element('p', `Pobrano: ${dateText(act.fetched_at)}. Właściwa wersja dla Twojej sprawy wymaga weryfikacji.`, 'temporal-note'), actions);
    results.append(card);
  }
  if (!data.items.length) results.append(element('p', 'Brak wyników w tym zakresie. Spróbuj krótszego tytułu lub innego źródła. To nie oznacza braku przepisów dotyczących sprawy.', 'notice'));
  renderSelectedSources();
  const offset = data.offset || 0;
  $('#search-pagination').hidden = data.mode !== 'eli' || !data.total;
  $('#previous-page').disabled = offset === 0;
  $('#next-page').disabled = !data.returned || offset + data.returned >= data.total;
  $('#page-position').textContent = `${data.returned ? offset + 1 : 0}–${offset + data.returned} z ${data.total || 0}`;
  feedback('#search-feedback', data.mode === 'eli' ? `ELI: ${data.returned ? offset + 1 : 0}–${offset + data.returned} z ${data.total} wyników. Rok oznacza publikację, nie okres obowiązywania.` : `Lokalny katalog: ${data.returned} wyników (maksymalnie 20).`);
}
async function performSearch(criteria) {
  const button = $('#search-form button[type="submit"]');
  if (button.disabled) return;
  button.disabled = true;
  $('#search-results').setAttribute('aria-busy','true'); $('#search-pagination').hidden = true;
  feedback('#search-feedback', 'Szukamy w wybranym źródle…'); $('#search-results').replaceChildren(); $('#search-empty').hidden = true;
  try { const data = await request('/api/search', criteria); currentSearch = {...criteria}; renderResults(data); }
  catch (error) { feedback('#search-feedback', error.message, true); }
  finally { button.disabled = false; $('#search-results').setAttribute('aria-busy','false'); }
}
$('#search-form').addEventListener('submit', event => {
  event.preventDefault();
  performSearch({query:$('#query').value.trim(),mode:$('input[name="mode"]:checked').value,publisher:$('#publisher').value,year:$('#publication-year').value,offset:0});
});
for (const [id,delta] of [['previous-page',-20],['next-page',20]]) $( '#' + id).addEventListener('click', () => {
  if (currentSearch) performSearch({...currentSearch,offset:Math.max(0,currentSearch.offset+delta)});
});
async function showAct(eli) {
  const dialog = $('#act-dialog');
  $('#act-title').textContent = 'Pobieranie źródła…'; $('#act-text').textContent = ''; $('#act-provenance').replaceChildren(); $('#act-note').textContent = '';
  dialog.showModal();
  try {
    const act = await request('/api/act?eli=' + encodeURIComponent(eli));
    $('#act-title').textContent = act.title;
    $('#act-note').textContent = act.text_stale
      ? 'Metadane źródła zmieniły się po pobraniu tekstu. Poniższa kopia jest oznaczona jako nieaktualna i wyłączona z wyszukiwania pełnotekstowego.'
      : 'To kopia tekstu dostarczonego przez ELI, bez potwierdzenia wersji właściwej dla daty Twojej sprawy. Sprawdź nowelizacje i przepisy przejściowe.';
    $('#act-provenance').append(externalLink('Sprawdź oficjalną publikację ↗', act.source_url));
    for (const snapshot of act.snapshots) $('#act-provenance').append(element('p', `${snapshot.kind} · ${snapshot.fetched_at} · SHA-256: ${snapshot.sha256}`));
    $('#act-text').textContent = act.text || 'Tekst nie został jeszcze zaimportowany. Dostępne są metadane i odnośnik do źródła.';
  } catch (error) { $('#act-title').textContent = 'Nie udało się otworzyć kopii'; $('#act-note').textContent = error.message; }
}
$('#close-dialog').addEventListener('click', () => $('#act-dialog').close());
const today = new Date(); $('#event-date').max = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`;
$('#intake-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = $('#intake-form button[type="submit"]'); button.disabled = true;
  const description = $('#description').value.trim();
  feedback('#intake-feedback', 'Porządkujemy pytania…'); $('#intake-results').replaceChildren();
  try {
    const data = await request('/api/intake', {description, event_date: $('#event-date').value, domain: $('#domain').value});
    const card = element('article', undefined, 'intake-card');
    card.append(element('h4', data.domain_label), element('p', data.routing.reason));
    const questions = element('ol'); for (const text of data.questions) questions.append(element('li', text));
    card.append(questions, element('p', data.note));
    if (data.suggested_query) {
      const search = element('button', 'Poszukaj źródeł →', 'button primary'); search.type = 'button';
      search.addEventListener('click', () => { setTab('search'); $('#query').value = data.suggested_query; $('#query').focus(); });
      card.append(search);
    }
    const download = element('button', 'Pobierz notatkę ↓', 'button outline'); download.type = 'button';
    download.addEventListener('click', () => {
      const text = `PRAWO OTWARTE — NOTATKA SPRAWY\nTo notatka przygotowawcza, nie opinia prawna.\n\nOpis użytkownika:\n${description}\n\nData zdarzenia: ${data.event_date || 'nie podano'}\nDziedzina: ${data.domain_label}\nSposób ustalenia: ${data.routing.reason}\n\nPytania do wyjaśnienia:\n${data.questions.map((q,i) => `${i+1}. ${q}`).join('\n')}\n\nSugerowana fraza do wyszukiwania: ${data.suggested_query || 'do ustalenia'}\n\n${data.note}\n`;
      downloadText('prawo-otwarte-notatka.txt',text);
    });
    card.append(download); $('#intake-results').append(card); feedback('#intake-feedback', 'Notatka gotowa. Treść nie została zapisana w bazie aplikacji.');
  } catch (error) { feedback('#intake-feedback', error.message, true); }
  finally { button.disabled = false; }
});
$('#publication-year').max = String(new Date().getFullYear());
const statusReady = loadStatus();
document.querySelectorAll('[data-domain]').forEach(button => button.addEventListener('click', async () => {
  await statusReady;
  setTab('intake'); $('#domain').value = button.dataset.domain;
  $('#pracownia').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
  $('#description').focus({preventScroll:true});
}));
