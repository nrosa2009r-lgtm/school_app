import string
import bcrypt as bct
from config.conf import get_data
from cryptography.fernet import Fernet

# Hashing password
def hash_password(password) ->str:
    pwd_bytes = password.encode("utf-8")
    hashed = bct.hashpw(pwd_bytes,bct.gensalt())
    return hashed.decode("utf-8")
# Chacking password is strong
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
    decrypted_data = key.decrypt(data).decode('utf-8')
    return decrypted_data
