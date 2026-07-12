"""
QR Code Service - generowanie, weryfikacja i skanowanie kodów QR
do odbierania zamówień na stołówce.
"""
import qrcode
import io
import base64
from typing import Optional
from security.sec import generate_qr_data, verify_qr_data
from database.db import async_session, Orders, Users, Schools
from sqlalchemy import select
from log.log_generator import create_log


def generate_qr_image_base64(order_id: int, user_id: int, school_id: Optional[int] = None) -> str:
    """
    Generuje obraz QR kodu jako base64 PNG.
    Używany przez API do zwracania inline obrazów.
    """
    qr_data = generate_qr_data(order_id, user_id, school_id)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_base64}"


async def verify_order_qr(qr_data: str, scanner_user_id: int) -> dict:
    """
    Weryfikuje kod QR zamówienia przy odbiorze na stołówce.
    Sprawdza poprawność podpisu, status zamówienia i uprawnienia skanującego.
    """
    payload = verify_qr_data(qr_data)
    if not payload:
        create_log(level="warning", message=f"Nieprawidłowy podpis QR podczas skanowania przez user ID {scanner_user_id}")
        return {"status": "error", "message": "Nieprawidłowy kod QR (naruszenie podpisu)."}

    order_id = payload.get("order_id")
    if not order_id:
        return {"status": "error", "message": "Brak ID zamówienia w kodzie QR."}

    async with async_session() as session:
        # Sprawdź uprawnienia skanującego
        scanner = await session.get(Users, scanner_user_id)
        if not scanner or scanner.role not in ["admin", "rootadmin", "staff"]:
            return {"status": "error", "message": "Brak uprawnień do weryfikacji zamówień."}

        order = await session.get(Orders, order_id)
        if not order:
            return {"status": "error", "message": "Zamówienie nie istnieje."}

        if order.status == "cancelled":
            return {"status": "error", "message": "Zamówienie zostało anulowane."}

        if order.qr_verified:
            return {"status": "error", "message": "Kod QR został już wykorzystany."}

        # Pobierz dane użytkownika
        user = await session.get(Users, order.user_id)

        # Oznacz jako zweryfikowane
        order.qr_verified = True
        order.status = "picked_up"
        await session.commit()

        create_log(
            level="info",
            message=f"Zamówienie ID {order_id} odebrane przez user ID {scanner_user_id}. "
                    f"Użytkownik: {user.id if user else 'N/A'}"
        )

        return {
            "status": "success",
            "message": "Zamówienie zweryfikowane i odebrane pomyślnie!",
            "order": {
                "id": order.id,
                "user_id": order.user_id,
                "total_price": float(order.total_price),
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else ""
            }
        }
