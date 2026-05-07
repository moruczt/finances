from dataclasses import dataclass

from fastapi import Request, Depends, Form
from redis.asyncio import Redis
from passlib.context import CryptContext

from database import get_redis


class AuthenticationRequiredException(Exception):
    pass

@dataclass
class LoginFormData:
    username: str = Form(...)
    password: str = Form(...)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_pw(password:str) -> str:
    return pwd_context.hash(password)

def verify_password(password:str, hashed_password:str) -> bool:
    return pwd_context.verify(password, hashed_password)

def authenticate_user(username, password):
    if username == "moruczt" and password == "admin":
        return username

async def auth_session(request:Request, redis:Redis=Depends(get_redis)) -> str:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise AuthenticationRequiredException()
    
    username = await redis.get(f"session:{session_id}")
    if not username:
        raise AuthenticationRequiredException()
    
    return username