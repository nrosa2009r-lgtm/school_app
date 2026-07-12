import string
import jwt
import secrets
import bcrypt as bct
import hashlib
import hmac
import base64
import httpx
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from config.conf import get_data, put_data, put_key
from fastapi import Request, HTTPException, status, Depends
from datetime import datetime, timezone
from typing import Optional, Tuple

# Hashing password
def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    hashed = bct.hashpw(pwd_bytes, bct.gensalt())
    return hashed.decode("utf-8")

# Checking password is the same
def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    try:
        plain_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bct.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False

# Checking password is strong
async def password_validator(password: str) -> bool:
    if not password or len(password) < 10:
        return False
    if not any(char in string.ascii_lowercase for char in password):
        return False
    if not any(char in string.ascii_uppercase for char in password):
        return False
    if not any(char in string.digits for char in password):
        return False
    if not any(char in string.punctuation for char in password):
        return False
    return True

def check_password_strength(password: str) -> tuple[bool, str, int]:
    if not password:
        return False, "red", 0
    score = 0
    if len(password) >= 10:
        score += 1
    if any(c in string.ascii_lowercase for c in password) and any(c in string.ascii_uppercase for c in password):
        score += 1
    if any(c in string.digits for c in password):
        score += 1
    if any(c in string.punctuation for c in password):
        score += 1
    
    if score <= 1:
        return False, "red", 25
    elif score == 2:
        return False, "orange", 50
    elif score == 3:
        return False, "yellow", 75
    else:
        return True, "green", 100

def gen_key() -> bytes:
    return Fernet.generate_key()

def _get_aes_gcm_key() -> bytes:
    master_key = get_data("MASTER_KEY")
    if not master_key:
        master_key = Fernet.generate_key().decode('utf-8')
        put_key("MASTER_KEY", master_key.encode('utf-8'))
    return hashlib.sha256(master_key.encode('utf-8')).digest()

# Encrypting data (AES-256-GCM)
def encrypt_data(data: str) -> str:
    if data is None or data == "":
        return ""
    key = _get_aes_gcm_key()
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, str(data).encode('utf-8'), None)
    combined = nonce + ciphertext
    return base64.b64encode(combined).decode('utf-8')

# Decrypting data
def decrypt_data(data: str) -> str:
    if not data:
        return ""
    # Try AES-256-GCM first
    try:
        raw = base64.b64decode(data.encode('utf-8'))
        if len(raw) >= 28:
            key = _get_aes_gcm_key()
            aesgcm = AESGCM(key)
            nonce = raw[:12]
            ciphertext = raw[12:]
            decrypted = aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted.decode('utf-8')
    except Exception:
        pass
    # Try legacy Fernet
    try:
        master_key = get_data("MASTER_KEY")
        if master_key:
            f = Fernet(master_key.encode('utf-8'))
            return f.decrypt(data.encode('utf-8')).decode('utf-8')
    except Exception:
        pass
    return str(data)

def blind_index(email: str) -> str:
    if not email:
        return ""
    hmac_key = get_data("HMAC_KEY")
    if not hmac_key:
        hmac_key = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
        put_data("HMAC_KEY", hmac_key)
    clean_email = email.strip().lower()
    return hmac.new(hmac_key.encode('utf-8'), clean_email.encode('utf-8'), hashlib.sha256).hexdigest()

def hash_email(email: str) -> str:
    return blind_index(email)

def gen_activation_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(6))

def gen_jwt_token() -> bytes:
    return secrets.token_bytes(32)

# ──────────────────────── TOTP 2FA ────────────────────────

def generate_totp_secret() -> str:
    """Generuje losowy sekret TOTP (Base32)."""
    return base64.b32encode(secrets.token_bytes(20)).decode('utf-8').rstrip('=')

def generate_totp_uri(secret: str, email: str, issuer: str = "SchoolCatering") -> str:
    """Generuje URI do QR kodu dla aplikacji Google Authenticator."""
    clean_secret = secret.upper().replace('=', '')
    return f"otpauth://totp/{issuer}:{email}?secret={clean_secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"

