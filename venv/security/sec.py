import string
import secrets
import bcrypt as bct
from config.conf import get_data
from cryptography.fernet import Fernet

# Hashing password
def hash_password(password) ->str:
    pwd_bytes = password.encode("utf-8")
    hashed = bct.hashpw(pwd_bytes,bct.gensalt())
    return hashed.decode("utf-8")


# Cheaking password is the same
def verify_password(plain_password: str, hashed_password: str) -> bool:

    plain_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    
    return bct.checkpw(plain_bytes, hashed_bytes)

# Chacking password is strong
async def password_validator(password) ->bool:
    if len(password)<8:
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


# Generating master key
def gen_key():
    key = Fernet.generate_key()
    return key


# Encrypting data
def encrypt_data(data):
    key = Fernet(get_data("MASTER_KEY").encode('utf-8'))
    encrypted_data = key.encrypt(data.encode())
    return encrypted_data.decode('utf-8')


# Decrypting data
def decrypt_data(data):
    key = Fernet(get_data("MASTER_KEY").encode('utf-8'))
    decrypted_data = key.decrypt(data.encode('utf-8')).decode('utf-8')
    return decrypted_data


def gen_activation_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(6))

def gen_jwt_token()->bytes:
    return secrets.token_bytes(32)