# Prawo Otwarte

**Polskie prawo, otwarte źródła i sprawdzalne informacje.**

**Adres strony:** [rdemb.github.io/prawo-otwarte](https://rdemb.github.io/prawo-otwarte/)
— publiczna pracownia, bez konta i opłat za dostęp.

Publiczny projekt budujący asystenta badania polskiego prawa. Docelowy zakres
obejmuje wszystkie dziedziny prawa polskiego, z prawem miejscowym, odpowiednimi
źródłami UE oraz odrębną warstwą orzecznictwa i objaśnień.

Projekt rozwijamy w oparciu o **[BASAL](https://basal.si5.pl/)**, otwarty model
decyzyjny Remigiusza Kinasa zbudowany na modelach **Bielik / SpeakLeash**.
Chcemy wspierać praktyczne zastosowania polskich modeli poprzez otwarty kod,
sprawdzalne testy i publikowanie ograniczeń. **Model nie jest jeszcze podłączony
do publicznej strony.** [Rola BASAL-a, autorstwo i plan integracji](docs/BASAL.md).

## Stan: 0.1 — działający fundament, nie gotowy autonomiczny prawnik

Wersja 0.1 oferuje:

- responsywną stronę i działające formularze, bez kont i zewnętrznego śledzenia;
- wyszukiwanie **tytułów aktów** w oficjalnym ELI/API Sejmu;
- filtry dziennika i roku publikacji oraz kolejne strony wyników;
- listę wybranych źródeł z eksportem tytułów, identyfikatorów i oficjalnych linków;
- lokalny katalog SQLite FTS5: metadane oraz dostępne, jawnie importowane teksty HTML;
- kopie źródeł z SHA-256, czasem pobrania i oryginalnym identyfikatorem ELI;
- jawny stan pokrycia źródeł — początkowo lokalna baza jest pusta;
- notatkę sprawy, pytania do wyjaśnienia i pobieranie notatki na urządzenie użytkownika;
- opcjonalne kierowanie sprawy do dziedziny przez **lokalny BASAL**;
- ograniczenie zapytań, walidację danych i ograniczenie równoległych wywołań BASAL-a.

Nie są jeszcze zaimplementowane: generatywna opinia prawna, rekonstrukcja prawa
na datę zdarzenia, OCR/PDF, pełny import wszystkich źródeł, prawo miejscowe,
import EUR-Lex i orzecznictwa, kalkulator terminów oraz merytoryczna walidacja
porad przez prawników. Interfejs nie przedstawia tych funkcji jako działających.

**Pobranie aktów nie jest potwierdzeniem kompletności prawa ani poprawności jego
interpretacji. Status aktu w ELI nie weryfikuje stanu prawnego konkretnej sprawy.**

## Publiczna strona — GitHub Pages

Wersja statyczna zachowuje wygląd aplikacji i oferuje wyszukiwanie w ELI bezpośrednio
z przeglądarki oraz notatkę sprawy tworzoną na urządzeniu użytkownika. Nie przesyła
opisu sprawy do modelu. Lokalna baza i BASAL wymagają osobnego backendu na VPS;
nie są przedstawiane jako podłączone do wersji Pages.

Lista źródeł i notatka pozostają w pamięci karty — odświeżenie je usuwa. Użytkownik
może pobrać je do pliku. Rok w filtrze jest rokiem publikacji, nie datą obowiązywania.

Workflow `Publish website` buduje stronę po zmianach na `main`. Dla własnej kopii repo ustaw
w [Settings → Pages](https://github.com/rdemb/prawo-otwarte/settings/pages)
**Build and deployment → Source → GitHub Actions**. Następnie uruchom workflow
lub ponów nieudane wdrożenie w Actions. Nie potrzeba dodatkowego tokenu ani domeny.

Publikowanych jest tylko siedem plików przygotowanych w `_site/`. Katalog repo,
kod serwera, dokumentacja wdrożenia i dane nie są przesyłane jako strona.

```bash
python3 -m scripts.build_pages --output _site
python3 -m http.server 8090 --bind 127.0.0.1 --directory _site
```

Przy kolejnym buildzie wybierz pusty katalog wyjściowy. Builder celowo nie kasuje
istniejącej zawartości. Instrukcje dla agentów i prywatne notatki operacyjne
pozostają poza publicznym repozytorium.

## Uruchomienie aplikacji na serwerze lub lokalnie

Python 3.12+ z SQLite FTS5. Kod aplikacji używa standardowej biblioteki Pythona;
do uruchomienia lokalnego nie trzeba instalować zależności.

```bash
git clone https://github.com/rdemb/prawo-otwarte.git
cd prawo-otwarte
python3 -m unittest discover -s tests -v
python3 -m prawo serve --port 8080
```

Otwórz `http://127.0.0.1:8080`. Serwer lokalny nie jest przeznaczony do internetu.
Samo otwarcie `index.html` lub hosting statyczny nie uruchamia API.

## Pierwsze źródła

Importer działa wyłącznie po jawnym uruchomieniu przez administratora. Aplikacja
webowa nie udostępnia endpointu importu ani operacji administracyjnych.

```bash
# Cztery przykładowe akty: Konstytucja, KC, KP, ustawa o prawach konsumenta.
# To identyfikatory źródeł, a nie ręcznie zatwierdzone wersje przepisów na dziś.
python3 -m prawo bootstrap --texts
python3 -m prawo status

# Metadane jednego rocznika, do 5 stron po 100 rekordów.
python3 -m prawo sync --publisher DU --year 2025 --max-pages 5
python3 -m prawo sync --publisher DU --year 2025 --max-pages 5 --resume

# Jawny import metadanych i dostępnego HTML wskazanego aktu.
python3 -m prawo import-act DU/1997/483 --text
```

`sync` obsługuje DU i MP oraz roczniki 1900–bieżący rok; nie każdy rocznik istnieje
w źródle. Domyślna przerwa między stronami wynosi sekundę. Wznowienie korzysta
z zapisanego offsetu. Zmiany źródła podczas stronicowania mogą powodować różnice:
zakończenie enumeracji nie jest certyfikatem kompletności. Wymagane są późniejsza
rekonsyliacja identyfikatorów i sprawdzanie zmian, opisane w roadmapie.

`data/` zawiera bazę i snapshoty. Jest wyłączone z Git. Kopie HTML są prezentowane
jako tekst, bez wykonywania kodu źródłowej strony. Tekst oznaczany jest jako
nieaktualny i wyłączany z FTS po wykryciu zmiany `changeDate` metadanych.

## BASAL

Integracja domyślnie jest wyłączona. Nie pobieramy wag podczas startu strony i nie
próbujemy samodzielnie zmieniać istniejącej instalacji modelu.

```bash
PRAWO_BASAL_ENABLED=1 PRAWO_BASAL_URL=http://127.0.0.1:8766 python3 -m prawo serve
```

Adapter oczekuje `POST /v1/systemone` z typem `choice`. Obsługuje dziewięć dziedzin,
w tym `unknown`. Adres musi wskazywać numeryczny loopback IP. Zmiana istniejącego
serwera modelu lub formatu odpowiedzi wymaga testu kontraktu i jakości.

Próg 0.80 jest **początkową regułą routingu**, a nie zwalidowaną kalibracją ani
prawdopodobieństwem poprawności prawnej. BASAL nie podejmuje decyzji o roszczeniach,
winie, terminach czy wyniku procesu. Przy awarii użytkownik wybiera dziedzinę sam.
Znane ograniczenia modeli opisuje [autor BASAL-a](https://github.com/rkinas/basal#limitations).

## Wdrożenie i rozwój

- [Architektura i model zaufania](docs/ARCHITECTURE.md)
- [Wdrożenie VPS](docs/DEPLOYMENT.md)
- [Plan rozwoju i kryteria jakości](docs/ROADMAP.md)
- [Źródła i zasady importu](docs/SOURCES.md)
- [Wyniki sprawdzeń tej wersji](docs/VALIDATION.md)
- [Współpraca](CONTRIBUTING.md) · [Bezpieczeństwo i prywatność](SECURITY.md)

Cały kod aplikacji: Apache-2.0. Zachowano oryginalny plik LICENSE repozytorium.
Wagi modeli i materiały zewnętrzne mają własne warunki; licencja kodu projektu
nie przenosi automatycznie praw do cudzych opracowań lub baz danych.

Projekt jest niezależny od Sejmu, sądów, UOKiK i autorów modeli. Nazwy źródeł
wskazują ich pochodzenie, nie partnerstwo ani urzędowe zatwierdzenie aplikacji.
