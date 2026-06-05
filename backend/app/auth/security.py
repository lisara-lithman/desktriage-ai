import os
import jwt
from datetime import datetime, timedelta
from bcrypt import hashpw, gensalt, checkpw
from dotenv import load_dotenv  

#laod variables from .env file
load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET not found in environment variables")

ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict) -> str:
    # Create a clean copy of the dictionary payload
    to_encode = data.copy()
    
    # Calculate the future datetime in UTC
    expire_datetime = datetime.now(timezone.utc) + timedelta(days=1)
    
    to_encode.update({"exp": int(expire_datetime.timestamp())})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
