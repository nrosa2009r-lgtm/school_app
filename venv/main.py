import asyncio
import subprocess
import sys
import os
from database.db import create_db
from security.sec import gen_key, gen_jwt_token, check_password_strength, password_validator, blind_index, hash_password, encrypt_data
from config.conf import put_key, get_data, put_data


async def safe_input(prompt: str) -> str:
    """Odporny na EOFError w testach/CI."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return ""


async def setup_wizard():
    """Interaktywny kreator pierwszego uruchomienia (krok po kroku)."""
    print("\n" + "=" * 60)
    print("  🏫  KREATOR PIERWSZEGO URUCHOMIENIA")
    print("  School Catering Application v2.0 Enterprise")
    print("=" * 60)

    # Krok 0: Sprawdź czy konfiguracja już zakończona
    if get_data("SETUP_COMPLETED") == "true":
        print("\n✅ Konfiguracja została już ukończona wcześniej. Przechodzę do normalnego startu...")
        return True

    print("\nWykryto pierwsze uruchomienie systemu.")
    print("Ten kreator przeprowadzi Cię przez podstawową konfigurację.\n")

    # Krok 1: Nazwa i adres szkoły
    print("─" * 50)
    print("  KROK 1/4: Konfiguracja Szkoły")
    print("─" * 50)
    school_name = await safe_input("Nazwa szkoły [Szkoła Podstawowa nr 1]: ")
    if not school_name:
        school_name = "Szkoła Podstawowa nr 1"

    school_addr = await safe_input("Adres szkoły [ul. Szkolna 1, 00-001 Warszawa]: ")
    if not school_addr:
        school_addr = "ul. Szkolna 1, 00-001 Warszawa"

    subdomain = await safe_input("Subdomena (identyfikator) [sp1]: ")
    if not subdomain:
        subdomain = "sp1"

    # Krok 2: Godzina graniczna
    print("\n" + "─" * 50)
    print("  KROK 2/4: Godzina Graniczna Zamówień")
    print("─" * 50)
    print("Zamówienia na dziś będą przyjmowane tylko do godziny granicznej.")
    print("Po jej przekroczeniu uczniowie mogą zamawiać tylko na przyszłe dni.")

    cutoff_str = await safe_input("Godzina graniczna (0-23) [9]: ")
    try:
        cutoff_hour = int(cutoff_str) if cutoff_str else 9
        cutoff_hour = max(0, min(23, cutoff_hour))
    except ValueError:
        cutoff_hour = 9
        print("⚠️  Nieprawidłowa wartość. Ustawiono domyślną: 9:00")

    print(f"✅ Godzina graniczna: {cutoff_hour}:00")

    # Krok 3: Konto administratora
    print("\n" + "─" * 50)
    print("  KROK 3/4: Konto Root Administratora")
    print("─" * 50)
    admin_email = ""
    while not admin_email or "@" not in admin_email:
        admin_email = await safe_input("E-mail administratora [nrpl350@gmail.com]: ")
        if not admin_email:
            admin_email = "nrpl350@gmail.com"
            break

    admin_pass = ""
    while True:
        admin_pass = await safe_input("Hasło administratora (min. 10 znaków, wielka/mała litera, cyfra, znak spec.): ")
        if not admin_pass:
            admin_pass = "Admin1234!@#$"
            print("⚠️  Użyto domyślnego hasła. ZMIEŃ JE po zalogowaniu!")
            break
        valid, color, score = check_password_strength(admin_pass)
        if valid:
            print(f"✅ Siła hasła: Silne ({score}/100)")
            break
        else:
            print(f"❌ Hasło za słabe. Wymagane: min. 10 znaków, wielka/mała litera, cyfra, znak specjalny.")

    # Krok 4: Zasianie przykładowego menu
    print("\n" + "─" * 50)
    print("  KROK 4/4: Zasianie Danych")
    print("─" * 50)
    seed = await safe_input("Czy chcesz utworzyć przykładowe menu stołówki? (T/n) [T]: ")
    seed_menu = seed.lower() != "n"

    # Podsumowanie
    print("\n" + "=" * 60)
    print("  📋  PODSUMOWANIE KONFIGURACJI")
    print("=" * 60)
    print(f"  Szkoła:        {school_name}")
    print(f"  Adres:         {school_addr}")
    print(f"  Godz. odcięcia: {cutoff_hour}:00")
    print(f"  Admin e-mail:  {admin_email}")
    print(f"  Menu startowe: {'Tak' if seed_menu else 'Nie'}")
    print("=" * 60)

    confirm = await safe_input("\nZapisać konfigurację? (T/n) [T]: ")
    if confirm.lower() == "n":
        print("❌ Konfiguracja anulowana. Uruchom ponownie kreator: python main.py --setup")
        return False

    # Zapis konfiguracji
    put_data("SCHOOL_NAME", school_name)
    put_data("SCHOOL_ADDRESS", school_addr)
    put_data("SCHOOL_SUBDOMAIN", subdomain)
    put_data("SCHOOL_CUTOFF_HOUR", str(cutoff_hour))
    put_data("ADMIN_EMAIL", admin_email)
    put_data("SETUP_COMPLETED", "true")

    # Zapisanie admina do bazy
    from database.db import async_session, Users, Schools, Wallet
    from sqlalchemy import select

    async with async_session.begin() as session:
        # Szkoła
        q_s = select(Schools).where(Schools.subdomain == subdomain)
        r_s = await session.execute(q_s)
        if not r_s.scalars().first():
            session.add(Schools(
                name=school_name, subdomain=subdomain, address=school_addr,
                cutoff_hour=cutoff_hour, cutoff_minute=0
            ))

    async with async_session() as session:
        existing = await session.execute(
            select(Users).where(Users.email_hash == blind_index(admin_email.strip().lower()))
        )
        if not existing.scalars().first():
            user = Users(
                name_enc=encrypt_data("Administrator"),
                last_name_enc=encrypt_data("Systemu"),
                email_enc=encrypt_data(admin_email.strip().lower()),
                email_hash=blind_index(admin_email.strip().lower()),
                role="rootadmin",
                password=hash_password(admin_pass),
                is_active=True
            )
            session.add(user)
            await session.commit()

            # Portfel dla admina
            q = select(Wallet).where(Wallet.user_id == user.id)
            r = await session.execute(q)
            if not r.scalars().first():
                session.add(Wallet(user_id=user.id, balance=500.0))
                await session.commit()
            print("✅ Konto administratora utworzone.")
        else:
            print("ℹ️  Administrator już istnieje w bazie.")

    print("\n" + "=" * 60)
    print("  ✅  KONFIGURACJA ZAKOŃCZONA POMYŚLNIE!")
    print("=" * 60)
    print("  Aby uruchomić aplikację: python main.py")
    print("  Lub na Windows: uruchom run.bat")
    print("=" * 60 + "\n")
    return True


async def main():
    # 1. Inicjalizacja kluczy w conf.json
    existing_key = get_data("MASTER_KEY")
    if not existing_key:
        put_key(key="MASTER_KEY", value=gen_key())

    existing_jwt_key = get_data("JWT_SECRET_KEY")
    if not existing_jwt_key:
        put_data(key="JWT_SECRET_KEY", value=gen_jwt_token().hex())

    existing_hmac_key = get_data("HMAC_KEY")
    if not existing_hmac_key:
        put_data(key="HMAC_KEY", value="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08")

    ip_adres = get_data("SERVER_IP")
    if not ip_adres:
        put_data(key="SERVER_IP", value="http://127.0.0.1:8000")

    # Pobranie prawidłowych ścieżek względem bieżącego katalogu
    base_dir = os.path.abspath(os.path.dirname(__file__))

    sciezka_fastapi = get_data("FASTAPI_PATH")
    default_fastapi = os.path.join(base_dir, "api", "main.py")
    if not sciezka_fastapi or not os.path.exists(sciezka_fastapi):
        sciezka_fastapi = default_fastapi
        put_data(key="FASTAPI_PATH", value=sciezka_fastapi)

    sciezka_flet = get_data("FLET_PATH")
    default_flet = os.path.join(base_dir, "ui", "front.py")
    if not sciezka_flet or not os.path.exists(sciezka_flet):
        sciezka_flet = default_flet
        put_data(key="FLET_PATH", value=sciezka_flet)

    # Inicjalizacja bazy danych i początkowego menu
    await create_db()

    # Obsługa flag CLI
    if len(sys.argv) > 1:
        if sys.argv[1] == "--setup":
            await setup_wizard()
            return
        elif sys.argv[1] == "--check-or-setup":
            if get_data("SETUP_COMPLETED") != "true":
                await setup_wizard()
            else:
                print("✅ Konfiguracja już ukończona.")
            return
        elif sys.argv[1] == "--init-only":
            print("✅ Inicjalizacja zakończona pomyślnie. (tylko init)")
            return

    print("\nInicjalizacja zakończona pomyślnie. Gotowe do uruchomienia usług.")
    if len(sys.argv) > 1 and sys.argv[1] == "--init-only":
        return

    print("\nUruchamianie usług w osobnych oknach...")
    if sys.platform == "win32":
        subprocess.Popen(f'start cmd /k "fastapi dev {sciezka_fastapi}"', shell=True)
        subprocess.Popen(f'start cmd /k "flet run {sciezka_flet}"', shell=True)
    else:
        # W środowisku Linux lub kontenerowym uruchamiamy w tle lub informujemy użytkownika
        print(f"Aby uruchomić API: fastapi dev {sciezka_fastapi}")
        print(f"Aby uruchomić UI: flet run {sciezka_flet}")


if __name__ == "__main__":
    asyncio.run(main())
