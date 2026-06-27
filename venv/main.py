import asyncio
from database.db import create_db
from services.users import add_user
from security.sec import gen_key
from config.conf import put_key

async def main():
    put_key(key="MASTER_KEY",value=gen_key())
    await create_db()
    
    await add_user("natan","rosa","nrpl350gmail.com","Trawis8!")


if __name__ == "__main__":
    asyncio.run(main())
