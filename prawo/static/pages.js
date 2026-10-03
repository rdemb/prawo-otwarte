'use strict';
// Loaded only by the static Pages build. Never sends the case description.
window.PrawoPages = {
  data: null,
  async load() {
    if (!this.data) {
      const response = await fetch('./pages-data.json', {credentials:'omit', signal:AbortSignal.timeout(10000)});
      if (!response.ok) throw new Error('Nie udało się wczytać katalogu źródeł. Odśwież stronę.');
      this.data = await response.json();
    }
    return this.data;
  },
  async request(path, body) {
    const data = await this.load();
    if (path === '/api/status') {
      return {site_mode:'static', sources:data.sources, domains:Object.fromEntries(Object.entries(data.domains).map(([key,value])=>[key,value.label])),
        corpus:{metadata_count:0,text_count:0,last_import:null,complete_polish_law:false}, eli_enabled:true};
    }
    if (path === '/api/search') {
      if (body.mode !== 'eli') throw new Error('Lokalna baza nie jest jeszcze podłączona do tej strony.');
      if (typeof body.query !== 'string' || body.query.trim().length < 2 || body.query.length > 160) throw new Error('Wpisz od 2 do 160 znaków.');
      const offset = body.offset ?? 0;
      if (!Number.isInteger(offset) || offset < 0 || offset > 1000000) throw new Error('Nieprawidłowy numer strony.');
      const params = new URLSearchParams({title:body.query.trim(),limit:'20',offset:String(offset),sortBy:'promulgation',sortDir:'desc'});
      if (body.publisher) {
        if (!['DU','MP'].includes(body.publisher)) throw new Error('Nieprawidłowy dziennik.');
        params.set('publisher',body.publisher);
      }
      if (body.year) {
        const year = Number(body.year);
        if (!Number.isInteger(year) || year < 1900 || year > new Date().getFullYear()) throw new Error('Nieprawidłowy rok publikacji.');
        params.set('year',String(year));
      }
      let result;
      try {
        const response = await fetch('https://api.sejm.gov.pl/eli/acts/search?' + params, {credentials:'omit',signal:AbortSignal.timeout(15000)});
        if (!response.ok) throw new Error('ELI');
        result = await response.json();
      } catch { throw new Error('Katalog Sejmu jest chwilowo niedostępny. Spróbuj ponownie za chwilę.'); }
      if (!Array.isArray(result.items) || !Number.isInteger(result.totalCount) || result.totalCount < 0) throw new Error('Źródło zwróciło nieprawidłowy wynik.');
      const stamp = new Date().toISOString();
      const items = result.items.slice(0,20).map(item => {
        if (!/^(DU|MP)\/\d{4}\/\d{1,10}$/.test(item.ELI) || typeof item.title !== 'string' || !item.title.trim()) throw new Error('Nie udało się zweryfikować identyfikatora lub tytułu publikacji.');
        return {eli:item.ELI,title:item.title,display_address:item.displayAddress || item.ELI,status:item.status || 'brak statusu w źródle',
          source_url:'https://eli.gov.pl/eli/' + item.ELI + '/ogl',fetched_at:stamp,temporal_verified:false};
      });
      return {mode:'eli',items,offset,returned:items.length,total:result.totalCount,temporal_verified:false};
    }
    if (path === '/api/intake') {
      if (typeof body.description !== 'string' || body.description.trim().length < 20 || body.description.length > 4000) throw new Error('Opis powinien mieć od 20 do 4000 znaków.');
      const key = Object.hasOwn(data.domains,body.domain) ? body.domain : 'unknown';
      const domain = data.domains[key];
      return {kind:'intake_only',domain_label:domain.label,event_date:body.event_date || '',questions:domain.questions,
        suggested_query:domain.query,legal_answer:null,temporal_verified:false,
        routing:{method:key === 'unknown' ? 'unavailable' : 'user',reason:key === 'unknown' ? 'Wybierz dziedzinę samodzielnie, aby otrzymać bardziej szczegółowe pytania.' : 'Dziedzina wybrana przez Ciebie.'},
        note:'To uporządkowanie sprawy, nie ocena prawna. Data zdarzenia została zanotowana; wersja przepisów właściwa dla tej daty nie została jeszcze zweryfikowana.'};
    }
    throw new Error('Ta funkcja wymaga podłączenia serwera projektu.');
  }
};
