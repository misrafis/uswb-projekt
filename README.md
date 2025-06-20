# uswb-projekt
Projekt aplikacji webowej do sprzedaży biletów na projekt z przedmiotu Usługi Sieciowe w Biznesie

# Asynchroniczny System Sprzedaży Biletów

[![Licencja: MIT](https://img.shields.io/badge/Licencja-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Technologie](https://img.shields.io/badge/technologie-Docker%2C%20Python%2C%20Flask%2C%20RabbitMQ-blue)](https://#stos-technologiczny)

Projekt demonstracyjny w pełni funkcjonalnej, skonteneryzowanej aplikacji webowej do sprzedaży biletów na wydarzenia. Głównym celem projektu było zaimplementowanie architektury odpornej na nagłe, masowe obciążenie (np. w momencie rozpoczęcia sprzedaży) oraz dostarczenie użytkownikowi transparentnej informacji zwrotnej o statusie jego zakupu.

Aplikacja wykorzystuje wzorzec producent-konsument z brokerem wiadomości (RabbitMQ) do asynchronicznego przetwarzania zamówień, co zapewnia wysoką responsywność i skalowalność.

## Kluczowe Funkcjonalności

* **Pełna Autoryzacja Użytkowników:** System rejestracji i logowania oparty na tokenach **JWT**.
* **Asynchroniczne Przetwarzanie Zamówień:** Odseparowanie procesu zakupu od interakcji z użytkownikiem za pomocą kolejki zadań, co gwarantuje stabilność pod dużym obciążeniem.
* **Śledzenie Statusu "Na Żywo":** Użytkownik może na bieżąco obserwować status swojego zamówienia oraz przybliżoną pozycję w kolejce.
* **Skalowalność Horyzontalna:** Możliwość łatwego uruchomienia wielu instancji "workerów" w celu zwielokrotnienia przepustowości systemu.
* **Symulacja Wysokiego Ruchu:** Dedykowany skrypt do generowania masowych, asynchronicznych żądań, pozwalający na testowanie wydajności architektury.
* **Pełna Konteneryzacja:** Cała aplikacja i jej zależności (baza danych, broker wiadomości) są zarządzane przez Docker i Docker Compose.

## Stos Technologiczny

-   **Backend:**
    -   Python 3.9
    -   Flask (jako framework API)
    -   Flask-JWT-Extended (do obsługi tokenów JWT)
    -   Flask-Bcrypt (do hashowania haseł)
    -   Pika (do komunikacji z RabbitMQ)
    -   Psycopg2 (sterownik do PostgreSQL)
-   **Frontend:**
    -   HTML5, CSS3, JavaScript (ES6)
    -   Bootstrap 5 (do stylizacji)
    -   Nginx (jako serwer i reverse proxy)
-   **Baza Danych:**
    -   PostgreSQL 16
-   **Broker Wiadomości:**
    -   RabbitMQ 3.13 (z panelem administracyjnym)
-   **Konteneryzacja:**
    -   Docker
    -   Docker Compose

## Instrukcja Uruchomienia

Do uruchomienia projektu wymagana jest jedynie instalacja **Docker** oraz **Docker Compose** (zawartego w Docker Desktop).

1.  **Sklonuj repozytorium:**
    ```bash
    git clone [adres-twojego-repozytorium]
    cd [nazwa-repozytorium]
    ```

2.  **Uruchomienie standardowe (1 worker):**
    ```bash
    docker-compose up --build
    ```
    Aplikacja będzie dostępna pod adresem `http://localhost:8080`.

3.  **Uruchomienie ze skalowaniem (np. 5 workerów):**
    Aby zobaczyć pełną moc systemu, uruchom go z 5 workerami przetwarzającymi kolejkę.
    ```bash
    docker-compose up --build --scale worker=5
    ```

4.  **Uruchomienie symulacji:**
    Aby wygenerować masowy ruch, w osobnym terminalu uruchom skrypt `symulacja.py`.
    ```bash
    # Upewnij się, że masz zainstalowane potrzebne biblioteki
    pip install aiohttp
    
    # Uruchom skrypt
    python symulacja.py
    ```
    Panel administracyjny RabbitMQ jest dostępny pod adresem `http://localhost:15672` (login: `guest`, hasło: `guest`).

<details>
<summary><strong>Szczegółowy opis plików</strong></summary>

-   `docker-compose.yml`: Definiuje 5 głównych serwisów (`backend`, `worker`, `frontend`, `rabbitmq`, `db`), ich obrazy, porty, sieci, wolumeny i zmienne środowiskowe. Jest to centralny plik konfiguracyjny.
-   `backend/app.py`: Zawiera logikę API, w tym endpointy do rejestracji, logowania, zakupu (tworzenie zadania), pobierania listy koncertów i statusu zamówień.
-   `worker/worker.py`: Łączy się z RabbitMQ, pobiera zadania zakupu i wykonuje logikę biznesową w transakcji na bazie danych PostgreSQL.
-   `frontend/nginx.conf`: Konfiguruje Nginx do serwowania plików statycznych oraz do działania jako reverse proxy dla wszystkich zapytań `/api/`, przekierowując je do serwisu `backend`.
-   `db_init/init.sql`: Tworzy tabele `users`, `concerts` i `orders` wraz z indeksami przy pierwszym uruchomieniu bazy danych.
-   `symulacja.py`: Asynchroniczny skrypt, który pozwala na realistyczne przetestowanie odporności systemu na duże obciążenie.

</details>

## Potencjalny Dalszy Rozwój

-   **Integracja z systemem płatności** (np. Stripe) w celu finalizacji transakcji.
-   **Wysyłanie powiadomień e-mail** po udanym zakupie z użyciem osobnej kolejki w RabbitMQ.
-   **Stworzenie panelu administratora** do zarządzania koncertami i użytkownikami.
-   **Implementacja WebSockets** (np. z Flask-SocketIO) w celu zastąpienia pollingu i uzyskania prawdziwie natychmiastowych aktualizacji.
-   **Napisanie testów automatycznych** (jednostkowych i integracyjnych) dla zapewnienia stabilności aplikacji.

## Licencja

Projekt udostępniony na licencji MIT.
