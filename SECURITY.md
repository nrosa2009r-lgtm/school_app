# 🛡️ Polityka Bezpieczeństwa (Security Policy & Zero Trust Architecture)

Projekt **School Catering Application (`school_app`)** został zaprojektowany zgodnie z paradygmatem **Zero Trust Security (Nigdy nie ufaj, zawsze weryfikuj)**. Niniejszy dokument opisuje szczegółowo architekturę bezpieczeństwa, wdrożone mechanizmy ochrony danych wrażliwych, zarządzanie sesjami, kontrolę dostępu oraz procedury zgłaszania potencjalnych podatności.

---

## 🔐 1. Szyfrowanie Danych w Spoczynku (`Data at Rest`) – AES-256-GCM

Wszystkie dane osobowe użytkowników przechowywane w bazie danych (takie jak imiona, nazwiska, adresy e-mail oraz jednorazowe kody aktywacyjne) są **bezwzględnie szyfrowane przed zapisaniem na dysk**.

### Specyfikacja kryptograficzna:
* **Algorytm:** `AES-256-GCM` (`Advanced Encryption Standard` w trybie `Galois/Counter Mode` z 256-bitowym kluczem).
* **Biblioteka:** `cryptography.hazmat.primitives.ciphers.aead.AESGCM`.
* **Klucz główny (`MASTER_KEY`):** Wywodzony kryptograficznie (SHA-256) z głównego sekretu konfiguracji systemu (`venv/config/conf.json`). Klucz generowany jest przy pierwszym uruchomieniu i nigdy nie trafia do kodu źródłowego ani systemów kontroli wersji.
* **Losowy Nonce (IV):** Każda operacja szyfrowania generuje unikalny, kryptograficznie bezpieczny 96-bitowy (12-bajtowy) wektor inicjalizacyjny (`secrets.token_bytes(12)`). Nonce jest dołączany na początku szyfrogramu i wraz z 16-bajtowym tagiem uwierzytelniającym kodowany do formatu `Base64`.
* **Kolumny w bazie danych:** Szyfrogramy trafiają do dedykowanych kolumn `name_enc`, `last_name_enc`, `email_enc`, `activation_code_enc`. Na poziomie kodu aplikacji (ORM SQLAlchemy) udostępniono przezroczyste właściwości (`@property def name(self)`), które zapewniają automatyczne szyfrowanie i odszyfrowywanie w locie wyłącznie w bezpiecznej pamięci RAM serwera dla uprawnionych zapytań.

---

## 🔍 2. Deterministyczny Blind Index (`Blind Indexing` dla e-maili)

Ponieważ szyfrowanie `AES-256-GCM` wykorzystuje losowy nonce przy każdej operacji, dwukrotne zaszyfrowanie tego samego adresu e-mail daje dwa zupełnie różne szyfrogramy Base64. Uniemożliwia to wykonanie tradycyjnych zapytań SQL typu `SELECT * FROM users WHERE email = :email` bez uprzedniego odczytania i odszyfrowania całej tabeli (co stanowiłoby ogromne zagrożenie wydajnościowe i bezpieczeństwa).

### Rozwiązanie – Blind Index (`HMAC-SHA256`):
* Aby umożliwić natychmiastowe i bezpieczne wyszukiwanie użytkowników przy logowaniu i rejestracji, aplikacja wylicza deterministyczny skrót **Blind Index** dla każdego adresu e-mail przy użyciu algorytmu `HMAC-SHA256` z osobnym, tajnym kluczem `HMAC_KEY`.
* Skrót wyliczany jest według wzoru: `hmac.new(HMAC_KEY.encode(), email.strip().lower().encode(), hashlib.sha256).hexdigest()`.
* Wyliczony 64-znakowy ciąg hex jest zapisywany w kolumnie `email_hash` z założonym unikalnym indeksem w bazie danych (`unique=True`).
* Nawet w przypadku wycieku całej bazy danych atakujący nie jest w stanie odwrócić skrótów `email_hash` na prawdziwe adresy e-mail (dzięki tajnemu kluczowi `HMAC_KEY`), a jednocześnie serwer API może błyskawicznie weryfikować unikalność lub pobierać rekord logującego się użytkownika w czasie $\mathcal{O}(1)$.

