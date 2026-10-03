# Sprawdzenia wersji 0.1

Data: 2026-10-03. Środowisko robocze, **nie docelowy VPS**.

## Wykonane

- Python 3.12: `python -m unittest discover -s tests -v` — 24 testy, PASS.
- `python -m compileall -q prawo` i `node --check prawo/static/app.js` — PASS.
- Gunicorn 26.2.0, jeden proces / cztery wątki: `/healthz` i `/api/status` — HTTP 200.
- Rzeczywisty import `bootstrap --texts`: 4 rekordy metadanych, 3 teksty HTML.
  Źródła: DU/1997/483, DU/1964/93, DU/1974/141, DU/2014/827.
  Pierwszy z tych rekordów nie deklarował dostępnego HTML; nie zastąpiono go
  wymyślonym ani pobranym z niezweryfikowanego miejsca tekstem.
- Rzeczywiste wyszukiwanie tytułów przez API Sejmu: „Kodeks pracy” — pokazano
  20 ze 110 wyników; „Kodeks cywilny” — 20 z 61. Są to wyniki z chwili testu,
  a nie stałe oczekiwane liczby ani liczba aktów obowiązujących.
- Test w Chrome Headless Shell 154 przez Playwright, widoki 1440×1050 i 390×844:
  wyszukiwanie lokalne, otwarcie tekstu aktu i pochodzenia (150 586 znaków tekstu KP),
  wyszukiwanie w ELI, wywiad z ręcznym wyborem dziedziny, pobranie notatki — PASS.
- Przegląd zrzutów desktop/mobile: brak poziomego przepełnienia na mobile
  (`scrollWidth=390`, `innerWidth=390`), brak błędów JavaScript w tych ścieżkach.

Testy automatyczne obejmują między innymi: tożsamość aktu w odpowiedzi,
nieprawidłowy JSON źródła, pochodzenie i sumy kopii, idempotentny import,
wyłączenie zmienionego tekstu z FTS, niedostępność źródeł i modelu, błędne
rozkłady BASAL-a, brak zapisywania treści sprawy, walidację wejścia,
limit żądań i odrzucanie obcego Origin.

## Granice tych wyników

Nie wykonano tutaj połączenia z modelem na serwerze właściciela, migracji VPS,
testu odtwarzania tamtejszego backupu, konfiguracji domeny ani publicznego HTTPS.
Test adaptera BASAL-a używa kontrolowanych odpowiedzi; nie dowodzi zgodności
z konkretną zainstalowaną wersją modelu ani trafności rozpoznawania prawa.

Nie przeprowadzono walidacji merytorycznej przez prawników, audytu bezpieczeństwa,
testu dużego ruchu, rekonstrukcji historycznych przepisów ani pełnego audytu
dostępności. Liczniki i dostępność źródeł w każdej instalacji wynikają z jej danych.
Do repozytorium nie dołączono zaimportowanej bazy, prywatnych spraw ani raportu VPS.

Workflow `application-checks` uruchamia testy offline na Pythonie 3.12 i 3.13
oraz sprawdza składnię JS. Bieżący wynik CI należy odczytywać w GitHub Actions.

## Wariant statyczny GitHub Pages

Po dodaniu wariantu Pages: 26 testów offline — PASS; sprawdzenie składni obu
plików JavaScript — PASS. Builder publikuje tylko siedem dozwolonych zasobów,
odrzuca katalog wyjściowy z obcą zawartością i używa względnych ścieżek.

Test przeglądarki pod `/prawo-otwarte/`, desktop 1440×1050 i mobile 390×844:
rzeczywiste wyszukiwanie w ELI (20 ze 110 wyników dla „Kodeks pracy”), odnośniki
do źródła, ręczny wybór dziedziny i pobranie notatki — PASS. Rejestr żądań nie
zawierał syntetycznego opisu sprawy ani wywołań backendu aplikacji. Brak błędów
JS i poziomego przepełnienia widoku mobile. Model nie jest podłączony w Pages.

Izolowana przeglądarka testowa wymagała pominięcia lokalnego błędu magazynu
certyfikatów; kod strony nie wyłącza TLS. Niezależne połączenie curl z ELI
przeszło weryfikację certyfikatu. Stan publicznego wdrożenia należy sprawdzić
osobno w workflow `Publish website` po włączeniu GitHub Pages.
