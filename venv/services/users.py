from security.sec import hash_password, password_validator, encrypt_data
from database.db import Users,async_session , is_exist
from log.log_generator import create_log

async def add_user(name:str,last_name:str,email:str,password:str):    
    if await is_exist(data=email,parm="email"):
        create_log(level="warning",message=f"Wykryto próbę utworzena konta które już istnieje!")
    elif await password_validator(password=password):
        create_log(level="warning",message=f"Hasło nie spełnia wymogów bepieczeństwa!")
    else:
        new_user = Users(
            name=encrypt_data(name.lower()),
            last_name=encrypt_data(last_name.lower()),
            email=encrypt_data(email),
            role="user",
            password=hash_password(password)
        )

        try:
            async with async_session.begin() as session:
             session.add(new_user)
            create_log(level="info",message=f"Pomyślnie utworzono urzytkownika-{name}.")
        except:
            create_log(level="error",message=f"Coś poszło nie tak!")

