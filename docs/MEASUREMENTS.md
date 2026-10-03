# Pomiary w otwartym laboratorium

Panel na stronie mierzy działanie aplikacji w bieżącej karcie przeglądarki.
Nie jest globalnym dashboardem ruchu ani oceną poprawności porad prawnych.

## Zakres i prywatność

- Ostatnie 50 zakończonych prób przygotowania notatki lub testu przykładu.
- Dane wyłącznie w pamięci karty; odświeżenie i „Wyczyść pomiary” usuwają pomiary.
- Bez cookies, localStorage, zewnętrznej analityki i wysyłania ocen na serwer.
- Eksport JSON obejmuje czas, sposób ustalenia dziedziny, identyfikator przykładu,
  oczekiwaną i wybraną kategorię oraz opcjonalną ocenę przydatności.
- Eksport nie obejmuje opisu, zapytania wyszukiwania ani komunikatu błędu z serwera.
  Dziedzina i czas nadal mogą zdradzać kontekst aktywności — sprawdź plik przed udostępnieniem.
- Zwykły opis formularza jest wysyłany do API w połączonej instalacji. Samo otwarcie
  strony lub wybór przykładu nie uruchamia modelu. Każdy test wymaga kliknięcia.

## Definicje

| Wskaźnik | Definicja |
| --- | --- |
| Czas odpowiedzi | `performance.now()` przed żądaniem do odebrania i sprawdzenia odpowiedzi. Obejmuje sieć, aplikację i ewentualny model. Nie jest czasem samej inferencji ani generowania tokenów. |
| Mediana | Środkowy czas zakończonych odpowiedzi BASAL-a; przy parzystej liczbie średnia dwóch środkowych. Odmowy są uwzględnione. Ręczny wybór, niedostępność i błędy są wyłączone. |
| P95 | Czas o pozycji `ceil(0.95 * n)` w uporządkowanych czasach. Pokazywany od 20 ukończonych odpowiedzi modelu. |
| Zakończone próby | Odpowiedzi `basal` lub `basal_abstained` / próby automatycznej klasyfikacji przy włączonym modelu, włącznie z niedostępnością i błędami. |
| Bez rozstrzygnięcia | Metoda `basal_abstained` lub wybór `unknown`. Nie jest błędem połączenia. |
| Przydatność według użytkownika | Liczba ocen „Tak” / liczba ocen „Tak” i „Nie” dla propozycji. Ponowny wybór zmienia ocenę, „Nie oceniam” ją usuwa. |
| Zgodność przykładów | Zgodna dziedzina / ukończone odpowiedzi modelu dla jawnych przykładów. Odmowa to brak zgodności, niedostępność i błędy nie wchodzą do mianownika. Powtórzenia to kolejne próby; liczba różnych przykładów jest pokazana osobno. |
| Poprawność prawna | Nie zbadano. Ani ocena użytkownika, ani prawdopodobieństwo modelu, ani test techniczny jej nie potwierdzają. |

## Przykłady pilotażowe v1

Osiem jawnych, syntetycznych opisów obejmuje po jednym przykładzie dla pracy,
konsumenta, umów cywilnych, rodziny, administracji, podatków, spraw karnych
i mieszkania. Teksty i etykiety są widoczne przed wysłaniem, w `sampleCases`
w [app.js](../prawo/static/app.js). Zestaw ma pomagać eksplorować zachowanie modelu.
Etykiety przygotowano redakcyjnie; nie przeszły niezależnej oceny ekspertów.

To mały, niereprezentatywny zbiór, bez osobnego zbioru walidacyjnego, kontroli
zmienności uruchomień czy pomiaru generalizacji. Nie wolno przedstawiać wyniku
jako ogólnej trafności BASAL-a lub poprawności prawnej aplikacji. Model nie tworzy
opinii prawnej. Kolejny etap wymaga zestawu zweryfikowanego przez prawników,
przypadków wielodziedzinowych i niejednoznacznych oraz jawnej procedury oceny.

## Odtwarzalność

Algorytmy agregacji są w [metrics.js](../prawo/static/metrics.js), a ich testy
w [metrics.test.cjs](../tests/metrics.test.cjs). Uruchomienie:

```sh
node --test tests/metrics.test.cjs
```

Test publicznego HTTPS i rzeczywistej odpowiedzi modelu jest oddzielnym workflow
[Public HTTPS and model check](../.github/workflows/public-check.yml).
Potwierdza działanie techniczne w chwili testu, nie ciągłą dostępność.
