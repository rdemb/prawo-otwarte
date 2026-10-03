# Odpowiedzi, źródła i kontrola BASAL-a

Nowy kod udostępnia `POST /api/answer`. Wdrożenie interfejsu Pages nie aktualizuje
serwera VPS. Interfejs odczytuje `source_answers` i `generative_answers` z API;
starsza wersja API pozostaje obsługiwana i pokazuje potrzebę aktualizacji.

## Dwa tryby

1. **Fragmenty:** wyszukiwanie w wybranych publikacjach źródłowych, bez generatora.
   Wynik zawiera tekst, ELI, datę pobrania, datę stanu prawnego publikacji (jeśli
   podano) i SHA-256 wyodrębnionego tekstu. Nie jest wygenerowaną poradą.
2. **Objaśnienie:** opcjonalny lokalny model generatywny, np. Bielik, otrzymuje
   pytanie i maksymalnie pięć fragmentów. Zwraca najwyżej jedno krótkie twierdzenie z
   dokładnym cytatem i identyfikatorem dostarczonego źródła. Aplikacja sprawdza
   istnienie źródła i cytatu. BASAL najpierw porównuje objaśnienie z samym cytatem, następnie sprawdza pełny
   kontekst, wybierając `supported`, `unsupported` albo `unclear`.

Objaśnienia są wyświetlane tylko po pozytywnej decyzji BASAL-a osiągającej próg.
Brak potwierdzenia, awaria lub zajętość zachowują widok fragmentów. Brak źródeł
jest jawny i nie wywołuje generatora. Klasyfikacja dziedziny nie jest bramką
odpowiedzi. Użytkownik może zadać pytanie bez niej.

**BASAL nie generuje tekstu.** Generator i model decyzyjny mają odrębne role.
Kontrola cytatów i decyzja modelu nie stanowią eksperckiej walidacji prawnej.
Nie deklarujemy zmierzonej poprawności prawnej ani skalibrowanej pewności.

## Dobór źródeł

`python -m prawo import-core --texts` odświeża 15 aktów z jawnego katalogu.
Dla każdego ustala najnowszą publikację wskazaną relacją ELI
`Inf. o tekście jednolitym` (rok i pozycja), sprawdza relację zwrotną
`Tekst jednolity dla aktu` i pobiera PDF typu T, ewentualnie O. Gdy nie ma
powiązanej publikacji, dopuszcza wyłącznie tekst ujednolicony U.

Oryginalne HTML mogą zawierać dawne brzmienie. Pozostają w katalogu, ale są
wykluczone z odpowiedzi. Wybrane publikacje i typ reprezentacji są zapisane
oddzielnie. Zmiana metadanych wyłącza nieodświeżony tekst z wyszukiwania.
Nowy, niedostępny PDF nie powoduje powrotu do pierwotnego HTML.

PDF odczytuje systemowy `pdftotext` (pakiet `poppler-utils`). Nie ma OCR.
Skany, błędny format i nieczytelny tekst są odrzucane. Ekstrakcja PDF może
spłaszczać tabele, indeksy i przypisy; oznaczenia jednostek wymagają kontroli
w oryginalnej publikacji. Snapshot PDF i ekstrakt są różnymi reprezentacjami
z osobnymi sumami SHA-256. Sam tekst jednolity nie uwzględnia automatycznie
późniejszych zmian i nie rekonstruuje prawa na podaną datę.

W publikacji z załącznikiem do obwieszczenia indeks fragmentów rozpoczyna się
od tego załącznika. Wstęp obwieszczenia pozostaje w pełnym tekście i snapshotach,
ale nie uczestniczy w tym wyszukiwaniu; zawarte tam przepisy przejściowe trzeba
sprawdzić oddzielnie.

Wyszukiwanie fragmentów używa SQLite FTS5, prefiksów polskich wyrazów i liczby
różnych dopasowanych terminów oraz ograniczonej premii za kolejność fraz w początku fragmentu. To początkowa metoda leksykalna, bez gwarancji
kompletności i trafności. Wyniki mogą pomijać wyjątki lub zawierać nietrafne akty.

## Uruchomienie generatora

