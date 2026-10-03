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

Statyczną stronę publikuje osobny workflow GitHub Pages opisany w README.
Ta wersja wyszukuje bezpośrednio w ELI i tworzy notatkę w przeglądarce.
Nie jest jeszcze połączona z backendem VPS. Podłączenie go wymaga adresu HTTPS,
świadomej konfiguracji zaufanego origin, limitów oraz zmiany adaptera strony;
nie wystarczy wstawić niezabezpieczonego adresu IP do frontendu.

`deploy/Caddyfile.example` jest szablonem. Zastąp `prawo.example.org` posiadaną
domeną, sprawdź DNS, istniejący reverse proxy i konflikt portów 80/443. Nie używaj
przykładowej domeny jako rzeczywistej konfiguracji. Potwierdź HTTPS i trasowanie
z zewnętrznej maszyny. Bez domeny pozostaw działający podgląd lokalny/Tailscale.

Nie wystawiaj portu modelu ani plików danych do internetu. Nie włączaj access logów
z pełną treścią żądań ani tracingu zbierającego opis sprawy. Konfigurację logów
reverse proxy należy zweryfikować osobno; własności aplikacji nie dowodzą
własności wszystkich warstw infrastruktury.

Gunicorn nie zastępuje reverse proxy. Limity zapytań i zasobów w szablonie są
ustawieniami pilota, nie gwarancją obsługi określonej liczby osób. Sprawdź timeouty,
koszt najdłuższego opisu, wzrost bazy, kolejkę i zachowanie przy restarcie modelu.

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
