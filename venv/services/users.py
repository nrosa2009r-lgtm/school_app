from security.sec import hash_password, password_validator, encrypt_data, verify_password, blind_index
from database.db import Users, async_session, is_exist, get_user_data_for_del, dell_in_db, get_login_data
from log.log_generator import create_log
from datetime import timedelta, datetime, timezone
from services.mail import send_activation_email

async def add_user(name: str, last_name: str, email: str, password: str) -> int:
    clean_email = email.strip().lower()
    if await is_exist(data=clean_email, parm="email"):
        create_log(level="warning", message=f"Wykryto próbę utworzenia konta które już istnieje ({clean_email})!")
        return 0
    elif not await password_validator(password):
        create_log(level="warning", message="Hasło nie spełnia wymogów bezpieczeństwa!")
        return 1
    else:
        expire_time = datetime.now(timezone.utc) + timedelta(minutes=5)
        ack_code = await send_activation_email(email_to=clean_email)
        new_user = Users(
            name_enc=encrypt_data(name.strip()),
            last_name_enc=encrypt_data(last_name.strip()),
            email_enc=encrypt_data(clean_email),
            email_hash=blind_index(clean_email),
            role="user",
            password=hash_password(password),
            is_active=False,
            activation_code_enc=encrypt_data(ack_code),
            code_expires_at=expire_time
        )
        try:
            async with async_session.begin() as session:
                session.add(new_user)
            create_log(level="info", message=f"Pomyślnie utworzono użytkownika: {name}.")
            return 2
        except Exception as e:
            create_log(level="error", message=f"Błąd bazy danych podczas tworzenia użytkownika: {str(e)}")
            return -1

async def del_user(email: str, password: str):
    clean_email = email.strip().lower()
    user_id, password_db = await get_user_data_for_del(clean_email)
    if user_id is None or password_db is None:
        create_log(level="error", message="Taki użytkownik nie istnieje!")
        return
    if not verify_password(password, password_db):
        create_log(level="error", message="Złe hasło podczas próby usunięcia!")
        return
    await dell_in_db(user_id)
    create_log(level="info", message=f"Usunięto użytkownika {clean_email} z bazy danych!")

async def login_user(email: str, password: str) -> int | Users:
    clean_email = email.strip().lower()
    user = await get_login_data(clean_email)
    if user is None:
        create_log(level="warning", message=f"Nieudana próba logowania: e-mail {clean_email} nie istnieje.")
        return 0
    if not user.is_active:
        create_log(level="warning", message=f"Próba logowania na nieaktywne konto: {clean_email}.")
        return 1
    if not verify_password(password, user.password):
        create_log(level="warning", message=f"Błędne hasło dla użytkownika: {clean_email}.")
        return 2
    create_log(level="info", message=f"Użytkownik {clean_email} zalogował się pomyślnie.")
    return user
