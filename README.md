# 🍽️ School Catering Application (`school_app`)

Zaawansowana, w pełni asynchroniczna aplikacja Full-Stack służąca do zarządzania stołówką szkolną, rezerwacją dań oraz zamówieniami żywieniowymi. Projekt został zbudowany z zachowaniem rygorystycznych standardów architektonicznych, wysokiej wydajności oraz bezwzględnego podejścia do bezpieczeństwa w modelu **Zero Trust**.

---

## 🛠️ Stos Technologiczny (Tech Stack)

* **Język programowania:** Czysty, asynchroniczny **Python 3.11+** z pełnym typowaniem (`Type Hints`).
* **Backend API:** **FastAPI** (wydajne, asynchroniczne RESTful API, automatyczna walidacja schematów przez Pydantic v2).
* **Baza Danych & ORM:** **SQLAlchemy 2.0** (`AsyncSession`, `async_sessionmaker`) ze wsparciem dla `aiosqlite` (SQLite) lub PostgreSQL.
* **Frontend UI:** **Flet** (framework oparty na silniku Flutter dla Pythona), architektura SPA (Single Page Application) z dynamicznym routingu po stronie klienta.
* **Bezpieczeństwo & Kryptografia:**
  * `cryptography` – Szyfrowanie danych wrażliwych w spoczynku w trybie **AES-256-GCM**.
  * `passlib[bcrypt]` / `bcrypt` – Haszowanie haseł.
  * `PyJWT` (`python-jose`) – Generowanie i weryfikacja tokenów JWT w bezpiecznych ciasteczkach.
  * `slowapi` – Rate Limiting (ochrona przed atakami Brute-Force/DDoS).

---

## 🚀 Jak uruchomić aplikację (Instrukcja Uruchomienia / Quickstart)

### 1. Wymagania wstępne
Upewnij się, że w systemie zainstalowany jest **Python 3.11** lub nowszy:
```bash
python3 --version
```

### 2. Klonowanie repozytorium i instalacja zależności
Sklonuj repozytorium (lub pobierz pliki projektu), przejjdź do katalogu głównego projektu i utwórz wirtualne środowisko:

```bash
# Utworzenie wirtualnego środowiska
python3 -m venv .venv

# Aktywacja wirtualnego środowiska
# Na systemach Linux / macOS:
source .venv/bin/activate
# Na systemach Windows (PowerShell/CMD):
.venv\Scripts\activate

# Instalacja wszystkich wymaganych pakietów
pip install -r requirements.txt
```

### 3. Inicjalizacja bazy danych i konfiguracji bezpieczeństwa
Przy pierwszym uruchomieniu aplikacja automatycznie wygeneruje bezpieczne klucze kryptograficzne (`MASTER_KEY`, `JWT_SECRET_KEY`, `HMAC_KEY` w pliku `venv/config/conf.json`), utworzy bazę danych ze strukturą tabel, zainicjalizuje domyślne menu stołówki oraz stworzy główne konto administratora (`rootadmin`):

```bash
python main.py --init-only
```
*(Alternatywnie, uruchomienie normalnego startu również przeprowadzi tę inicjalizację za pierwszym razem).*

### 4. Uruchomienie usług (Serwer API oraz Interfejs Flet UI)

Aplikacja składa się z dwóch współpracujących ze sobą komponentów: **Serwera API (FastAPI)** na porcie `8000` oraz **Klienta SPA (Flet)**.

#### Opcja A: Uruchomienie w dwóch osobnych terminalach (Rekomendowane dla developmentu)
Otwórz dwa okna terminala z aktywnym środowiskiem `.venv`:

**Terminal 1 — Uruchomienie Backend API (FastAPI):**
```bash
fastapi dev api/main.py --port 8000
# Lub alternatywnie przez uvicorn:
uvicorn api.main:app --reload --port 8000
```
*Serwer API będzie dostępny pod adresem `http://127.0.0.1:8000`. Dokumentacja interaktywna Swagger UI jest dostępna pod `http://127.0.0.1:8000/docs`.*

