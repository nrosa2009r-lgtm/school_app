import asyncio
from database.db import create_db
from security.sec import gen_key,gen_jwt_token
from config.conf import put_key ,get_data,put_data

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

    await create_db()

if __name__ == "__main__":
    asyncio.run(main())

