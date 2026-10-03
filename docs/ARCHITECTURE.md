# Architektura 0.1

## Granice komponentów

1. **Przeglądarka** — statyczny HTML/CSS/JS, bez zewnętrznych fontów, reklam,
   telemetryki i trwałego magazynowania opisu sprawy. Notatka jest eksportowana
   lokalnie po kliknięciu użytkownika.
2. **WSGI API** — wyszukiwanie, odczyt katalogu i wywiad. Żadnych operacji shell,
   uploadu dokumentów, kasowania danych, administrowania serwerem ani importu z sieci.
3. **ELI adapter** — jedyny zewnętrzny endpoint aplikacji. Publiczna wyszukiwarka
   przesyła jawnie wpisaną frazę tytułową, nie opis sprawy. Nie przyjmuje dowolnych URL.
4. **Katalog SQLite FTS5** — źródła, metadane, treść z HTML i checkpointy importu.
   Snapshoty są adresowane przez SHA-256 i nie są nadpisywane.
5. **Lokalny BASAL** — nieufny klasyfikator; jeden równoległy request na proces,
   limit długości opisu, timeout i walidacja kategorii oraz rozkładu odpowiedzi.
6. **CLI importera** — świadomie uruchamiana praca administratora, limit stron,
   opóźnienie, wznowienie i jawne błędy. Bez automatycznego masowego pobierania.

Warstwa generowania opinii prawnych nie istnieje w 0.1. Jej włączenie będzie
osobnym etapem, z odrębnymi testami, kosztem i oceną jakości prawnej.

## Trzy rodzaje czasu

- `fetched_at`: kiedy nasz system otrzymał metadane;
- `source_changed_at`: `changeDate` deklarowany przez źródło;
- data skuteczności normy w danym stanie faktycznym: **nieustalona w 0.1**.

Nie używamy warunku `entryIntoForce <= event_date` jako dowodu obowiązywania.
Trzeba uwzględnić jednostki redakcyjne, uchylenia, nowelizacje, przepisy przejściowe,
terytorium, rodzaj sprawy i daty relewantnych zdarzeń. Do czasu implementacji tej
warstwy `temporal_verified` jest zawsze `false`.

## Znaczenie snapshotów

`metadata` przechowuje oryginalne bajty odpowiedzi szczegółów aktu; `metadata_item`
to kanonicznie zserializowany element odpowiedzi listy z URL tej listy. `html`
przechowuje oryginalne bajty pobranego HTML. Osobna treść służy do wyszukiwania
i wyświetlania jako zwykły tekst. Hash dowodzi tożsamości kopii, nie jej mocy prawnej.

Źródłowy HTML może odzwierciedlać określoną wersję bez pełnej historii. Nie
nazywamy go automatycznie tekstem aktualnym ani urzędowym tekstem jednolitym.
Oryginalne metadane i relacje nie są zastępowane streszczeniem modelu.

## API

| Endpoint | Zachowanie |
|---|---|
| `GET /healthz` | Stan procesu; nie test jakości prawa ani dostępności modelu |
| `GET /api/status` | Faktyczne liczniki, zakres źródeł, konfiguracja integracji |
| `POST /api/search` | `{query, mode: eli|local}`; do 20 wyników |
| `GET /api/act?eli=DU/1997/483` | Lokalna kopia, metadane i pochodzenie |
| `POST /api/intake` | `{description,event_date,domain}`; pytania i kierunek szukania |

`basal.enabled` informuje o konfiguracji. `verified_live=false` nie jest zastępowane
`true` na podstawie samego URL: model testuje się osobno. Włączenie modelu i jego
sprawne uruchomienie nie oznaczają zweryfikowanej skuteczności prawnej.

## Granice wdrożenia

Jeden proces Gunicorn, cztery wątki, limiter w pamięci. Limiter nie jest globalnym
limiterem rozproszonej instalacji. Za reverse proxy adres źródłowy może być wspólny;
w 0.1 oznacza to konserwatywny wspólny limit. Nie ufamy dowolnemu X-Forwarded-For.
Przy skalowaniu trzeba wprowadzić zaufany proxy i wspólny limiter.

SQLite wystarcza do pilota i importu sekwencyjnego. Wielu zapisujących importerów
oraz duży ruch wymagają testów i ewentualnego przeniesienia katalogu do PostgreSQL.
Przed rozszerzaniem stosu mierzymy p50/p95, pamięć RSS, IO i czas importu.
