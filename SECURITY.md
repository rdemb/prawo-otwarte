# Bezpieczeństwo i prywatność

Nie publikuj opisów rzeczywistych spraw, danych identyfikacyjnych, sekretów,
adresów administracyjnych VPS ani surowych raportów hosta w publicznych issues.
Zgłoszenia powinny zawierać zanonimizowany, minimalny przykład odtworzenia.
Poufne podatności zgłaszaj przez prywatny mechanizm GitHuba, jeżeli został
włączony przez właściciela. Nie publikuj działających sekretów jako „dowodu”.

Aplikacja nie zapisuje opisów spraw ani nie ma endpointu przesyłania dokumentów.
To nie jest twierdzenie o retencji reverse proxy, dostawcy hostingu, kopiach
pamięci czy narzędziach diagnostycznych. Operator musi sprawdzić cały przepływ.

Katalog i kopie źródeł nie powinny być serwowane jako katalog statyczny.
Model dostępny tylko lokalnie; strona ma dostęp wyłącznie do API aplikacji.
Wariant GitHub Pages bez API wyszukuje bezpośrednio w publicznym ELI; opis sprawy
pozostaje w przeglądarce. W połączonej instalacji opis trafia do serwera projektu
i opcjonalnie lokalnego BASAL-a. Aplikacja nie zapisuje opisu w bazie. Lista źródeł,
notatka i pomiary pozostają w pamięci karty przeglądarki. Odświeżenie je usuwa.
Eksport do pliku odbywa się na żądanie użytkownika. Nie używamy localStorage,
zewnętrznego śledzenia ani formularza przesyłania dokumentów. GitHub Pages
i API Sejmu obsługują żądania sieciowe według własnych zasad; brak własnej
analityki nie oznacza braku danych technicznych u dostawców infrastruktury.
Nie dodawać zewnętrznego LLM bez jawnej konfiguracji i informacji o przesyłaniu danych.

Znane ograniczenia 0.1: limiter lokalny dla procesu, brak logowania użytkowników,
brak gotowej odporności wielowęzłowej, brak niezależnej walidacji prawnej.
Aktualizuj przypięte zależności po sprawdzeniu testów i aktualnych komunikatów.

CI oraz publikacja uruchamiają `python -m scripts.check_public_repo`. Kontrola
odrzuca wybrane kategorie plików prywatnych i charakterystyczne formaty kluczy.
Wyświetla wyłącznie ścieżkę i nazwę reguły, nigdy wartość sekretu. To dodatkowa
ochrona, nie pełny audyt ani gwarancja wykrycia dowolnych danych poufnych.

Workflow Pages publikuje wyłącznie wynik `scripts.build_pages`: jawnie dozwolone
zasoby strony. Nazwy stylów, skryptów i konfiguracji zawierają skrót ich zawartości;
nowy HTML nie odwołuje się do starych, zapamiętanych plików. Nie dodawaj równoległego workflow publikującego `path: '.'`.
Instrukcje agentów i raporty VPS przechowuj poza publicznym repozytorium.
