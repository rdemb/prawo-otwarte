# Sprawdzenia projektu

Poniżej zapisano kolejne etapy testów. Ograniczenia wcześniejszych etapów
nie opisują automatycznie aktualnego wdrożenia. Bieżące wyniki CI są w GitHub Actions.

## Publiczne wdrożenie i laboratorium — 2026-10-03

- Publiczna strona jest połączona przez HTTPS z API i BASAL-em.
- Niezależny test TLS, CORS i modelu: [uruchomienie 37118309874](https://github.com/rdemb/prawo-otwarte/actions/runs/37118309874), PASS.
- PR #8: 41 testów Python, 6 testów agregacji i ręczne scenariusze przeglądarkowe, PASS.
- Rzeczywisty model w próbie laboratorium: 4,93 s, brak jednoznacznej klasyfikacji.
  Nie jest to pomiar trafności ani dowód poprawności prawnej.
- Zgłoszony następnie błąd na telefonie odtworzono: nowy HTML razem ze starym
  CSS/JS z cache dawał nieostylowane laboratorium i zero przykładów. Poprzednie
  sprawdzenie w czystej przeglądarce nie wykrywało tego scenariusza.
- Poprawka używa nazw zasobów zależnych od zawartości i automatycznych testów
  przeglądarkowych, uruchamianych również przed publikacją.
- Przegląd 181 lokalnie dostępnych obiektów historycznych nie znalazł formatów
  poświadczeń rozpoznawanych przez kontrolę projektu. To nie pełny audyt.
- Brak eksperckiej walidacji odpowiedzi prawnych, pełnego korpusu i potwierdzonej
  kopii poza VPS pozostaje ograniczeniem projektu.

## Historia: początkowe sprawdzenia wersji 0.1

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

## Opcjonalny adres IP dla API — 2026-10-03

41 testów offline — PASS. Dodano test budowania konfiguracji z publicznym IPv4
i IPv6 oraz odrzucania adresów niepublicznych, multicast, zarezerwowanych,
niejednoznacznych reprezentacji i identyfikatorów interfejsu. Adresy testowe służą
wyłącznie do parsowania; testy nie nawiązują z nimi połączenia. Domyślny tryb
samodzielny Pages pozostaje bez zmian. Nie wystawiono tu certyfikatu dla VPS ani
nie potwierdzono jego publicznego HTTPS; są to czynności wdrożeniowe operatora.

## 2026-10-03 — odpowiedzi, diagnostyka i import PDF

- 60 testów Python: istniejące API, nowe odpowiedzi, ścisłe cytaty, brak źródeł,
  sprzeczny/niepewny BASAL, awaria/zajętość generatora, brak zapisu pytania,
  dobór najnowszej publikacji, relacja zwrotna i wyłączenie pierwotnego HTML.
- 6 przypadków agregacji pomiarów Node oraz 4 scenariusze prawdziwej przeglądarki:
  cache, odzyskanie plików, laboratorium, odpowiedzi ze źródłami, awarie,
  starsze API, prywatny eksport pomiarów, odporność renderowania na HTML,
  szerokości 320/390/768/1440.
- Rzeczywisty import 15 aktów w tymczasowej bazie przez ELI, bez zmian VPS:
  14 powiązanych publikacji jednolitych i PDF ujednolicony Konstytucji;
  15 źródeł dopuszczonych do odpowiedzi, zero nieudanych importów końcowych.
  Wcześniejszy test pierwotnych HTML wykrył historyczne brzmienie; są wyłączone
  z nowej ścieżki odpowiedzi. Naprawiono także negocjację typu PDF w ELI.
- Pełna lokalna ścieżka przeglądarka → API → rzeczywiste PDF dla trzech pytań:
  odstąpienie od umowy internetowej, okres wypowiedzenia i zwrot kaucji.
  To sprawdzenie działania pobierania i wyświetlania, nie ekspercka ocena prawa.
- Nowy generator i trzyopcjowa kontrola dowodów BASAL-a mają testy kontraktu
  z odpowiedziami syntetycznymi. Nie zostały jeszcze uruchomione na VPS.
  Wymagają oddzielnego odbioru rzeczywistego runtime, zasobów i jakości.
- Test repozytorium jest kontrolą wskazanych typów plików/wzorców, nie pełnym
  audytem bezpieczeństwa. Bazy, PDF, raporty i instrukcje agentów pozostają poza Git.

## Lokalny generator i kontrola dowodów

Dodatkowe testy obejmują dokładne cytaty powiązane ze źródłem w schemacie JSON,
próg kontrolera dowodów bez jego obniżania, ranking różnych pojęć przed
powtarzanymi nagłówkami oraz gateway utrzymujący zajętość po rozłączeniu klienta.
Testy gateway uruchamiają prawdziwe gniazda loopback z kontrolowanym upstream;
nie zastępują testu rzeczywistego modelu i limitów na docelowym hoście.

Mała próba kontraktu BASAL nie jest ewaluacją poprawności prawnej. Kontroler
może wskazać błędną opcję z niskim wynikiem; próg ma pozostać aktywny. Wdrożenie
wymaga sprawdzenia zarówno poprawnych objaśnień, jak i sprzeczności, pominiętych
warunków, ataków instrukcjami oraz braku dostępnego modelu.
