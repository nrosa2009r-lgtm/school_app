from database.db import async_session, Users, is_root_admin_exist

async def create_root_admin(iname, ilastname, iemail, ipassword):
    root_admin_status = await is_root_admin_exist()
    
    # Jeśli status to None, użytkownika nie ma - tworzymy go
    if root_admin_status is None:
        print("Brak administratora. Tworzę nowego...")
        async with async_session() as conn:
            admin_data = Users(
                name=iname,
                last_name=ilastname,
                email=iemail,
                password=ipassword,
                role="root_admin",
                is_active=True
            )
            conn.add(admin_data)
            await conn.commit()
            print(f"Pomyślnie utworzono nowego root admina: {iemail}")

