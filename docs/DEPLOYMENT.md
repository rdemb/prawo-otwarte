# Wdrożenie na VPS

Ta instrukcja jest ogólna. Nie zawiera prywatnego raportu hosta ani instrukcji
usuwania cudzych projektów. Nie zakłada dostępu do konkretnego serwera.

## 1. Inwentaryzacja

Sprawdź obowiązujące zasady administratora hosta, zajęte porty, obecne usługi, wolne
RAM/dysk, rzeczywisty CPU, system, zaporę i lokalizację hosta. Zachowaj SSH,
Tailscale, konfigurację Codexa oraz konfiguracje innych usług. Instalacja aplikacji
nie wymaga zmiany portu SSH ani sieci administracyjnej.

## 2. Konto i katalogi

Przykładowa konfiguracja:

- konto systemowe `prawo`, bez interaktywnego logowania;
- kod `/srv/prawo-otwarte`, zablokowany do zapisu dla procesu aplikacji;
- dane `/var/lib/prawo-otwarte`, zapisywalne wyłącznie przez `prawo` i administratora;
- konfiguracja `/etc/prawo-otwarte.env`, uprawnienia `0640`, root:root (systemd czyta ją przed zmianą użytkownika);
- osobna instalacja BASAL-a i osobna usługa z własnymi limitami zasobów;
- lokalne API `127.0.0.1:8080`, BASAL wyłącznie na loopback.

Jeżeli te ścieżki lub konto już istnieją, sprawdź właściciela i przeznaczenie.
Nie zmieniaj właścicieli ani konfiguracji istniejących usług w ciemno.

Po przygotowaniu katalogu i konta przez administratora:

```bash
cd /srv/prawo-otwarte
python3 -m venv .venv
.venv/bin/pip install -r requirements-server.txt
.venv/bin/python -m unittest discover -s tests -v
```

Python uruchamia aplikację bez instalacji jej pakietu, z katalogu roboczego.
Nie instaluj zależności aplikacji do środowiska modelu. `.env.example` nie jest
automatycznie ładowany przez Python: systemd używa `EnvironmentFile`.

Skopiuj i sprawdź `deploy/prawo-otwarte.service`. Najpierw uruchom lokalnie,
sprawdź `/healthz`, `/api/status`, wyszukiwanie i obsługę niedostępnego BASAL-a.
Włączenie autostartu dotyczy wyłącznie nowej usługi.

## 3. BASAL już istniejący na hoście

Nie aktualizuj ani nie pobieraj ponownie modelu na podstawie tej instrukcji.
Ustal rzeczywisty model, rewizję, runtime, zależności, pliki kalibracji, tokenizator,
wagę, konfigurację i ścieżki. Standardowy Python venv może zawierać absolutne
ścieżki, a editable installs oraz symlinki mogą wskazywać na poprzedni projekt.

Odtwórz runtime w nowej lokalizacji z zapisanej listy wersji lub zachowaj sprawdzony
kontener. Sprawdź importy, pełny kontrakt API i odpowiedzi na identyczne neutralne
pytania przed i po migracji. BASAL 1.5B jest rozsądnym kandydatem do pomiaru na CPU,
ale ostateczny wybór ma wynikać z istniejącej instalacji i jej testu.

Ta aplikacja wysyła dziewięć opcji `choice` i oczekuje rozkładu dla wszystkich
opcji. Test pilota musi sprawdzić zgodność rzeczywistego endpointu, nie sam port.
Pełny opis sprawy pozostaje na hoście, jeżeli BASAL działa na loopback jak wymaga
konfiguracja. Domyślnie `PRAWO_BASAL_ENABLED=0`.

## 4. Import i odtwarzanie

Uruchamiaj importer jako `prawo`, z `PRAWO_DATA_DIR=/var/lib/prawo-otwarte`.
Rozpocznij od `bootstrap --texts`; następnie importuj metadane DU/MP rocznikami
w ograniczonych partiach. Najpierw zmierz skutki importu i obciążenie API.
Nie twórz harmonogramu bez checkpointów, raportowania błędów i planu rekonsyliacji.

Kopię aktywnej bazy wykonuj przez SQLite backup API (`sqlite3.Connection.backup`),
nie przez kopiowanie samego pliku bazy z pominięciem WAL. Do kompletu należą
snapshoty, konfiguracja i wersja kodu. Trzymaj zaszyfrowaną kopię poza VPS-em.
Backup na tym samym dysku zabezpiecza przed pomyłką podczas migracji, nie awarią hosta.

## 5. Dostęp publiczny

Statyczną stronę publikuje workflow GitHub Pages opisany w README.
Bez konfiguracji API wyszukuje bezpośrednio w ELI i tworzy notatkę w przeglądarce.
Adapter obsługuje także backend HTTPS: adres ustala operator podczas budowania,
nigdy przez parametr URL, localStorage ani pole użytkownika.

