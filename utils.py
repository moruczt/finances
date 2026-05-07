from dataclasses import dataclass

from fastapi import Request, Depends, Form
from redis.asyncio import Redis

from database import get_redis

class AuthenticationRequiredException(Exception):
    pass

@dataclass
class LoginFormData:
    username: str = Form(...)
    password: str = Form(...)

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