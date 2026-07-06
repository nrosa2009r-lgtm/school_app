import asyncio
import subprocess
import sys
from database.db import create_db
from security.sec import gen_key, gen_jwt_token
from config.conf import put_key, get_data, put_data

async def main():
    # 1. Inicjalizacja klucza - zapisze się w conf.json na stałe
    existing_key = get_data("MASTER_KEY")
    if not existing_key:
        put_key(key="MASTER_KEY", value=gen_key())
    
    existing_jwt_key = get_data("JWT_SECRET_KEY")
    if not existing_jwt_key:
        put_data(key="JWT_SECRET_KEY", value=gen_jwt_token().hex())

    ip_adres = get_data("SERVER_IP")
    if not ip_adres:
        put_data(key="SERVER_IP", value="http://127.0.0.1:8000")

    # --- LOGIKA AUTOMATYCZNEGO ZAPISU ŚCIEŻEK ---
    
    # Sprawdzenie i pobranie ścieżki dla FastAPI
    sciezka_fastapi = get_data("FASTAPI_PATH")
    if not sciezka_fastapi:
        sciezka_fastapi = "C:/Users/admin/Documents/app/venv/api/main.py"
        put_data(key="FASTAPI_PATH", value=sciezka_fastapi)

    # Sprawdzenie i pobranie ścieżki dla Flet
    sciezka_flet = get_data("FLET_PATH")
    if not sciezka_flet:
        sciezka_flet ="C:/Users/admin/Documents/app/venv/ui/front.py"
        put_data(key="FLET_PATH", value=sciezka_flet)

    # Inicjalizacja bazy danych
    await create_db()

    # 2. Uruchamianie terminali z pobranymi ścieżkami
    print("\nUruchamianie usług w osobnych oknach...")

    if sys.platform == "win32":
        # System WINDOWS
        subprocess.Popen(f'start cmd /k "fastapi dev {sciezka_fastapi}"', shell=True)
        subprocess.Popen(f'start cmd /k "flet run --android {sciezka_flet}"', shell=True)
    else:
        # System LINUX
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"fastapi dev {sciezka_fastapi}; exec bash"])
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"flet run --android {sciezka_flet}; exec bash"])

if __name__ == "__main__":
    asyncio.run(main())
