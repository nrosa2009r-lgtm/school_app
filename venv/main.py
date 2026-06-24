import asyncio
from database.db import create_db
from services.create_admin import create_root_admin
async def main():
    print("Rozpoczynam tworzenie bazy danych...")
    await create_db()
    print("Baza danych i tabele zostały pomyślnie utworzone!")
    await create_root_admin("natan","rosa","nrpl350@gmail.com","Trawis8!")



if __name__ == "__main__":
    asyncio.run(main())