---

## 🔑 3. Ochrona Haseł i Walidacja Siły

* **Haszowanie (`bcrypt`):** Hasła użytkowników nie są nigdy przechowywane w formie jawnej ani w postaci prostych skrótów (jak MD5 czy SHA-1). Stosujemy bibliotekę `passlib[bcrypt]` z dynamicznym generowaniem soli (`bcrypt.gensalt()`). Haszowanie algorytmem `bcrypt` ze zmiennym kosztem obliczeniowym skutecznie chroni przed atakami słownikowymi i tablicami tęczowymi (Rainbow Tables).
* **Walidacja siły hasła:** Zarówno po stronie serwera (`async def password_validator(password)` w `security/sec.py`), jak i po stronie interfejsu użytkownika (dynamiczny pasek siły hasła `check_password_strength()` we Flet SPA) egzekwowane są rygorystyczne zasady:
  1. Minimum **10 znaków** długości.
  2. Obecność co najmniej jednej **małej litery** (`a-z`).
  3. Obecność co najmniej jednej **wielkiej litery** (`A-Z`).
  4. Obecność co najmniej jednej **cyfry** (`0-9`).
  5. Obecność co najmniej jednego **znaku specjalnego** (`!@#$...`).

---

## 🍪 4. Bezpieczna Sesja (`HttpOnly Cookies`) i JWT

W tradycyjnych aplikacjach SPA tokeny dostępu często przesyłane są w ciele odpowiedzi JSON i zapisywane w pamięci przeglądarki `LocalStorage` lub `SessionStorage`, co wystawia je na ryzyko kradzieży w przypadku podatności XSS (Cross-Site Scripting).

### Wdrożona ochrona sesji:
* **Brak tokena w JSON:** Po udanym uwierzytelnieniu (`POST /api/login`) endpoint API nie zwraca tokenu JWT w ciele odpowiedzi.
* **Ciasteczko sesyjne:** Token JWT (`HMAC-SHA256` z podpisem `JWT_SECRET_KEY`) jest przesyłany wyłącznie jako nagłówek HTTP:  
  `Set-Cookie: access_token=...; HttpOnly; SameSite=Lax; max_age=1800`.
* **Flaga `HttpOnly`:** Ciasteczko jest niedostępne z poziomu skryptów JavaScript ( Nawet w przypadku udanego wstrzyknięcia skryptu XSS, token sesyjny pozostaje bezpieczny i nie może zostać skradziony przez JavaScript).
* **Flaga `SameSite=Lax`:** Ogranicza przesyłanie ciasteczek w żądaniach międzywitrynowych, chroniąc przed atakami CSRF (Cross-Site Request Forgery).
* **Czas życia (`max_age`):** Token wygasa ściśle po **30 minutach** (1800 sekundach) od wydania.

---

## 🛡️ 5. Route Guards, RBAC i Ochrona przed Atakami (`Rate Limiting`)

### Aktywna weryfikacja w bazie przy każdym zapytaniu (`Zero Trust Dependency`):
Zależność autoryzacyjna `Depends(get_current_user)` w FastAPI nie tylko weryfikuje poprawność kryptograficzną podpisu tokenu JWT i czas wygaśnięcia (`exp`), ale przede wszystkim **odpytuje bazę danych w czasie rzeczywistym**, sprawdzając czy dany użytkownik nadal istnieje i czy jego konto posiada aktywny status (`is_active == True`). Jeśli administrator zablokuje lub usunie użytkownika w bazie danych, jego sesja natychmiast przestanie działać na wszystkich endpointach.

