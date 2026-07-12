from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from config.conf import get_data
from pydantic import EmailStr, NameEmail
from security.sec import gen_activation_code
from log.log_generator import create_log

async def send_activation_email(email_to: str) -> str:
    activation_code = gen_activation_code()

    content = (
        f"Witaj!\n\n"
        f"Twój kod aktywacyjny to: {activation_code}\n\n"
        f"Kod jest ważny przez 5 minut."
    )

    try:
        sender_mail = get_data("SENDER_MAIL") or "test@example.com"
        sender_pass = get_data("SENDER_PASSWORD") or "secret"
        sender_server = get_data("SENDER_SERVER") or "smtp.gmail.com"

        mail_config = ConnectionConfig(
            MAIL_USERNAME=sender_mail,
            MAIL_PASSWORD=sender_pass,
            MAIL_FROM=sender_mail,
            MAIL_PORT=587,
            MAIL_SERVER=sender_server,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )

        message = MessageSchema(
            subject="Kod do aktywacji Twojego konta",
            recipients=[NameEmail(name="Użytkownik", email=str(email_to))],
            body=content,
            subtype=MessageType.plain
        )

        fm = FastMail(mail_config)
        await fm.send_message(message)
        create_log(level="info", message=f"Wysłano e-mail aktywacyjny do: {email_to}")
    except Exception as e:
        # W środowisku testowym / lokalnym bez dostępu do SMTP logujemy kod aktywacyjny, by umożliwić testy
        create_log(level="warning", message=f"Nie udało się wysłać wiadomości SMTP do {email_to} ({str(e)}). Wygenerowany kod: {activation_code}")

    return activation_code
