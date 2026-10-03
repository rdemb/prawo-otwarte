# BASAL w Prawie Otwartym

Prawo Otwarte jest niezależnym, otwartym projektem rozwijanym w oparciu o BASAL.
Publiczna strona nie wywołuje jeszcze modelu. Istniejący adapter serwerowy
pozostaje oddzielony od wariantu GitHub Pages; uruchomienie całej integracji
wymaga testu na rzeczywistym modelu.

## Autorstwo i pochodzenie

BASAL tworzy Remigiusz Kinas. Według [NOTICE autora](https://github.com/rkinas/basal/blob/main/NOTICE)
modele `basal-1.0-4.5B` i `basal-1.0-1.5B` powstały przez dostrojenie odpowiednio
`speakleash/Bielik-4.5B-v3.0-Instruct` i `speakleash/Bielik-1.5B-v3.0-Instruct`.
Kod silnika oraz modele są udostępniane na Apache-2.0 zgodnie z dokumentacją autora.
Prawo Otwarte nie jest autorem tych modeli ani oficjalnym partnerem ich twórców.
Samo wskazanie technologii nie oznacza rekomendacji aplikacji przez autorów.

## Rola modelu

BASAL otrzymuje kontekst, pytanie i dozwolone opcje. Zwraca rozkład
prawdopodobieństw, a nie generowane uzasadnienie lub rozmowę. Nasz pierwszy
zakres to propozycja dziedziny sprawy, którą użytkownik może potwierdzić.
Model nie jest źródłem tekstów ustaw ani potwierdzeniem prawa obowiązującego
w danej sprawie. Stan prawny musi wynikać ze zweryfikowanych źródeł i dat.

Wysoki wynik klasyfikacji nie dowodzi poprawności prawnej. Wyników benchmarków
autora nie przedstawiamy jako skuteczności naszej aplikacji. Dokumentacja
BASAL-a opisuje ograniczenia, w tym błąd związany z okresami wypowiedzenia.
Po zmianie modelu, runtime lub kwantyzacji trzeba ponownie ocenić jakość.

## Wspieranie polskich modeli w praktyce

Chcemy tworzyć przydatne zastosowanie polskiego AI i publikować rzetelne wyniki
jego sprawdzeń: syntetyczne przypadki, definicje kategorii, pomyłki, niepewność,
metody i poprawki. To zamierzenie rozwoju, nie deklaracja ukończonej ewaluacji.
Do publicznych testów nie trafiają rzeczywiste sprawy ani dane klientów.

Przed włączeniem modelu dla użytkowników wymagamy:

- zgodności kontraktu API na rzeczywistej instalacji;
- zmierzonego czasu odpowiedzi i kontrolowanej liczby wywołań;
- poprawnej obsługi awarii i niejednoznacznej klasyfikacji;
- ręcznego wyboru dziedziny oraz przejrzystej informacji o przepływie opisu;
- oddzielnej oceny trafności na przypadkach zweryfikowanych przez ludzi.

## Źródła informacji

- [Strona BASAL-a](https://basal.si5.pl/)
- [Dokumentacja, typy decyzji i ograniczenia](https://github.com/rkinas/basal)
- [Autorstwo modeli bazowych](https://github.com/rkinas/basal/blob/main/NOTICE)
- [Licencja silnika](https://github.com/rkinas/basal/blob/main/LICENSE)

Informacje o technologii sprawdzono 2026-10-03. Zainstalowany wariant modelu
i jego rewizja będą opisane po zakończeniu weryfikacji integracji.
