import string
import bcrypt as bct
from cryptography.fernet import Fernet
def hash_password(password) ->str:
    pwd_bytes = password.encode("utf-8")
    hashed = bct.hashpw(pwd_bytes,bct.gensalt())
    return hashed.decode("utf-8")

async def password_validator(password) ->bool:
    if len(password)<=8:
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

def gen_key():
    key = Fernet.generate_key()
    return key