Konfiguracja `.env.example` jest domyślnie wyłączona. Wymagany jest lokalny
serwer z `POST /v1/chat/completions`, obsługą `response_format` JSON ze schematem
oraz właściwym szablonem rozmowy modelu. Sprawdzono dokumentację
[llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
i [Bielika 4.5B v3 GGUF](https://huggingface.co/speakleash/Bielik-4.5B-v3.0-Instruct-GGUF).
Rzeczywisty model, rewizję, wariant wag i limity należy ustalić i przetestować
na docelowym hoście. Repozytorium nie pobiera wag ani nie uruchamia nowej usługi.

- API generatora tylko na numerycznym loopback IP, przykładowo 127.0.0.1:8767.
- Wywołania lokalne omijają proxy HTTP. Nie ma zewnętrznego dostawcy inferencji.
- Jedno żądanie generowania na proces aplikacji, do 700 tokenów, bez narzędzi.
- Limit generatora 90 s, kontrola BASAL-a do 30 s, przeglądarka 130 s.
- Gunicorn: jeden worker gthread, timeout/graceful timeout co najmniej 150 s
  dla tej funkcji; sprawdzić również timeout reverse proxy.
- Runtime musi ograniczać rzeczywistą inferencję i kolejkę po rozłączeniu klienta.
  Semafor WSGI nie zastępuje tego zabezpieczenia.
- Przed publicznym włączeniem: pomiary RAM/CPU, pełny kontrakt, cytaty,
  sprzeczne i niedostateczne dowody, brak źródeł, przeciążenie, timeout i rollback.

## Prywatność i pomiary

Pytania i odpowiedzi są przetwarzane w pamięci, bez historii rozmów w bazie.
Pobranie odpowiedzi z pytaniem i źródłami jest jawną czynnością użytkownika.
Eksport pomiarów nie zawiera pytań, odpowiedzi ani cytatów. Przechowuje ostatnie
50 prób w pamięci karty: czas całości, czas lokalnego żądania generatora, tryb,
liczbę źródeł i twierdzeń oraz wynik kontroli BASAL-a. Odświeżenie usuwa pomiary.
Logi infrastruktury i runtime trzeba osobno sprawdzić na VPS.

## Ograniczanie kolejki lokalnego runtime

`deploy/generator_gateway.py` uruchamia dedykowany proces `llama-server` i przyjmuje
wyłącznie ograniczony kontrakt aplikacji na loopback. Jeden aktywny POST zajmuje
miejsce do zakończenia odczytu odpowiedzi, także gdy klient się rozłączy. Następne
żądanie dostaje HTTP 503. Limit obejmuje również liczbę wątków obsługi i czas
odczytu żądania. Gdy połączenie z runtime przekroczy timeout, gateway kończy i
zbiera proces potomny przed zwolnieniem miejsca. Jednostka systemd musi używać
`KillMode=control-group`, aby restart kończył również proces modelu.

Przykładowe uruchomienie po osobnym pobraniu i weryfikacji binarium oraz wag:

```bash
python3 deploy/generator_gateway.py --port 8767 --upstream-port 8768 --timeout 115 --model bielik -- \
  /srv/prawo-generator/llama/llama-server --model /var/lib/prawo-generator/models/model.gguf \
  --alias bielik --host 127.0.0.1 --port 8768 --ctx-size 8192 --parallel 1 \
  --n-predict 700 --threads 6 --threads-batch 6 --cache-ram 0 --cache-reuse 0 \
  --no-webui --no-ui-mcp-proxy --log-disable --timeout 110 --offline
```

Port upstream nie jest publicznym API. Nie udostępniaj żadnego portu modelu przez
proxy. Użyj odrębnego konta, limitów RAM/CPU, dostępu sieciowego tylko do loopback
i wyłączonego zapisu stdout/stderr. Parametry runtime sprawdź dla przypiętej wersji.
Nie nadpisuj szablonu rozmowy z wag obcym szablonem.

Objaśnienie ma cytat 20–350 znaków i jedno zdanie do 300 znaków. Schemat wysyłany
do runtime ogranicza cytaty do dosłownych, krótkich zdań dostarczonych źródeł,
powiązanych z ich identyfikatorami. Nie korygujemy po cichu błędnego cytatu modelu.
Jeżeli nie ma odpowiedniego krótkiego cytatu, model może zwrócić pustą listę.
Generator nadal widzi pięć fragmentów, ale bez pól technicznych niepotrzebnych do redakcji.
Ograniczenie liczby twierdzeń utrzymuje pełny kontekst wybranego fragmentu w
ograniczonym wejściu kontrolera dowodów. Kontrola istnienia cytatu i próg BASAL-a
pozostają obowiązkowe. Nawet poprawny JSON może zostać odrzucony. Przykładowy
proces na CPU nie gwarantuje odpowiedzi dla dowolnego pytania w 90 sekund.

Kontrola dowodów przekazuje BASAL-owi polskie pola „Kontekst źródła”, „Cytat” i
„Twierdzenie do sprawdzenia”. Opcje opisują potwierdzenie, sprzeczność i brak
podstaw; `option_keys=hide` ukrywa techniczne identyfikatory w tekście opcji, nie
zmienia ich w odpowiedzi API. Klasyfikacja dziedziny zachowuje dotychczasowy
kontrakt. Próg 0,80, wagi i kalibracja runtime nie są zmieniane przez aplikację.
Obsługę `option_keys` trzeba potwierdzić na zainstalowanym serwerze BASAL.

Obie kontrole BASAL-a muszą zwrócić supported powyżej progu i dzielą jeden
budżet czasu. Treść z innego miejsca kontekstu nie może zastąpić podstawy
w przypisanym cytacie. Urwane objaśnienia są odrzucane. Podanie daty sprawy
wyłącza generowanie: aplikacja pokazuje źródła i informację, że nie odtworzono
wersji prawa dla tej daty.
