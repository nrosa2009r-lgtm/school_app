from security.sec import hash_password
from database.db import Users,async_session
from log.log_generator import create_log

async def add_user(name:str,last_name:str,email:str,password:str):
    new_user = Users(
        name=name.lower(),
        last_name=last_name.lower(),
        email=email,
        role="user",
        password=hash_password(password)
    )

    try:
        async with async_session.begin() as session:
            session.add(new_user)
        create_log(level="info",message=f"Pomyślnie utworzono urzytkownika-{name}")
    except:
        create_log(level="error",message=f"Coś poszło nie tak")

