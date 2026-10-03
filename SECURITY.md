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
Nie dodawać zewnętrznego LLM bez jawnej konfiguracji i informacji o przesyłaniu danych.

Znane ograniczenia 0.1: limiter lokalny dla procesu, brak logowania użytkowników,
brak gotowej odporności wielowęzłowej, brak niezależnej walidacji prawnej.
Aktualizuj przypięte zależności po sprawdzeniu testów i aktualnych komunikatów.