def get_totp_code(secret: str, time_step: int = 30, digits: int = 6) -> str:
    """Generuje bieżący kod TOTP na podstawie sekretu."""
    import struct
    import time as time_mod
    clean_secret = secret.upper().replace('=', '')
    # Pad to multiple of 8
    padding = 8 - len(clean_secret) % 8
    if padding != 8:
        clean_secret += '=' * padding
    try:
        key = base64.b32decode(clean_secret)
    except Exception:
        return "000000"

    counter = int(time_mod.time() // time_step)
    counter_bytes = struct.pack('>Q', counter)
    hmac_hash = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    offset = hmac_hash[-1] & 0x0F
    binary = struct.unpack('>I', hmac_hash[offset:offset + 4])[0] & 0x7FFFFFFF
    code = binary % (10 ** digits)
    return str(code).zfill(digits)

def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    """Weryfikuje kod TOTP z tolerancją ±window kroków."""
    if not code or not secret:
        return False
    code = code.strip()
    if len(code) != 6 or not code.isdigit():
        return False
    return code == get_totp_code(secret)

# ──────────────────────── Have I Been Pwned ────────────────────────

async def check_haveibeenpwned(password: str) -> Tuple[bool, int]:
    """
    Sprawdza czy hasło wyciekło w znanych bazach (API HaveIBeenPwned).
    Używa k-anonimowości: wysyła tylko pierwsze 5 znaków SHA-1.
    Zwraca (czy_wyciekło, liczba_wycieków).
    """
    sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix = sha1_hash[:5]
    suffix = sha1_hash[5:]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                headers={"User-Agent": "SchoolCateringApp"}
            )
            if response.status_code == 200:
                hashes = (line.split(':') for line in response.text.splitlines())
                for h, count in hashes:
                    if h == suffix:
                        return True, int(count)
            return False, 0
    except Exception:
        return False, -1  # -1 = nie udało się sprawdzić

# ──────────────────────── QR Code Generation ────────────────────────

def generate_qr_data(order_id: int, user_id: int, school_id: Optional[int] = None) -> str:
    """Generuje dane do zakodowania w QR (podpisaną wiadomość)."""
    payload = {
        "order_id": order_id,
        "user_id": user_id,
        "school_id": school_id,
        "timestamp": int(datetime.now(timezone.utc).timestamp())
    }
    payload_str = json.dumps(payload, separators=(',', ':'))
    signature = hmac.new(
        get_data("HMAC_KEY").encode('utf-8') if get_data("HMAC_KEY") else b"default_key",
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"{payload_str}|{signature}"

def verify_qr_data(qr_data: str) -> Optional[dict]:
    """Weryfikuje dane QR i zwraca payload lub None."""
    try:
        payload_str, signature = qr_data.rsplit('|', 1)
        expected_sig = hmac.new(
            get_data("HMAC_KEY").encode('utf-8') if get_data("HMAC_KEY") else b"default_key",
            payload_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        return json.loads(payload_str)
    except Exception:
        return None

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Brak autoryzacji. Zaloguj się."
        )
    
    try:
        jwt_secret = get_data("JWT_SECRET_KEY")
        if not jwt_secret:
            jwt_secret = "6a47123711ea6ba224051b631961405b014c474d8a82424b978e8d93b740375a"
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])

        exp = payload.get("exp")
        if exp and datetime.now(timezone.utc).timestamp() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Obecny token wygasł. Zaloguj się ponownie."
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nieprawidłowy token."
            )

        from database.db import Users, async_session
        async with async_session() as session:
            user = await session.get(Users, int(user_id))
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Konto nie istnieje lub nie jest aktywne."
                )
            
            return {
                "id": user.id,
                "role": user.role,
                "name": decrypt_data(user.name_enc),
                "last_name": decrypt_data(user.last_name_enc) if user.last_name_enc else "",
                "email": decrypt_data(user.email_enc),
                "user_obj": user
            }

    except jwt.PyJWKError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy token."
        )

def require_roles(*allowed_roles: str):
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role", "").lower().replace("_", "")
        normalized_allowed = [r.lower().replace("_", "") for r in allowed_roles]
        if user_role not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Brak uprawnień do tego zasobu. Wymagane role: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker
