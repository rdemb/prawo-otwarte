# Zasób prawa i jego aktualizowanie

Celem jest szerokie pokrycie polskiego prawa. Obecna baza nie jest kompletna.
Każda instalacja publikuje własne liczniki w `/api/status` i na stronie.

| Licznik | Co oznacza | Czego nie potwierdza |
| --- | --- | --- |
| Metadane | Identyfikatory, tytuły i dane z katalogu ELI | Dostępności treści przepisu |
| Teksty | Pobrane HTML lub tekst wyodrębniony z PDF | Aktualności na datę sprawy |
| Publikacje w odpowiedziach | Wybrane reprezentacje aktów z zaimportowanym tekstem | Kompletności wszystkich aktów |
| Fragmenty | Jednostki tekstu w indeksie | Trafności wyszukiwania ani interpretacji |

## Pierwsza enumeracja całego katalogu DU i MP

Lista roczników pochodzi z oficjalnego endpointu
[`/eli/acts`](https://api.sejm.gov.pl/eli/acts).
Polecenia korzystają ze skonfigurowanego `PRAWO_DATA_DIR`; uruchamiaj je jako
użytkownik aplikacji, z dostępem do sieci przez `PRAWO_ALLOW_ELI=true`.

```sh
python -m prawo.cli catalog-plan
python -m prawo.cli sync-catalog --max-pages 10 --pause 1
python -m prawo.cli status
```

Ponowne `sync-catalog` wznawia pracę z ostatniego zapisanego offsetu i przechodzi
przez kolejne roczniki. Budżet stron dotyczy całego wywołania (do 100 rekordów
na stronę); opcjonalny `--publisher DU` lub `--publisher MP` ogranicza zakres.
Uruchamiaj jeden importer naraz. Harmonogram powinien mieć blokadę wykluczającą
równoległe importy, ograniczenia zasobów i przerwę między partiami.

Import jest idempotentny według identyfikatora ELI. Sprawdza zakres, powtórzenia
na stronie oraz liczbę unikalnych lokalnych rekordów po zakończeniu rocznika.
Rozbieżność zatrzymuje partię i wymaga rekonsyliacji identyfikatorów z ELI;
sam offset nie potwierdza kompletności. Nie usuwaj aktów automatycznie.

**To pierwsza enumeracja metadanych, nie usługa aktualizacji ani import tekstów.**
Zakończone roczniki są pomijane. Nowe publikacje i zmiany w starych aktach wymagają
osobnej synchronizacji zmian oraz okresowej ponownej enumeracji. Starsze punkty
wznowienia utworzone przez `sync` należy również zweryfikować. Docelowy mechanizm
powinien korzystać z dziennika zmian ELI, zachowywać poprzednie wersje i rejestrować
braki, wycofania oraz nieudane pobrania. Import nie rekonstruuje prawa na datę sprawy.

## Treści do odpowiedzi

`python -m prawo.cli import-core --texts` obsługuje wybrany zestaw 15 aktów.
Sprawdza powiązanie z najnowszą wskazaną publikacją tekstu jednolitego; wymaga
`pdftotext`. Niedostępność nowego PDF nie może prowadzić do cichego użycia starego
brzmienia. `import-act --text` pobiera dostępny HTML do katalogu, ale samo pobranie
nie kwalifikuje tekstu jako bezpiecznej podstawy odpowiedzi.

Dalsze rozszerzenie wymaga selekcji reprezentacji, zachowania dat i relacji zmian,
obsługi paragrafów oraz skanów/OCR. Kopie dokumentów, bazy i indeksy pozostają
poza publicznym repozytorium; kod importerów i jawne definicje pokrycia są publiczne.

## Pozostałe warstwy

DU i MP nie obejmują całego docelowego zasobu. Odrębnych adapterów i kontroli
wymagają dzienniki urzędowe województw i pozostałych organów, źródła UE oraz
orzecznictwo. Wyroki i materiały objaśniające muszą być oznaczone oddzielnie od
przepisów. Projekt nie przedstawia ich jako zaimportowanych na podstawie samych linków.

## Jakość odpowiedzi

Oceniamy osobno wyszukanie właściwego przepisu, dosłowność cytatu, zachowanie
warunków i wyjątków, dobór wersji czasowej i poprawność objaśnienia. Wynik BASAL-a
nie jest prawdopodobieństwem poprawności prawnej. Testy techniczne i trafienie
właściwego artykułu nie wystarczają do zatwierdzenia objaśnienia; potrzebna jest
ocena merytoryczna na odłożonym zbiorze przypadków.
