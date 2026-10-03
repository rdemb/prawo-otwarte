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

## Rozbudowa publicznej pracowni — 2026-10-03

- 30 testów offline: PASS, w tym filtry/stronicowanie API i reguły publikacji.
- Testy przeglądarki desktop 1440×1000 oraz mobile 390×844 i 320×844: PASS.
- Rzeczywiste ELI dla frazy „ustawa”, DU, rok publikacji 2025: strony 1–20
  oraz 21–40 z 220 wyników w chwili sprawdzenia. Parametry potwierdzone w żądaniach.
- Dodanie dwóch aktów z różnych stron, eksport z tytułami/ELI/oficjalnymi URL,
  usunięcie pozycji i wyczyszczenie stanu po odświeżeniu: PASS.
- Wejście przez kartę tematyczną do formularza z wybraną dziedziną: PASS.
- Syntetyczny opis sprawy nie wystąpił w żądaniach sieciowych; brak błędów JS
  i poziomego przepełnienia widoku na obu szerokościach mobilnych.
- Sprawdzono wygląd całej strony, sekcji BASAL i widoku mobilnego.
- Kontrola bieżących śledzonych plików pod kątem zdefiniowanych kategorii
  prywatnych i formatów poświadczeń: PASS. Dodatkowy przegląd lokalnie dostępnych
  historycznych blobów nie wykrył tych formatów poświadczeń. Nie jest to pełny audyt.

Usunięto dodatkowy workflow publikujący katalog repozytorium w całości.
Jedynym procesem publikacji jest `Publish website` z wynikiem buildera `_site`.
Przed publikacją działa teraz również kontrola publicznych plików.
Instrukcje agenta usunięto z bieżącej wersji w poprzedniej zmianie; historii Git
nie przepisywano. Nie wykryto w nich poświadczeń wskazaną kontrolą wzorców.

Sekcja BASAL opisuje rolę i autorstwo technologii na podstawie źródeł autora.
Nie jest dowodem uruchomienia modelu. VPS i jego prace wdrożeniowe nie były
w tej zmianie obsługiwane z tego środowiska.

## Przygotowanie połączenia Pages z API — 2026-10-03

- PR #4: sprawdzono zmiany, 32 testy lokalne i CI; scalono do `main`.
- Po dodaniu opcjonalnego adresu API: 39 testów offline — PASS. Obejmują
  domyślne wyłączenie połączenia, odrzucenie niewłaściwych adresów, preflight,
  dokładny origin, błędne nagłówki/metody i dostępność błędów dla przeglądarki.
- Chrome przez Playwright: rzeczywiste żądania między dwoma lokalnymi serwerami
  HTTPS o różnych originach; ręczny wywiad, fallback przy wyłączonym modelu,
  awaria API zachowująca opis w formularzu — PASS. Test używał syntetycznych
  opisów oraz lokalnej konfiguracji QA, bez modelu właściciela.
- Strona o niedozwolonym originie nie odczytała stanu; formularz nie wysłał
  opisu. W domyślnym trybie statycznym opis również nie opuścił przeglądarki.
- Brak błędów JS i poziomego przepełnienia przy szerokości 320 px.
- HTTPS w QA używał tymczasowego certyfikatu własnego; pominięcie jego weryfikacji
  dotyczyło tylko testowej przeglądarki. Kod produktu wymaga HTTPS. Produkcyjną
  domenę i certyfikat należy potwierdzić z zewnątrz bez tego pominięcia.

Nie włączono publicznego połączenia bez potwierdzonego adresu API. Nie wykonano
tutaj testu VPS ani jego rzeczywistego modelu; wynik lokalnego CORS nie zastępuje
testu całej ścieżki przez produkcyjny reverse proxy. Raporty z serwera pozostają
poza publicznym repozytorium.
