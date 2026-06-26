import bcrypt as bct

async def hash_password(password):
    hashed = bct.hashpw(password,bct.gensalt())
    return hashed