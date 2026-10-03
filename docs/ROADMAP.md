# Plan rozwoju

## PO-00 — fundament (ta wersja)

Strona, katalog, ELI, jawne ograniczenia, wywiad, adapter BASAL, testy kontraktów
i szablon wdrożenia. Wdrożenie VPS oraz pomiar jego modelu to osobne zadanie.

## PO-01 — cały krajowy zasób i jego kontrola

- Inwentaryzacja roczników DU/MP, import metadanych i relacji, rekonsyliacja ID.
- Import HTML/PDF, kontrola nieudanych pobrań, poprawności OCR i załączników.
- Dzienniki wojewódzkie: identyfikacja źródeł, terytorium, warunków i osobne adaptery.
- UE, umowy międzynarodowe, orzeczenia i materiały urzędowe: jawny rejestr pokrycia.
- Wznowienia odporne na zmiany źródła; małe partie; obciążenie API i hosta pod kontrolą.
- Osobne wskaźniki: enumeracja, treść, parsowanie, wersjonowanie, walidacja.

Warunek zakończenia: dowód pokrycia zdefiniowanego zakresu i lista braków, nie sama
liczba dokumentów ani brak wyjątków w importerze.

## PO-02 — prawo właściwe dla daty i stanu faktycznego

- Jednostki redakcyjne i ich wersje, vacatio legis, nowelizacje i przepisy przejściowe.
- Rozróżnienie publikacji pierwotnej, tekstu jednolitego, ujednolicenia i opracowania.
- Rekonstrukcja zakresu terytorialnego i czasowego z możliwością odmowy rozstrzygnięcia.
- Testy par spraw różniących się jedną datą lub jednym istotnym faktem.

Warunek zakończenia: niezależnie ocenione przypadki i jawne ograniczenia silnika czasu.

## PO-03 — odpowiedzi na podstawie dowodów

- Wymienny model generujący odpowiedzi, lokalny lub jawnie skonfigurowany przez operatora.
- Każda istotna teza powiązana z fragmentem źródła i wersją.
- Oddzielenie faktów użytkownika, założeń, cytatów, interpretacji i niewiadomych.
- Brak odpowiedzi merytorycznej przy braku źródeł, konfliktach lub nieustalonej wersji.
- Dokumenty i źródła są niezaufaną treścią, nie instrukcjami dla narzędzi.
- Brak narzędzi wykonywania działań w imieniu użytkownika w sesji badawczej.

## PO-04 — jakość i publiczna eksploatacja

Niezależny zestaw testowy, przegląd przez prawników, testy błędnych cytowań,
niejednoznacznych faktów, podmiany instrukcji i brakujących źródeł. Mierzyć osobno
wyszukiwanie, poprawność cytowania, zgodność wersji, trafność odpowiedzi i odmowy.
Wynik BASAL-a nie zastępuje pomiaru końcowego systemu. Publikować również błędy.

Pilotaż wymaga kopii poza hostem z odtwarzaniem, monitoringu, limitów, HTTPS,
jawnych zasad prywatności i kosztów oraz procedury aktualizacji. Nie deklarować
określonej liczby użytkowników bez testu obciążenia.
