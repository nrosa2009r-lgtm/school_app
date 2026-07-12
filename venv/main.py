import asyncio
import subprocess
import sys
import os
from database.db import create_db
from security.sec import gen_key, gen_jwt_token
from config.conf import put_key, get_data, put_data

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

    print("\nInicjalizacja zakończona pomyślnie. Gotowe do uruchomienia usług.")
    if len(sys.argv) > 1 and sys.argv[1] == "--init-only":
        return

    print("\nUruchamianie usług w osobnych oknach...")
    if sys.platform == "win32":
        subprocess.Popen(f'start cmd /k "fastapi dev {sciezka_fastapi}"', shell=True)
        subprocess.Popen(f'start cmd /k "flet run {sciezka_flet}"', shell=True)
    else:
        # W środowisku Linux lub kontenerowym uruchamiamy w tłe lub informujemy użytkownika
        print(f"Aby uruchomić API: fastapi dev {sciezka_fastapi}")
        print(f"Aby uruchomić UI: flet run {sciezka_flet}")

if __name__ == "__main__":
    asyncio.run(main())
