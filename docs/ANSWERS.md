# Odpowiedzi, źródła i kontrola BASAL-a

Nowy kod udostępnia `POST /api/answer`. Wdrożenie interfejsu Pages nie aktualizuje
serwera VPS. Interfejs odczytuje `source_answers` i `generative_answers` z API;
starsza wersja API pozostaje obsługiwana i pokazuje potrzebę aktualizacji.

## Dwa tryby

1. **Fragmenty:** wyszukiwanie w wybranych publikacjach źródłowych, bez generatora.
   Wynik zawiera tekst, ELI, datę pobrania, datę stanu prawnego publikacji (jeśli
   podano) i SHA-256 wyodrębnionego tekstu. Nie jest wygenerowaną poradą.
2. **Objaśnienie:** opcjonalny lokalny model generatywny, np. Bielik, otrzymuje
   pytanie i maksymalnie pięć fragmentów. Zwraca najwyżej trzy twierdzenia z
   dokładnym cytatem i identyfikatorem dostarczonego źródła. Aplikacja sprawdza
   istnienie źródła i cytatu. BASAL osobno porównuje objaśnienia, cytaty i ich
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
różnych dopasowanych terminów oraz kolejności fraz w początku fragmentu. To początkowa metoda leksykalna, bez gwarancji
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
