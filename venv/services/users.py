from security.sec import hash_password, password_validator, encrypt_data ,verify_password
from database.db import Users,async_session , is_exist,get_user_data_for_del,dell_in_db
from log.log_generator import create_log
from datetime import timedelta,datetime,timezone
from services.mail import send_activation_email
# Adding new users
async def add_user(name:str,last_name:str,email:str,password:str):    
    if await is_exist(data=email,parm="email"):
        create_log(level="warning",message=f"Wykryto próbę utworzena konta które już istnieje!")
        return 0
    elif not await password_validator(password):
        create_log(level="warning",message=f"Hasło nie spełnia wymogów bepieczeństwa!")
        return 1
    else:
        ack_code =await send_activation_email(email_to=email)

        expire_time = datetime.now(timezone.utc) + timedelta(minutes=5)
        
        
        new_user = Users(
            name=encrypt_data(name.lower()),
            last_name=encrypt_data(last_name.lower()),
            email=encrypt_data(email),
            role="user",
            password=hash_password(password),
            is_active=False,
            activation_code=encrypt_data(ack_code),
            code_expires_at=expire_time
        )

        try:
            async with async_session.begin() as session:
             session.add(new_user)
            create_log(level="info",message=f"Pomyślnie utworzono urzytkownika-{name}.")
            return 2
        except:
            create_log(level="error",message=f"Coś poszło nie tak!")
            return -1



async def del_user(email: str, password: str):
    user_id, password_db = await get_user_data_for_del(email)

    
    if user_id is None or password_db is None:
        create_log(level="error", message="Taki użytkownik nie istnieje!")
        return
    
    if not verify_password(password, password_db): 
        create_log(level="error", message="Złe hasło!")
        return 

    
    await dell_in_db(user_id)
    create_log(level="info", message=f"Usunięto użytkownika {email} z bazy danych!")


