# Źródła, pochodzenie i zakres

Zweryfikowano dokumentację API 2026-10-03:

- [ELI API — dokumentacja Kancelarii Sejmu](https://api.sejm.gov.pl/eli_pl.html)
- [Schemat OpenAPI](https://api.sejm.gov.pl/eli/openapi/)
- [ELI i postacie dokumentów](https://eli.gov.pl/)
- [BASAL: kod, protokół, licencja i ograniczenia](https://github.com/rkinas/basal)
- [Karta modelu BASAL 1.5B](https://huggingface.co/Remek/basal-1.0-1.5B)
- [Karta modelu BASAL 4.5B](https://huggingface.co/Remek/basal-1.0-4.5B)

## Pokrycie

Rejestr `prawo/config/sources.json` jawnie oddziela adaptery gotowe, planowane
i zwykłe odnośniki. `GET /api/status` zwraca liczbę faktycznie zaimportowanych
metadanych i tekstów, zamiast marketingowej deklaracji „całe prawo”.

Publiczny katalog może wyszukiwać tytuły przez API Sejmu bez pełnego lokalnego
importu. Wyniki nie są automatycznie zapisywane. Pełnotekstowe wyszukiwanie lokalne
obejmuje zaimportowane HTML i ekstrakty PDF. Importer `import-core --texts` dobiera
powiązane publikacje jednolite dla 15 podstawowych aktów. Odpowiedzi korzystają
wyłącznie z wybranych PDF, nigdy z pierwotnego HTML. Skany i OCR nie są obsługiwane.
[Reguły wyboru publikacji i ograniczenia ekstrakcji](ANSWERS.md).

## Wersje i zmiany

Należy zachować osobno datę publikacji, wejścia w życie, aktualizacji metadanych,
pobrania i skuteczności właściwej jednostki redakcyjnej. HTML z endpointu
`text.html` nie jest automatycznie dowodem brzmienia na dzień zdarzenia.
Źródłowe relacje między aktami znajdują się w metadanych; 0.1 nie wykonuje jeszcze
pełnego rozstrzygania relacji, nowelizacji i przepisów przejściowych.

`changeDate` jest sygnałem do odświeżenia treści, a nie kompletnym detektorem zmian.
Docelowo wymagane są okresowa rekonsyliacja i porównywanie hashy tekstów również
przy niezmienionych metadanych. Wznowienie stronicowania po offsecie może pomijać
lub powtarzać pozycje, gdy zmienia się źródło. Nie jest gwarancją kompletności.

## Warunki ponownego wykorzystania

Wagi nie są commitowane. Należy zachować ich oryginalne LICENSE/NOTICE, model card,
tokenizer, rewizję i pliki kalibracji. Nie kopiować płatnych komentarzy, baz ani
opracowań bez sprawdzenia warunków. Oficjalna publikacja aktu i cudze opracowanie
tego aktu to różne zasoby. Nie przenosić licencji Apache-2.0 na cały korpus.