**Terminal 2 — Uruchomienie Frontend UI (Flet SPA):**
```bash
flet run app.py
# Aby uruchomić interfejs bezpośrednio w oknie przeglądarki internetowej:
flet run --web app.py
```

#### Opcja B: Automatyczny Launcher (`python main.py`)
Możesz użyć wbudowanego skryptu startowego, który w systemach Windows automatycznie otworzy dwa osobne okna konsoli dla API i UI, a w systemach Linux wyświetli dokładną instrukcję lub spróbuje uruchomić procesy:
```bash
python main.py
```

---

## 🔑 Domyślne dane logowania (Konto Root Admina)

Po zainicjalizowaniu bazy danych system tworzy domyślne konto głównego administratora:
* **E-mail:** `nrpl350@gmail.com`
* **Hasło:** `12345678`
* **Rola:** `rootadmin`

Po zalogowaniu się na to konto masz pełny dostęp do panelu administracyjnego (`/admin`), zarządzania rolami użytkowników, przeglądania logów bezpieczeństwa oraz dodawania dań i opcji do menu.

---

## 💼 Krytyczna Logika Biznesowa (Domain Logic)

### 1. Struktura Menu (Relacje One-to-Many)
System obsługuje wielopoziomowe menu stołówki oparte o relacje w SQLAlchemy:
`MenuCategory` ➡️ `MenuItem` (zawierający cenę `price` oraz aktualną pulę dostępnych porcji `stock`) ➡️ `MenuOption` (dodatki do dań, np. *"bez glutenu"* czy *"podwójna porcja mięsa"*, z własną dopłatą `extra_price`).

### 2. Zarządzanie Koszykiem i Czasem Życia (`CartManager` & TTL = 300s)
* **Pamięć RAM i blokady:** Koszyk użytkownika działa w pamięci podręcznej serwera w oparciu o menedżer `CartManager` zabezpieczony asynchronicznym zamkiem `asyncio.Lock()` i posiada czas wygaśnięcia **TTL = 5 minut (300 sekund)**.
* **Atomowa Rezerwacja Porcji:** Dodanie dania do koszyka (`/api/cart/add`) **natychmiast zdejmuje porcje ze stanu magazynowego** operacją SQL:  
  `UPDATE menu_items SET stock = stock - N WHERE id = X AND stock >= N`. Zapobiega to sytuacji, w której kilku uczniów zamówi ostatnie dostępne porcje obiadu w tym samym czasie (zjawisko *race condition*).
* **Zwolnienie Blokady (Rollback):** Jeśli zamówienie nie zostanie sfinalizowane w ciągu 5 minut lub użytkownik kliknie przycisk wyczyszczenia koszyka (`/api/cart/clear`), automatyczny mechanizm w tle lub próba odczytu przeterminowanego koszyka natychmiast **zwraca zarezerwowane porcje powrotem do puli (`stock = stock + N`)**. Finalizacja zamówienia (`/api/cart/checkout`) utrwala transakcję w tabeli `Orders` i usuwa koszyk z pamięci.

### 3. Godzina Graniczna (Cut-off Time = 09:00 rano)
Ze względów logistycznych kuchnia szkolna musi znać dokładną liczbę przygotowywanych posiłków z wyprzedzeniem.
* System automatycznie sprawdza czas serwera (`is_past_cutoff()`).
* **Po godzinie 09:00 rano danego dnia system bezwzględnie blokuje:**
  * Składanie nowych zamówień (`/api/cart/checkout`).
  * Anulowanie już złożonych i aktywnych zamówień (`/api/orders/{id}/cancel`).

---

## 🔐 Filar Bezpieczeństwa (Zero Trust)