Kolejność podłączenia:

1. Wdróż aktualne `main` na VPS z zachowaniem własnego środowiska, danych i
   ustawień BASAL-a. Wykonaj kopię oraz testy przed restartem aplikacji.
2. Skonfiguruj reverse proxy HTTPS do `127.0.0.1:8080`: z posiadaną domeną i DNS
   albo publicznym adresem IP oraz zaufanym certyfikatem opisanym poniżej.
   Potwierdź prawidłowy certyfikat i `/api/status` z maszyny poza VPS.
3. W prywatnym pliku środowiska VPS ustaw
   `PRAWO_ALLOWED_ORIGINS=https://rdemb.github.io` i zrestartuj aplikację.
   Origin to schemat i host, **bez** `/prawo-otwarte/` i końcowego ukośnika.
   Dla innych instalacji podaj dokładne adresy HTTPS, oddzielone przecinkiem.
   Nie używaj `*`. Inne strony tego samego konta GitHub mają ten sam origin;
   CORS nie rozróżnia ścieżek i nie zastępuje uwierzytelniania ani limitowania.
4. Sprawdź preflight `OPTIONS /api/intake` z tym origin, metodą `POST` i nagłówkiem
   `Content-Type`. Oczekiwane: 204 i dokładny `Access-Control-Allow-Origin`.
   Obcy origin ma otrzymać 403 bez tego nagłówka. Potwierdź również nagłówki
   CORS dla odpowiedzi 400, 429 i 503, aby przeglądarka mogła pokazać błąd.
5. Dopiero po testach dodaj w GitHub: Settings → Secrets and variables → Actions
   → Variables → **Repository variable** `PRAWO_API_BASE_URL`, np.
   `https://api.twoja-domena.pl` (zastąp własnym adresem). To publiczny adres,
   nie hasło ani klucz. Użyj domyślnego portu HTTPS i nie dopisuj `/api`.
6. Uruchom Actions → Publish website → Run workflow na `main`. Zmiana samej
   zmiennej nie przebudowuje istniejącej strony. Builder zapisze adres w
   publicznym `pages-data.json`; brak zmiennej zachowuje tryb samodzielny.
7. Na publicznej stronie sprawdź status, lokalne wyszukiwanie, ręczny wywiad,
   pojedyncze rzeczywiste wywołanie BASAL-a, jego niepewność/zajętość oraz awarię
   API. Potwierdź komunikaty o wysyłaniu opisu na serwer, widok telefonu i brak
   zapisu syntetycznego opisu w bazie i logach. Stan „klasyfikacja włączona” jest
   konfiguracją aplikacji, a nie ciągłym testem zdrowia modelu.

Wycofanie: usuń zmienną `PRAWO_API_BASE_URL` i ponownie uruchom publikację.
Nowo wczytana strona wróci do samodzielnego ELI i lokalnej notatki; otwarte karty
wymagają odświeżenia. Nie usuwaj przy tym bazy ani modelu. Gdy odczyt stanu
skonfigurowanego API się nie powiedzie, formularz wstrzymuje wysłanie opisu.
Nie przełącza się po cichu na inny serwer i nie ponawia automatycznie żądania.

Budowanie ręczne z adresem API:
`python -m scripts.build_pages --output _site --api-base-url https://api.twoja-domena.pl`.
Bez tej opcji i zmiennej środowiskowej `PRAWO_API_BASE_URL` pozostaje tryb
samodzielny. Katalog wyjściowy musi być pusty; publikuje się wyłącznie siedem
dozwolonych zasobów, nigdy repozytorium w całości.

`deploy/Caddyfile.example` jest szablonem wariantu z domeną. Zastąp `prawo.example.org` posiadaną
domeną, sprawdź DNS, istniejący reverse proxy i konflikt portów 80/443. Nie używaj
przykładowej domeny jako rzeczywistej konfiguracji. Potwierdź HTTPS i trasowanie
z zewnętrznej maszyny. Brak domeny nie wymusza rezygnacji z publicznego HTTPS;
alternatywą jest certyfikat publicznego IP, nie certyfikat samopodpisany.

### HTTPS bez własnej domeny

Od stycznia 2026 Let’s Encrypt wydaje publicznie zaufane certyfikaty adresów IP.
Mają ważność 160 godzin, więc wymagają sprawdzonego automatycznego odnawiania.
Builder przyjmuje także `https://PUBLICZNY_IP` (IPv6 w nawiasach kwadratowych),
na porcie 443. Odrzuca m.in. loopback, sieci prywatne, link-local, CGNAT,
multicast, adresy zarezerwowane i niejednoznaczne skróty IPv4. Walidacja adresu
nie potwierdza własności hosta, dostępności ani poprawności jego certyfikatu.

Operator musi potwierdzić, że adres nadal jest przypisany do jego VPS.
Nie wpisuj adresów z testów jako docelowego serwera. Zmiana IP wymaga nowego
certyfikatu i ponownej publikacji Pages z aktualnym adresem.

