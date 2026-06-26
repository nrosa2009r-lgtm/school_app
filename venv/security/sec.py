import bcrypt as bct

def hash_password(password) ->str:
    pwd_bytes = password.encode("utf-8")
    hashed = bct.hashpw(pwd_bytes,bct.gensalt())
    return hashed.decode("utf-8")