'use strict';
// Detect an incomplete download/startup without silently clearing a visitor's work.
window.addEventListener('load', () => {
  const banner = document.querySelector('#startup-problem');
  const ready = document.documentElement.dataset.appReady === 'true';
  const styled = getComputedStyle(document.documentElement).getPropertyValue('--prawo-ui').trim() === 'ready';
  if (!ready || !styled) {
    banner.hidden = false;
    document.querySelector('#startup-problem-title').textContent = !ready
      ? 'Nie udało się uruchomić wszystkich narzędzi.' : 'Nie udało się wczytać wyglądu strony.';
    if (!ready) document.querySelectorAll('form button[type="submit"], #run-benchmark').forEach(button => button.disabled = true);
  }
  document.querySelector('#reload-application').addEventListener('click', async event => {
    const button = event.currentTarget;
    button.disabled = true;
    button.textContent = 'Pobieranie plików…';
    try {
      // Revalidate resources too: a failed response may have been cached by a proxy.
      const urls = [...document.querySelectorAll('script[src], link[rel="stylesheet"]')].map(node => node.src || node.href);
      await Promise.all(urls.map(async url => {
        if (new URL(url).origin !== location.origin) throw new Error('Unexpected asset origin');
        const response = await fetch(url, {cache:'reload', credentials:'same-origin'});
        if (!response.ok) throw new Error('Asset unavailable');
        await response.arrayBuffer();
      }));
      const address = new URL(location.href);
      address.searchParams.set('refresh', String(Date.now()));
      location.replace(address.href);
    } catch {
      document.querySelector('#startup-problem-title').textContent = 'Pliki nadal są niedostępne. Sprawdź połączenie i spróbuj ponownie.';
      button.disabled = false;
      button.textContent = 'Pobierz stronę ponownie';
    }
  });
});