Przykładowa ścieżka wdrożenia to Certbot w trybie `certonly --webroot`
(obsługa IP w webroot wymaga wersji co najmniej 5.4), profil `shortlived`
i parametr `--ip-address`. Publiczny port 80 serwuje wyłącznie katalog
`/.well-known/acme-challenge/` oraz przekierowanie do HTTPS; nie udostępnia API
po HTTP. Najpierw sprawdź ACME staging, potem uzyskaj certyfikat produkcyjny.
Nginx lub Caddy musi jawnie wczytywać uzyskaną parę certyfikat/klucz.
Nie zakładaj, że domyślna konfiguracja Caddy dla IP uzyska zaufany certyfikat.

Zweryfikuj timer odnowienia, test `certbot renew --dry-run` i deploy hook,
który po odnowieniu waliduje konfigurację i przeładowuje proxy. Przy Caddy
potrzebne jest ponowne wczytanie certyfikatu również wtedy, gdy tekst konfiguracji
się nie zmienił. Klucz pozostaje prywatny. Monitoruj datę certyfikatu faktycznie
serwowanego klientom. Poświadczenia, klucze i lokalne adresy administracyjne
nie trafiają do repozytorium.

Po uzyskaniu produkcyjnego TLS ustaw `PRAWO_API_BASE_URL` na origin HTTPS tego IP.
`PRAWO_ALLOWED_ORIGINS=https://rdemb.github.io` pozostaje bez zmian. Przed
aktywacją sprawdź całą ścieżkę z publicznej strony, bez pomijania kontroli TLS.

Źródła: [dostępność i czas ważności certyfikatów IP](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability),
[Certbot i certyfikaty IP](https://letsencrypt.org/2026/03/11/shorter-certs-certbot),
[odnawianie Certbot](https://eff-certbot.readthedocs.io/en/stable/using.html#renewing-certificates),
[własne certyfikaty w Caddy](https://caddyserver.com/docs/caddyfile/directives/tls).

Nie wystawiaj portu modelu ani plików danych do internetu. Nie włączaj access logów
z pełną treścią żądań ani tracingu zbierającego opis sprawy. Konfigurację logów
reverse proxy należy zweryfikować osobno; własności aplikacji nie dowodzą
własności wszystkich warstw infrastruktury.

Gunicorn nie zastępuje reverse proxy. Limity zapytań i zasobów w szablonie są
ustawieniami pilota, nie gwarancją obsługi określonej liczby osób. Sprawdź timeouty,
koszt najdłuższego opisu, wzrost bazy, kolejkę i zachowanie przy restarcie modelu.
Za reverse proxy aplikacja widzi wspólny adres połączenia: limit 30/min może być
wspólny dla wszystkich odwiedzających. Nie ufa nagłówkowi `X-Forwarded-For`
dostarczonemu przez klienta. Przed zwiększeniem ruchu wprowadź limitowanie na
zaufanym proxy i wykonaj pomiary; nie podnoś limitów tylko po to, by ominąć test.

Dokumentacja: [zmienne GitHub Actions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-variables),
[HTTPS w Caddy](https://caddyserver.com/docs/quick-starts/https),
[CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS).

### Budżet czasu klasyfikacji na CPU

`PRAWO_BASAL_TIMEOUT` pozostaje domyślnie równy 8 sekund; po pomiarze lokalnego
modelu można ustawić dodatnią wartość do 30 sekund. Przeglądarka czeka na wywiad
do 40 sekund, pozostałe żądania do 25 sekund. Szablon Gunicorn ma timeout oraz
graceful timeout 60 sekund. Timeout Gunicorna nadzoruje worker i nie zastępuje
limitu wywołania modelu. Użytkownik widzi informację o oczekiwaniu i zachowuje
możliwość samodzielnego wyboru dziedziny przy błędzie klasyfikacji.

Serwer BASAL musi osobno ograniczać długość wejścia i liczbę przyjętych żądań.
Po rozłączeniu klienta nie wolno zwalniać jego miejsca przed zakończeniem
rzeczywistej inferencji. Kolejne żądanie powinno szybko otrzymać informację
o zajętości zamiast trafiać do nieograniczonej kolejki. Semafor aplikacji sam
nie zapewnia tej własności procesu modelu. Sprawdź ją na rzeczywistym runtime.

## 6. Aktualizacja i rollback

Zapisz obecny SHA, wykonaj backup, pobierz zatwierdzony commit fast-forward,
uruchom testy, a następnie restartuj wyłącznie `prawo-otwarte.service`.
W razie błędu wróć do wcześniejszego wydania i sprawdzonej kopii danych. Nie używaj
`git reset --hard` do usuwania nieznanych lokalnych zmian. Zmiany schematu bazy
w kolejnych wersjach wymagają jawnych migracji i planu cofnięcia.
