import asyncio
from database.db import create_db

async def main():
    print("Rozpoczynam tworzenie bazy danych...")
    await create_db()
    print("Baza danych i tabele zostały pomyślnie utworzone!")



if __name__ == "__main__":
    asyncio.run(main())
