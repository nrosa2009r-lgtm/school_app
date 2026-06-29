from fastapi_mail import FastMail,MessageSchema,ConnectionConfig,MessageType
from config.conf import get_data
from pydantic import EmailStr,NameEmail
from security.sec import gen_activation_code

mail_config = ConnectionConfig(
    MAIL_USERNAME= get_data("SENDER_MAIL"),
    MAIL_PASSWORD=get_data("SENDER_PASSWORD"),
    MAIL_FROM=get_data("SENDER_MAIL"),
    MAIL_PORT=587,
    MAIL_SERVER=get_data("SENDER_SERVER"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)
async def send_activation_email(email_to: EmailStr) -> str:
    activation_code = gen_activation_code()

    content = (
        f"Witaj!\n\n"
        f"Twój kod aktywacyjny to: {activation_code}\n\n"
        f"Kod jest ważny przez 5 minut."
    )

    message = MessageSchema(
        subject="Kod do aktywacji Twojego konta",
        recipients=[NameEmail(name="Użytkownik", email=str(email_to))],
        subtype=MessageType.plain
    )

    fm = FastMail(mail_config)
    await fm.send_message(message)

    return activation_code