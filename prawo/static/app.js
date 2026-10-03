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
let serviceReady = false;
let modelEnabled = false;
let intakeBusy = false;
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
  serviceReady = false;
  $('#refresh-status').disabled = true;
  $('#lab-refresh').disabled = true;
  $('#lab-connection-status').textContent = 'Sprawdzamy dostępność modelu…';
  $('#service-label').textContent = 'Sprawdzamy połączenie…';
  $('#service-dot').className = 'connection-dot';
  try {
    const status = await request('/api/status');
    modelEnabled = status.basal?.enabled === true;
    if (status.site_mode === 'static') {
      $('#service-label').textContent = 'Tryb bez modelu';
      $('#service-detail').textContent = 'Notatka na Twoim urządzeniu · wyszukiwanie w ELI';
      $('#model-connection-state').textContent = 'MODEL NIEPODŁĄCZONY';
      $('#model-connection-note').textContent = 'Ta wersja działa bez API. Dziedzinę wybierasz samodzielnie; testy BASAL-a są niedostępne.';
      $('#faq-model-copy').textContent = $('#model-connection-note').textContent;
      const stats = [['2', 'dzienniki w wyszukiwaniu'], ['Bez konta', 'dostęp do narzędzi'], ['U Ciebie', 'powstaje notatka sprawy']];
      ['metadata-count','text-count','import-date'].forEach((id, index) => {
        const node = $('#' + id); node.textContent = stats[index][0]; node.nextElementSibling.textContent = stats[index][1];
      });
      $('#connection-status').textContent = 'Wyszukiwarka łączy się bezpośrednio z oficjalnym katalogiem Sejmu. Lokalna baza projektu i automatyczna analiza spraw nie są jeszcze podłączone do tej strony.';
      $('input[value="local"]').disabled = true; $('input[value="local"]').closest('label').hidden = true;
      $('#search-panel .panel-intro').textContent = 'Wpisz tytuł lub fragment tytułu aktu. Otrzymasz odnośniki do oficjalnych publikacji.';
      $('#search-tab small').textContent = 'Oficjalne tytuły i publikacje';
      $('#intake-form > .micro').textContent = 'Opis i notatka pozostają na Twoim urządzeniu. W tej wersji dziedzinę wybierasz samodzielnie; opis nie trafia do modelu ani na serwer projektu.';
      $('#domain option[value="unknown"]').textContent = 'Wybierz dziedzinę (opcjonalnie)';
      $('#method-privacy-copy').textContent = 'Nie wymagamy konta ani nie zapisujemy opisu sprawy. Notatka powstaje w pamięci przeglądarki. Pobranie jej na urządzenie jest Twoją decyzją.';
      $('#method-model-copy').textContent = 'Projekt rozwijamy w oparciu o BASAL. W tej publicznej wersji samodzielnie wybierasz dziedzinę; podłączenie modelu jest kolejnym etapem. Narzędzie nie rozstrzyga uprawnień ani nie oblicza terminów.';
    } else {
      $('#metadata-count').textContent = status.corpus.metadata_count.toLocaleString('pl-PL');
      $('#text-count').textContent = status.corpus.text_count.toLocaleString('pl-PL');
      $('#import-date').textContent = dateText(status.corpus.last_import);
      $('#connection-status').textContent = 'Dane pochodzą z działającej aplikacji. Pokrycie prawa i poprawność historycznych wersji nie są jeszcze potwierdzone.';
      $('#service-label').textContent = 'Połączono z aplikacją';
      $('#service-detail').textContent = `${modelEnabled ? 'BASAL włączony' : 'Ręczny wybór dziedziny'} · akty: ${status.corpus.metadata_count} · teksty: ${status.corpus.text_count}`;
      $('#service-dot').classList.add('ready');
      $('#model-connection-state').textContent = modelEnabled ? 'KLASYFIKACJA WŁĄCZONA' : 'KLASYFIKACJA WYŁĄCZONA';
      const modelNote = modelEnabled
        ? 'Ta instalacja ma włączony lokalny BASAL do proponowania dziedziny. Przy awarii lub niejednoznacznym wyniku możesz wybrać dziedzinę samodzielnie. Klasyfikacja nie jest opinią prawną.'
        : 'Klasyfikacja przez model jest wyłączona w tej instalacji. Wybierz dziedzinę samodzielnie; wyszukiwanie i notatka pozostają dostępne.';
      $('#model-connection-note').textContent = modelNote;
      $('#faq-model-copy').textContent = modelNote;
      $('#faq-privacy-copy').textContent = 'Opis obsługuje serwer tej instalacji; przy automatycznym wyborze dziedziny i włączonym BASAL-u także jego lokalny model. Aplikacja nie zapisuje opisu w bazie. Do API Sejmu trafia wyłącznie fraza wyszukiwania i wybrane filtry.';
      $('#intake-form > .micro').textContent = 'Opis trafi do serwera projektu, a przy automatycznym wyborze dziedziny także do lokalnego BASAL-a. Aplikacja nie zapisuje go w bazie. Nie wpisuj danych osobowych.';
      $('#method-privacy-copy').textContent = 'Nie wymagamy konta. Opis jest przetwarzany na serwerze projektu, bez zapisu do bazy aplikacji. Przy automatycznym wyborze dziedziny obsługuje go również lokalny BASAL. Nie wpisuj danych identyfikujących osoby.';
      $('#roadmap-tools-copy').textContent = 'Wyszukiwanie ELI, lokalny katalog, lista źródeł i notatka sprawy. Bez konta. Opis przetwarza serwer projektu.';
      $('#roadmap-model-state').textContent = modelEnabled ? 'DOSTĘPNE W TEJ INSTALACJI' : 'DO URUCHOMIENIA';
      $('#roadmap-model-copy').textContent = modelEnabled ? 'BASAL proponuje dziedzinę sprawy. Wynik może być niejednoznaczny; możesz samodzielnie wybrać dziedzinę. Trafność prawna wymaga dalszych testów.' : modelNote;
    }
    $('#privacy-processing').textContent = $('#intake-form > .micro').textContent;
    if (status.site_mode === 'static') $('#faq-privacy-copy').textContent = $('#privacy-processing').textContent;
    renderSources(status.sources);
    const selectedDomain = $('#domain').value;
    $('#domain').querySelectorAll('option:not([value="unknown"])').forEach(option => option.remove());
    for (const [key, label] of Object.entries(status.domains)) {
      if (key !== 'unknown') { const option = element('option', label); option.value = key; $('#domain').append(option); }
    }
    $('#domain').value = [...$('#domain').options].some(option => option.value === selectedDomain) ? selectedDomain : 'unknown';
    $('input[value="eli"]').disabled = !status.eli_enabled;
    if (!status.eli_enabled) {
      $('input[value="eli"]').disabled = true; $('input[value="local"]').checked = true; updateSearchPrivacy();
    }
    serviceReady = true;
    $('#service-detail').textContent += ' · sprawdzono ' + new Date().toLocaleTimeString('pl-PL', {hour:'2-digit', minute:'2-digit'});
  } catch (error) {
    $('#connection-status').textContent = error.message;
    $('#model-connection-state').textContent = 'BRAK POŁĄCZENIA';
    $('#model-connection-note').textContent = 'Nie udało się odczytać stanu aplikacji. Nie potwierdzamy dostępności modelu. Użyj przycisku „Sprawdź połączenie” nad pracownią.';
    $('#faq-model-copy').textContent = $('#model-connection-note').textContent;
    if (window.PrawoPages?.apiBaseUrl) {
      $('#faq-privacy-copy').textContent = 'Ta strona jest skonfigurowana do wysyłania zapytań i opisu na serwer projektu, ale obecnie nie udało się połączyć. Nie potwierdzamy aktualnej dostępności API. Przy próbie wysłania opis jest kierowany do tego serwera.';
    }
    $('#service-label').textContent = 'Nie udało się potwierdzić połączenia';
    $('#service-detail').textContent = 'Sprawdź ponownie. Wpisany opis pozostaje w formularzu.';
    $('#service-dot').classList.add('offline');
    renderSources(sourceFallback);
  } finally {
    $('#refresh-status').disabled = false;
    $('#lab-refresh').disabled = false;
    $('#lab-connection-status').textContent = !serviceReady ? 'Brak połączenia z aplikacją. Spróbuj ponownie.' : modelEnabled ? 'BASAL jest włączony. Uruchom przykład, aby sprawdzić rzeczywistą odpowiedź.' : 'Ta instalacja działa bez modelu. Przykłady można przeczytać, ale test jest niedostępny.';
    $('#run-benchmark').disabled = !serviceReady || !modelEnabled || intakeBusy;
    if (!serviceReady || !modelEnabled) feedback('#benchmark-feedback', serviceReady ? 'Ta instalacja działa bez modelu. Możesz nadal przygotować notatkę, wybierając dziedzinę samodzielnie.' : 'Najpierw sprawdź połączenie z aplikacją nad pracownią.');
    else if (!measurements.rows().some(row => row.sampleId)) feedback('#benchmark-feedback', '');
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
      meta.append(element('span', act.indexed_text ? 'Tekst dostępny lokalnie' : act.text_stale ? 'Kopia wymaga aktualizacji' : 'Tylko metadane', 'status-badge'));
      const open = element('button', act.indexed_text ? 'Tekst i pochodzenie →' : 'Metadane i pochodzenie →'); open.type = 'button';
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
let documentRequest = 0;
async function showAct(eli) {
  const requestId = ++documentRequest;
  const dialog = $('#act-dialog');
  $('#act-title').textContent = 'Pobieranie źródła…'; $('#act-text').textContent = ''; $('#act-provenance').replaceChildren(); $('#act-note').textContent = '';
  dialog.showModal();
  try {
    const act = await request('/api/act?eli=' + encodeURIComponent(eli));
    if (requestId !== documentRequest || !dialog.open) return;
    $('#act-title').textContent = act.title;
    $('#act-note').textContent = act.text_stale
      ? 'Metadane źródła zmieniły się po pobraniu tekstu. Poniższa kopia jest oznaczona jako nieaktualna i wyłączona z wyszukiwania pełnotekstowego.'
      : 'To kopia tekstu dostarczonego przez ELI, bez potwierdzenia wersji właściwej dla daty Twojej sprawy. Sprawdź nowelizacje i przepisy przejściowe.';
    $('#act-provenance').append(externalLink('Sprawdź oficjalną publikację ↗', act.source_url));
    for (const snapshot of act.snapshots) $('#act-provenance').append(element('p', `${snapshot.kind} · ${snapshot.fetched_at} · SHA-256: ${snapshot.sha256}`));
    $('#act-text').textContent = act.text || 'Tekst nie został jeszcze zaimportowany. Dostępne są metadane i odnośnik do źródła.';
  } catch (error) { if (requestId !== documentRequest || !dialog.open) return; $('#act-title').textContent = 'Nie udało się otworzyć kopii'; $('#act-note').textContent = error.message; }
}
$('#act-dialog').addEventListener('close', () => { documentRequest++; });
$('#close-dialog').addEventListener('click', () => $('#act-dialog').close());
const today = new Date(); $('#event-date').max = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`;
const measurements = PrawoMetrics.createSession();
const seconds = ms => (ms / 1000).toLocaleString('pl-PL', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' s';
const methodLabels = {basal:'Propozycja BASAL-a', basal_abstained:'Brak rozstrzygnięcia', user:'Ręczny wybór', unavailable:'Model niedostępny', error:'Błąd połączenia'};
const sampleCases = [
  {id:'work', label:'Praca', expected:'work', text:'Pracodawca wręczył mi wypowiedzenie umowy o pracę. Chcę uporządkować dokumenty przed rozmową z prawnikiem.'},
  {id:'consumer', label:'Zakupy i konsument', expected:'consumer', text:'Kupiłem od sklepu internetowego nowy odkurzacz do domu. Urządzenie nie działa, a sprzedawca odrzucił reklamację. Chcę uporządkować dokumenty zakupu.'},
  {id:'civil', label:'Umowy i sprawy cywilne', expected:'civil', text:'Pożyczyłem znajomemu pieniądze na podstawie pisemnej umowy. Uzgodniony termin zwrotu minął, a pieniędzy nie otrzymałem. Chcę przygotować dokumenty dotyczące tej umowy.'},
  {id:'family', label:'Rodzina', expected:'family', text:'Sprawa dotyczy alimentów na dziecko i wcześniejszego orzeczenia sądu rodzinnego. Chcę uporządkować informacje o płatnościach przed konsultacją z prawnikiem.'},
  {id:'administrative', label:'Urząd i administracja', expected:'administrative', text:'Otrzymałem decyzję administracyjną od urzędu gminy. Pismo ma pouczenie o odwołaniu. Chcę uporządkować datę doręczenia i treść pouczenia.'},
  {id:'tax', label:'Podatki', expected:'tax', text:'Urząd skarbowy wezwał mnie do wyjaśnień dotyczących rocznego rozliczenia podatku PIT. Chcę przygotować deklarację i dokumenty do rozmowy z doradcą.'},
  {id:'criminal', label:'Sprawy karne', expected:'criminal', text:'Otrzymałem wezwanie na przesłuchanie jako podejrzany w postępowaniu karnym. Chcę uporządkować dokumenty przed pilnym kontaktem z obrońcą.'},
  {id:'property', label:'Mieszkanie i nieruchomości', expected:'property', text:'Wynajmowałem mieszkanie i po zakończeniu najmu właściciel nie zwrócił kaucji. Mam umowę najmu i protokół zdania lokalu. Chcę uporządkować te dokumenty.'}
];
function renderMeasurements() {
  const rows = measurements.rows(), summary = measurements.summary();
  $('#metric-time').textContent = summary.medianMs === null ? '—' : seconds(summary.medianMs);
  $('#metric-time-note').textContent = summary.completed ? `n = ${summary.completed} · P95: ${summary.p95Ms === null ? 'od 20 odpowiedzi' : seconds(summary.p95Ms)}` : 'Wyślij pierwszą sprawę do BASAL-a';
  $('#metric-completed').textContent = `${summary.completed} / ${summary.attempts}`;
  $('#outcome-counts').textContent = `Propozycje: ${summary.proposals} · bez rozstrzygnięcia: ${summary.abstentions} · niedostępne lub błędy: ${summary.unavailable}`;
  $('#metric-rating').textContent = summary.rated ? `${summary.positive} / ${summary.rated}` : '—';
  $('#metric-rating-note').textContent = summary.rated ? 'Propozycje ocenione jako przydatne / wszystkie oceny' : 'Brak ocen propozycji dziedziny';
  $('#benchmark-score').textContent = summary.benchmarkCount ? `${summary.benchmarkMatches} / ${summary.benchmarkCount}` : '—';
  $('#benchmark-score-note').textContent = summary.benchmarkCount ? `Zgodne odpowiedzi / ukończone testy · ${summary.benchmarkDistinct} z 8 różnych przykładów` : 'Zgodność z oczekiwaną dziedziną pojawi się po teście.';
  $('#measurement-count').textContent = `${rows.length} / 50 pomiarów`;
  $('#measurement-empty').hidden = rows.length > 0;
  $('#download-metrics').disabled = !rows.length;
  $('#clear-metrics').disabled = !rows.length || intakeBusy;
  const list = $('#measurement-list'); list.replaceChildren();
  for (const row of rows.slice(-6).reverse()) {
    const item = element('li');
    const info = element('div');
    info.append(element('strong', methodLabels[row.method]), element('small', `${row.sampleId ? 'Przykład: ' + sampleCases.find(sample => sample.id === row.sampleId)?.label : 'Notatka sprawy'} · ${new Date(row.at).toLocaleTimeString('pl-PL')}`));
    item.append(info, element('span', seconds(row.ms))); list.append(item);
  }
}
function setIntakeBusy(busy) {
  intakeBusy = busy;
  $('#intake-form button[type="submit"]').disabled = busy;
  $('#run-benchmark').disabled = busy || !serviceReady || !modelEnabled;
  $('#benchmark-case').disabled = busy;
  $('#clear-metrics').disabled = busy || !measurements.rows().length;
}
async function measuredIntake(payload, sample = null) {
  const started = performance.now();
  const modelAttempt = payload.domain === 'unknown' && modelEnabled;
  try {
    const data = await request('/api/intake', payload);
    if (data.kind !== 'intake_only' || data.legal_answer !== null || !data.routing || !Array.isArray(data.questions)) throw new Error('Nieprawidłowa odpowiedź aplikacji. Spróbuj ponownie później.');
    const ms = performance.now() - started;
    const id = measurements.add({ms, modelAttempt, method:data.routing.method, predicted:data.routing.domain, sampleId:sample?.id, expected:sample?.expected});
    renderMeasurements(); return {data, ms, id};
  } catch (error) {
    measurements.add({ms:performance.now() - started, modelAttempt, method:'error', sampleId:sample?.id, expected:sample?.expected});
    renderMeasurements(); throw error;
  }
}
$('#download-metrics').addEventListener('click', () => downloadText('prawo-otwarte-pomiary.json', JSON.stringify({schema:'prawo-otwarte/session-metrics/v1', exportedAt:new Date().toISOString(), scope:'Current browser tab; last 50 intakes; no case content', timing:'Browser round-trip, not model inference time', benchmark:'Synthetic pilot v1; labels not expert-reviewed; repetitions count', legalCorrectness:'not_evaluated', summary:measurements.summary(), measurements:measurements.rows()}, null, 2)));
$('#clear-metrics').addEventListener('click', () => { measurements.clear(); renderMeasurements(); feedback('#benchmark-feedback', ''); feedback('#metrics-feedback', 'Pomiary usunięto. Nowe oceny będą dostępne przy kolejnej notatce.'); document.querySelectorAll('.rating-controls button').forEach(button => button.disabled = true); });
$('#benchmark-case').replaceChildren();
$('#benchmark-case').disabled = false;
for (const sample of sampleCases) { const option = element('option', sample.label); option.value = sample.id; $('#benchmark-case').append(option); }
function showBenchmarkCase() {
  const sample = sampleCases.find(item => item.id === $('#benchmark-case').value);
  $('#benchmark-description').textContent = sample.text;
  $('#benchmark-expected').textContent = sample.label;
  feedback('#benchmark-feedback', '');
}
$('#benchmark-case').addEventListener('change', showBenchmarkCase); showBenchmarkCase();
$('#run-benchmark').addEventListener('click', async () => {
  if (intakeBusy || !serviceReady || !modelEnabled) return;
  const sample = sampleCases.find(item => item.id === $('#benchmark-case').value);
  setIntakeBusy(true); feedback('#benchmark-feedback', 'BASAL sprawdza przykład. To może potrwać do 40 sekund.');
  try {
    const {data, ms} = await measuredIntake({description:sample.text, event_date:'', domain:'unknown'}, sample);
    const match = data.routing.method === 'basal' && data.routing.domain === sample.expected;
    feedback('#benchmark-feedback', `${match ? 'Zgodność z oczekiwaną dziedziną.' : methodLabels[data.routing.method] + ': ' + data.domain_label + '.'} Czas odpowiedzi: ${seconds(ms)}. ${data.routing.reason}`);
  } catch (error) { feedback('#benchmark-feedback', error.message, true); }
  finally { setIntakeBusy(false); }
});
let heroSample = sampleCases[0];
document.querySelectorAll('[data-hero-sample]').forEach(button => button.addEventListener('click', () => {
  heroSample = sampleCases.find(sample => sample.id === button.dataset.heroSample);
  $('#hero-sample-text').textContent = '„' + heroSample.text + '”';
  document.querySelectorAll('[data-hero-sample]').forEach(node => node.setAttribute('aria-pressed', String(node === button)));
}));
function descriptionChanged() {
  $('#description-count').textContent = `${$('#description').value.length} / 4000 znaków${$('#description').value.trim().length < 20 ? ' · minimum 20' : ''}`;
  if ($('#intake-results').childElementCount) {
    $('#intake-results').replaceChildren();
    feedback('#intake-feedback', 'Zmieniono dane. Utwórz notatkę ponownie, aby uwzględnić aktualny opis i dziedzinę.');
  }
}
$('#description').addEventListener('input', descriptionChanged);
$('#event-date').addEventListener('input', descriptionChanged);
$('#domain').addEventListener('change', descriptionChanged);
$('#open-example').addEventListener('click', () => {
  setTab('intake'); $('#pracownia').scrollIntoView();
  if (!$('#description').value.trim()) { $('#description').value = heroSample.text; $('#domain').value = 'unknown'; descriptionChanged(); }
  else feedback('#intake-feedback', 'Twój opis jest już w formularzu. Wyczyść go, jeśli chcesz otworzyć wybrany przykład.');
  $('#description').focus({preventScroll:true});
});
$('#intake-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (intakeBusy) return;
  setIntakeBusy(true);
  await statusReady;
  if (!serviceReady) {
    feedback('#intake-feedback', 'Nie udało się potwierdzić połączenia. Opis pozostał w formularzu. Użyj „Sprawdź połączenie” nad pracownią i spróbuj ponownie.', true);
    setIntakeBusy(false); return;
  }
  const payload = {description:$('#description').value.trim(), event_date:$('#event-date').value, domain:$('#domain').value};
  if (payload.description.length < 20) { feedback('#intake-feedback', 'Opis powinien zawierać co najmniej 20 znaków poza białymi znakami.', true); setIntakeBusy(false); return; }
  const started = performance.now();
  feedback('#intake-feedback', 'Przygotowujemy notatkę. Może to potrwać do 40 sekund.');
  const timer = setInterval(() => feedback('#intake-feedback', `Przygotowujemy notatkę… ${Math.floor((performance.now() - started) / 1000)} s. Opis pozostaje w formularzu.`), 1000);
  $('#intake-results').replaceChildren(); $('#intake-results').setAttribute('aria-busy', 'true');
  try {
    const {data, ms, id} = await measuredIntake(payload);
    clearInterval(timer);
    if (payload.description !== $('#description').value.trim() || payload.event_date !== $('#event-date').value || payload.domain !== $('#domain').value) {
      feedback('#intake-feedback', 'Dane zmieniły się w trakcie oczekiwania. Utwórz notatkę ponownie dla aktualnego opisu.'); return;
    }
    const card = element('article', undefined, 'intake-card');
    card.append(element('span', `${methodLabels[data.routing.method]} · ${seconds(ms)}`, 'result-meta'), element('h4', data.domain_label));
    const reason = element('p', data.routing.reason); card.append(reason);
    let confirmed = data.routing.method === 'user';
    if (data.routing.method === 'basal' && data.routing.domain !== 'unknown') {
      const controls = element('div', undefined, 'confirmation-controls');
      const confirm = element('button', 'Potwierdź dziedzinę', 'button primary'); confirm.type = 'button';
      confirm.addEventListener('click', () => { confirmed = true; $('#domain').value = data.routing.domain; reason.textContent = 'Propozycja BASAL-a potwierdzona przez Ciebie.'; confirm.textContent = 'Dziedzina potwierdzona ✓'; confirm.disabled = true; });
      controls.append(confirm); card.append(controls);
    }
    if (data.routing.method !== 'user') {
      const change = element('button', 'Wybierz dziedzinę samodzielnie', 'text-button'); change.type = 'button';
      change.addEventListener('click', () => { $('#domain').focus(); $('#domain').scrollIntoView({block:'center'}); }); card.append(change);
    }
    const questions = element('ol'); for (const text of data.questions) questions.append(element('li', text));
    card.append(questions, element('p', data.note));
    const actions = element('div', undefined, 'note-actions');
    if (data.suggested_query) {
      const search = element('button', 'Poszukaj źródeł', 'button primary'); search.type = 'button';
      search.addEventListener('click', () => { setTab('search'); $('#query').value = data.suggested_query; $('#query').focus(); $('#search-form').requestSubmit(); });
      actions.append(search);
    }
    const download = element('button', 'Pobierz notatkę', 'button outline'); download.type = 'button';
    download.addEventListener('click', () => {
      const text = `PRAWO OTWARTE — NOTATKA SPRAWY\nTo notatka przygotowawcza, nie opinia prawna.\n\nOpis użytkownika:\n${payload.description}\n\nData zdarzenia: ${data.event_date || 'nie podano'}\nDziedzina: ${data.domain_label}\nSposób ustalenia: ${data.routing.reason}\nPotwierdzenie użytkownika: ${confirmed ? 'tak' : 'nie'}\nCzas odpowiedzi (sieć i aplikacja): ${seconds(ms)}\n\nPytania do wyjaśnienia:\n${data.questions.map((q,i) => `${i+1}. ${q}`).join('\n')}\n\nSugerowana fraza do wyszukiwania: ${data.suggested_query || 'do ustalenia'}\n\n${data.note}\n`;
      downloadText('prawo-otwarte-notatka.txt', text);
    });
    actions.append(download); card.append(actions);
    if (data.routing.method === 'basal' && data.routing.domain !== 'unknown') {
      const rating = element('div', undefined, 'rating-controls'); rating.append(element('p', 'Czy propozycja dziedziny była przydatna? Ocena pozostaje w tej karcie.'));
      for (const [label, value] of [['Tak', true], ['Nie', false], ['Nie oceniam', null]]) {
        const button = element('button', label); button.type = 'button'; button.setAttribute('aria-pressed', 'false');
        button.addEventListener('click', () => { measurements.rate(id, value); renderMeasurements(); rating.querySelectorAll('button').forEach(node => node.setAttribute('aria-pressed', String(node === button))); }); rating.append(button);
      }
      card.append(rating);
    }
    $('#intake-results').append(card); feedback('#intake-feedback', `Notatka gotowa w ${seconds(ms)}. Nie jest oceną prawną. Treść nie została zapisana w bazie aplikacji.`);
  } catch (error) { clearInterval(timer); feedback('#intake-feedback', error.message, true); }
  finally { clearInterval(timer); setIntakeBusy(false); $('#intake-results').setAttribute('aria-busy', 'false'); }
});
renderMeasurements();
$('#publication-year').max = String(new Date().getFullYear());
let statusReady = loadStatus();
for (const id of ['refresh-status','lab-refresh']) $('#' + id).addEventListener('click', () => { if (!$('#refresh-status').disabled) statusReady = loadStatus(); });
document.querySelectorAll('[data-domain]').forEach(button => button.addEventListener('click', async () => {
  await statusReady;
  setTab('intake'); $('#domain').value = button.dataset.domain; descriptionChanged();
  $('#pracownia').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
  $('#description').focus({preventScroll:true});
}));

$('#build-label').textContent = 'Wydanie: ' + ($('meta[name="prawo-build"]')?.content || 'lokalne');
document.documentElement.dataset.appReady = 'true';
