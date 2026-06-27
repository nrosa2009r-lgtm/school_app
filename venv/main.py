import asyncio
from database.db import create_db
from services.users import add_user , del_user
from security.sec import gen_key
from config.conf import put_key ,get_data

async def main():
    # 1. Inicjalizacja klucza - zapisze się w conf.json na stałe
    existing_key = get_data("MASTER_KEY")
    if not existing_key:
        put_key(key="MASTER_KEY", value=gen_key())
        
    # 2. Tworzenie czystego pliku bazy
    await create_db()
    
    # 3. KROK REJESTRACJI (Uruchom ten kod, aby dodać świeży rekord)
    await add_user("natan", "rosa", "czysty-test@gmail.com", "Trawis8!")
    
    # 4. KROK USUNIĘCIA (Uruchom dokładnie z tym samym mailem i hasłem)
    await del_user("czysty-test@gmail.com", "Trawis8!")

if __name__ == "__main__":
    asyncio.run(main())

