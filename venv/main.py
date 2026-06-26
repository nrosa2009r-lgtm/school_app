import asyncio
from database.db import create_db
from services.users import add_user

async def main():
    print("Rozpoczynam tworzenie bazy danych...")
    await create_db()
    print("Baza danych i tabele zostały pomyślnie utworzone!")
    await add_user("natan","rosa","nrpl350gmail.com","Trawis8!")


if __name__ == "__main__":
    asyncio.run(main())
