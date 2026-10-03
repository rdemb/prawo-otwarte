# Współpraca

Przeczytaj README i roadmapę. Otwórz issue opisujące konkretny problem,
źródło, aktualny rezultat i oczekiwane zachowanie. Nie umieszczaj danych klienta
ani prywatnych dokumentów.

Zmiany w kodzie powinny zawierać test istotnej własności: zgodności źródeł,
obsługi wersji, błędów integracji, prywatności albo zachowania użytkowego.
Nie oceniaj poprawności porady wyłącznie na podstawie opinii innego modelu.

Zmiana adaptera lub sposobu kwantyzacji modelu wymaga sprawdzenia kontraktu
i różnic wyników. Zmiany w źródłach muszą zachowywać pochodzenie i relacje.

Wkład w kod jest udostępniany na warunkach Apache-2.0 projektu. Dołączając dane
lub cudze materiały, opisz oddzielnie ich pochodzenie i warunki wykorzystania.

Pomoc jest potrzebna także poza kodem: dostępność i czytelność interfejsu,
sprawdzanie źródeł, syntetyczne przypadki testowe i niezależna ocena prawnicza.
Nie nazywaj wyniku klasyfikacji opinią prawną. Nie przenoś benchmarku modelu
na deklarowaną skuteczność aplikacji bez osobnego badania.

Przed publikacją uruchom `python -m scripts.check_public_repo`. Nie dodawaj
plików z instrukcjami agentów, raportów hosta, baz, wag ani prawdziwych spraw.
Do testów używaj danych syntetycznych. Jedyny workflow publikacji strony to
`Publish website`; jego artefakt zawiera wyłącznie publiczne zasoby.

## Testy strony przed publikacją

```sh
python3 -m unittest discover -s tests -v
npm ci --ignore-scripts
npx playwright install chromium
npm test
npm run test:browser
```

Testy przeglądarkowe używają lokalnego serwera, syntetycznych odpowiedzi API
i rzeczywistej pamięci podręcznej przeglądarki. Nie obciążają publicznego VPS
ani modelu. Obejmują powracającego użytkownika, brak pliku aplikacji/CSS,
odzyskanie połączenia, laboratorium, eksport bez opisu sprawy i widoki mobilne.
Workflow publikacji musi przejść te same testy przed wysłaniem strony.