Każdy element aplikacji został zaprojektowany w oparciu o architekturę **Zero Trust**:
1. **Szyfrowanie w spoczynku (`AES-256-GCM`):** Wszystkie dane wrażliwe użytkowników (`name_enc`, `last_name_enc`, `email_enc`, `activation_code_enc`) są przechowywane w bazie danych wyłącznie jako zaszyfrowane ciągi Base64. Zwracając dane przez API, aplikacja odszyfrowuje je w locie dla uprawnionego odbiorcy.
2. **Deterministyczny Blind Index (`HMAC-SHA256`):** Ponieważ szyfrowanie `AES-256-GCM` generuje losowy nonce (dając różne ciągi wyjściowe dla tego samego e-maila), wyszukiwanie w bazie SQL odbywa się błyskawicznie po kolumnie `email_hash` z użyciem stałego, tajnego klucza `HMAC_KEY`.
3. **Ochrona Haseł i Siła:** Hasła są przechowywane w postaci skrótu `bcrypt`. Zarówno frontend, jak i backend walidują wymogi bezpieczeństwa (min. 10 znaków, wielka i mała litera, cyfra oraz znak specjalny `!@#$...`).
4. **Bezpieczna Sesja (`HttpOnly Cookies`):** Token JWT po zalogowaniu zapisywany jest **wyłącznie w ciasteczku sesyjnym** (`Set-Cookie: access_token=...; HttpOnly; SameSite=Lax; max_age=1800`), nigdy nie jest przesyłany w ciele JSON (ochrona przed wyciekiem przez XSS).
5. **Route Guards & RBAC:** Zależność `Depends(get_current_user)` weryfikuje ciasteczko, podpis JWT, wygaśnięcie oraz aktywnie sprawdza w bazie danych czy konto nie zostało wyłączone (`is_active == True`). Model wspiera 5 ról: `rootadmin`, `admin`, `teacher`, `student`, `user`.
6. **Rate Limiting (`slowapi`):** Ochrona wrażliwych endpointów (np. logowanie `5/minute`, rejestracja `3/minute`).
7. **Asynchroniczny Centralny Logger (`create_log()`):** Zapisuje zdarzenia równolegle i bez blokowania pętli do: pliku `.log`, konsoli systemowej oraz tabeli `logs` w bazie SQL wraz z adresem IP klienta.

---

## 🎨 Architektura Frontendu (Flet SPA & UI/UX)

* **SPA (Single Page Application):** Jeden punkt wejścia `app.py`, dynamiczne przełączanie widoków za pomocą `page.on_route_change` (`/login`, `/register`, `/menu`, `/cart`, `/orders`, `/admin`). Client-side Route Guard weryfikuje sesję z serwerem i przekierowuje do logowania w razie wygaśnięcia.
* **Motywy (`ThemeManager`):** Wydajne wsparcie dla trybu Jasnego (Light) i Ciemnego (Dark) z płynną animacją obrotu ikony o 360° (`ft.Rotate`).
* **Animacje GPU-Accelerated:**
  * **Shake Animation:** Pola błędnie wypełnione "trzęsą się" w poziomie (`ft.Offset`).
  * **Pulse & Scale Button:** Przyciski akcji reagują animacją skali przy naciskaniu (`ft.Scale`).
  * **Shimmer Effect:** Szkieletowe ładowanie danych w menu i historii zamówień przed otrzymaniem odpowiedzi HTTP.
  * **Password Strength Bar:** Pasek postępu dynamicznie zmieniający kolor (czerwony -> pomarańczowy -> żółty -> zielony) podczas wpisywania hasła.

---

## 🧪 Uruchamianie Testów Automatycznych

Projekt zawiera kompleksowy zestaw testów w oparciu o framework `pytest`, sprawdzających kryptografię, rezerwacje atomowe koszyka, wygasanie TTL, odcięcie czasowe 09:00 oraz wszystkie endpointy API:

```bash
# Uruchomienie pełnego zestawu testów
pytest -v tests/test_school_app.py
```