### Model uprawnień RBAC (Role-Based Access Control):
Aplikacja natywnie wspiera 5 zdefiniowanych ról o hierarchicznych uprawnieniach:
1. `rootadmin` — Główny administrator systemu (tworzony automatycznie przy inicjalizacji bazy). Posiada pełny dostęp do wszystkich funkcji, logów oraz nadawania ról.
2. `admin` — Administrator stołówki szkolnej. Posiada uprawnienia do edycji menu, zarządzania użytkownikami, przeglądania logów bezpieczeństwa oraz wszystkich zamówień.
3. `teacher` — Nauczyciel/pracownik szkoły. Uprawniony do rezerwacji dań i składania zamówień.
4. `student` — Uczeń. Uprawniony do rezerwacji dań w ramach własnego koszyka oraz przeglądania własnej historii zamówień z ograniczeniem czasowym do 09:00.
5. `user` — Podstawowa rola nowo zarejestrowanego użytkownika po aktywacji konta e-mailem.

Weryfikacja ról realizowana jest przez dedykowany dekorator i zależność `Depends(require_roles('admin', 'rootadmin'))`.

### Rate Limiting (`slowapi`):
W celu zapobiegania atakom typu Brute-Force (zgadywanie haseł) oraz Denial-of-Service (DDoS) na wrażliwe punkty końcowe zaimplementowano limitowanie zapytań na podstawie adresu IP klienta (`slowapi.Limiter`):
* **Logowanie (`POST /api/login`):** Limit `5 zapytań na minutę` z danego adresu IP.
* **Rejestracja (`POST /api/register` / `/api/add_user`):** Limit `3 zapytania na minutę`.
Przekroczenie limitu skutkuje zwrotem kodu błędu `HTTP 429 Too Many Requests` oraz zapisaniem ostrzeżenia z adresem IP w centralnych logach bezpieczeństwa.

---

## 📊 6. Centralny, Asynchroniczny Logger Bezpieczeństwa (`create_log()`)

W architekturze Zero Trust pełna rozliczalność (Accountability) i audytowalność wszystkich zdarzeń jest kluczowa. Moduł logowania w pliku `venv/log/log_generator.py` został przeprojektowany tak, aby działać asynchronicznie i bez opóźniania pętli zdarzeń.

Każde wywołanie `create_log(level, message, ip_address)` powoduje natychmiastowy zapis zdarzenia w **trzech niezależnych miejscach równolegle**:
1. **Plik logów na dysku (`logs.log`):** Zapisuje zdarzenie ze znacznikiem czasowym i poziomem ważności.
2. **Konsola systemowa (`sys.stdout`):** Zapewnia podgląd w czasie rzeczywistym dla administratorów systemów Linux i kontenerów Docker.
3. **Tabela SQL (`Logs` table w bazie danych):** Asynchroniczne zadanie w tle (`asyncio.create_task`) zapisuje zdarzenie w relacyjnej bazie danych wraz z dokładnym czasem UTC, poziomem logu, treścią komunikatu oraz **adresem IP klienta**.

Dzięki temu administratorzy z uprawnieniami `admin` / `rootadmin` mogą przeglądać dziennik bezpieczeństwa bezpośrednio z poziomu interfejsu graficznego w zakładce `/admin`.

---

## 🐛 7. Zgłaszanie Podatności (Vulnerability Disclosure Policy)

Traktujemy bezpieczeństwo aplikacji szkolnych i danych dzieci/pracowników z najwyższym priorytetem. Jeśli odkryłeś potencjalną lukę bezpieczeństwa, podatność w kodzie lub błąd kryptograficzny w systemie **School Catering Application (`school_app`)**, prosimy o odpowiedzialne zgłoszenie problemu (Responsible Disclosure).

### Procedura zgłaszania:
1. **Nie zgłaszaj luki publicznie** poprzez otwarte zgłoszenia (Issues) na GitHubie ani na forach publicznych przed udostępnieniem łatki.
2. Skontaktuj się bezpośrednio z zespołem bezpieczeństwa lub głównym architektem pod adresem e-mail: `nrpl350@gmail.com` (lub adresem wskazanym przez administratora Twojej placówki).
3. W treści zgłoszenia dołącz:
   * Opis podatności lub błędu.
   * Kroki potrzebne do odtworzenia problemu (Proof of Concept / skrypt testowy).
   * Przewidywany wpływ podatności na system i dane użytkowników.
4. Zespół dokona weryfikacji zgłoszenia w ciągu 48 godzin od otrzymania wiadomości i podejmie kroki w celu natychmiastowej naprawy i wydania aktualizacji bezpieczeństwa.
