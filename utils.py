import os
from dotenv import load_dotenv
load_dotenv()
import json
import re
from dataclasses import dataclass
from typing import Annotated
import logging
import sys

from fastapi import Request, Depends, Form
from redis.asyncio import Redis
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy import select, insert, update
from sqlalchemy.orm import selectinload, joinedload

from database import get_db, get_redis
import models


UNKNOWN_ACCOUNT_ID = os.getenv("UNKNOWN_ACCOUNT_ID")

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


def is_match(tr, rules:dict) -> int:
    for target_account_id, conditions in rules.items():
        if all(re.search(val, tr[col]) for col, val in conditions.items()):
            return target_account_id
    return UNKNOWN_ACCOUNT_ID

async def apply_rule(rule_id:int, db:AsyncSession) -> None:
    query = select(models.Rule).where(models.Rule.id==rule_id)
    log(f"Query rule:\n{query}")
    rule = (await db.execute(query)).scalar_one()
    log(f"Queried rule:\n{rule}")
    query = select(models.AccountConfig.account_id)
    log(f"Query transfer accounts:\n{query}")
    transfer_account_ids = (await db.execute(query)).scalars()
    log(f"Queried transfer accounts:\n{transfer_account_ids}")

    query = select(models.RawImport) \
            .join(models.Entry, models.Entry.raw_import_id==models.RawImport.id) \
            .where(models.RawImport.account_id==rule.account_id,
                   models.Entry.account_id==UNKNOWN_ACCOUNT_ID)
    log(f"Query transactions:\n{query}")
    transactions = (await db.execute(query)).scalars().all()
    for tr in transactions:
        log(f"Transaction:\n{tr}")
        target_id = is_match(json.loads(tr.raw_data), {rule.target_account_id:json.loads(rule.conditions)})
        log(f"Target account: {target_id} ({target_id == rule.target_account_id})")
        if target_id != rule.target_account_id:
            continue
        
        ## Update Transactions:
        ## - is_temporary = False
        query = update(models.Transaction).values(is_temporary=False).where(models.Transaction.source_raw_import_id==tr.id)
        log(f"Update Transaction:\n{query}")
        await db.execute(query)

        ## Update Entries:
        ## - account_id = rule.target_account_id

    

        