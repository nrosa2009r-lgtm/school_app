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
        
    await create_db()

if __name__ == "__main__":
    asyncio.run(main())

