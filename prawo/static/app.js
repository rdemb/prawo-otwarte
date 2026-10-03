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
  const timeout = path === '/api/intake' ? 40000 : 25000;
  const options = {signal: AbortSignal.timeout(timeout), credentials: 'same-origin'};
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
function setTab(name, focus = false) {
  for (const key of ['search', 'intake']) {
    const active = key === name;
    $(`#${key}-tab`).classList.toggle('active', active);
    $(`#${key}-tab`).setAttribute('aria-selected', String(active));
    $(`#${key}-tab`).tabIndex = active ? 0 : -1;
    $(`#${key}-panel`).hidden = !active;
  }
  if (focus) $(`#${name}-tab`).focus();
}
for (const name of ['search', 'intake']) {
  $(`#${name}-tab`).addEventListener('click', () => setTab(name));
  $(`#${name}-tab`).addEventListener('keydown', (event) => {
    if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
      event.preventDefault();
      setTab(event.key === 'Home' ? 'search' : event.key === 'End' ? 'intake' : name === 'search' ? 'intake' : 'search', true);
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
      document.querySelectorAll('.method-list details')[3].querySelector('p').textContent = 'Nie wymagamy konta ani nie zapisujemy opisu sprawy. Notatka powstaje w pamięci przeglądarki. Pobranie jej na urządzenie jest Twoją decyzją.';
      document.querySelectorAll('.method-list details')[2].querySelector('p').textContent = 'W tej publicznej wersji samodzielnie wybierasz dziedzinę. Integracja modelu na serwerze jest kolejnym etapem. Narzędzie nie rozstrzyga uprawnień, nie oblicza terminów i nie prognozuje wyniku postępowania.';
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
  $('#search-privacy').textContent = mode === 'eli'
    ? 'Fraza wyszukiwania trafi do API Sejmu. Wpisz temat lub tytuł aktu, bez danych osobowych.'
    : 'Wyszukiwanie obejmuje wyłącznie dokumenty zaimportowane do tej instalacji. Brak wyniku nie oznacza braku odpowiedniego przepisu.';
}
document.querySelectorAll('input[name="mode"]').forEach(node => node.addEventListener('change', updateSearchPrivacy));
document.querySelectorAll('[data-query]').forEach(button => button.addEventListener('click', () => {
  $('#query').value = button.dataset.query; $('#search-form').requestSubmit();
}));
function renderResults(data) {
  const results = $('#search-results'); results.replaceChildren();
  $('#search-empty').hidden = true;
  for (const act of data.items) {
    const card = element('article', undefined, 'result-card');
    const meta = element('div', undefined, 'result-meta');
    meta.append(element('span', act.display_address), element('span', `ELI: ${act.eli}`));
    const actions = element('div', undefined, 'result-actions');
    actions.append(externalLink('Oficjalna publikacja ↗', act.source_url));
    if (data.mode === 'local') {
      const open = element('button', 'Kopia i pochodzenie →'); open.type = 'button';
      open.addEventListener('click', () => showAct(act.eli)); actions.append(open);
    }
    card.append(meta, element('h4', act.title, 'result-title'), element('span', `Status źródła: ${act.status}`, 'status-badge'),
      element('p', `Pobrano: ${dateText(act.fetched_at)}. Właściwa wersja dla Twojej sprawy wymaga weryfikacji.`, 'temporal-note'), actions);
    results.append(card);
  }
  if (!data.items.length) results.append(element('p', 'Brak wyników w tym zakresie. Spróbuj krótszego tytułu lub innego źródła. To nie oznacza braku przepisów dotyczących sprawy.', 'notice'));
  feedback('#search-feedback', data.mode === 'eli' ? `ELI: pokazano ${data.returned} z ${data.total} wyników. Wyszukiwanie po tytułach.` : `Lokalny katalog: ${data.returned} wyników (maksymalnie 20).`);
}
$('#search-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = $('#search-form button[type="submit"]'); button.disabled = true;
  feedback('#search-feedback', 'Szukamy w wybranym źródle…'); $('#search-results').replaceChildren();
  try { renderResults(await request('/api/search', {query: $('#query').value.trim(), mode: $('input[name="mode"]:checked').value})); }
  catch (error) { feedback('#search-feedback', error.message, true); }
  finally { button.disabled = false; }
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
  const waiting = $('#domain').value === 'unknown' && !window.PrawoPages
    ? 'Rozpoznajemy dziedzinę i porządkujemy pytania. Może to potrwać do 40 sekund.'
    : 'Porządkujemy pytania…';
  feedback('#intake-feedback', waiting); $('#intake-results').replaceChildren();
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
      const url = URL.createObjectURL(new Blob([text], {type:'text/plain;charset=utf-8'}));
      const a = element('a'); a.href = url; a.download = 'prawo-otwarte-notatka.txt'; document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
    card.append(download); $('#intake-results').append(card); feedback('#intake-feedback', 'Notatka gotowa. Treść nie została zapisana w bazie aplikacji.');
  } catch (error) { feedback('#intake-feedback', error.message, true); }
  finally { button.disabled = false; }
});
loadStatus();
