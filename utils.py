from dataclasses import dataclass
from typing import Annotated
import logging
import sys

from fastapi import Request, Depends, Form
from redis.asyncio import Redis
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import get_db, get_redis
import models


class AuthenticationRequiredException(Exception):
    pass

@dataclass
class LoginFormData:
    username: str = Form(...)
    password: str = Form(...)
DB = Annotated[Session, Depends(get_db)]
REDIS = Annotated[Redis,Depends(get_redis)]

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
logger = logging.getLogger("app")

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout), # Logs to terminal
            logging.FileHandler("app.log")     # Also logs to a file
        ]
    )

def log(msg:str, level:str="info"):
    levels = {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error
    }
    levels.get(level, logger.debug)(msg)


def hash_pw(password:str) -> str:
    return pwd_context.hash(password)

def verify_password(password:str, hashed_password:str) -> bool:
    return pwd_context.verify(password, hashed_password)

async def authenticate_user(username, password, db):
    query = select(models.User.password).where(models.User.username==username)
    res = await db.execute(query)
    hashed_pw = res.scalar()
    if verify_password(password, hashed_pw):
        return username
    

async def auth_session(request:Request, redis:REDIS) -> str:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise AuthenticationRequiredException()
    
    username = await redis.get(f"session:{session_id}")
    if not username:
        raise AuthenticationRequiredException()
    
    request.state.user = username
    return username


AuthedUser = Annotated[str, Depends(auth_session)]
