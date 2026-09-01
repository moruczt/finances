import os
from dotenv import load_dotenv
load_dotenv()
import json
import re
from dataclasses import dataclass
from typing import Annotated, Any
import logging
import sys

from fastapi import Request, Depends, Form
from redis.asyncio import Redis
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy import select, insert, update, delete
from sqlalchemy.orm import selectinload, joinedload, aliased

from database import get_db, get_redis
import models


UNKNOWN_ACCOUNT_ID = int(os.getenv("UNKNOWN_ACCOUNT_ID", "0"))

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

def log(msg:Any, level:str="info"):
    levels = {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error
    }
    levels.get(level, logger.debug)(str(msg))


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


def _condition_matches(col, val, tr):
    try:
        return re.search(str(val), str(tr[col])) is not None
    except re.error as err:
        log(f"Invalid rule pattern {val!r} for column {col!r}: {err}", "warning")
        return False

def is_match(tr, rules:dict) -> int:
    for target_account_id, conditions_list in rules.items():
        for conditions in conditions_list:
            # An empty conditions dict must never match - all() of an empty iterable is True,
            # which would otherwise match every row unconditionally.
            if conditions and all(_condition_matches(col, val, tr) for col, val in conditions.items()):
                return target_account_id
    return UNKNOWN_ACCOUNT_ID

async def get_leaf_categories(db:AsyncSession) -> dict:
    """Every account with no children of its own, excluding Unknown - the set of valid
    categorization targets shown on /categorize and offered to the AI suggestion."""
    ChildAccount = aliased(models.Account)
    query = select(models.Account.id, models.Account.path) \
            .join(ChildAccount, ChildAccount.parent_id==models.Account.id, isouter=True) \
            .where(ChildAccount.id.is_(None)) \
            .order_by(models.Account.path)
    return {c["id"]:c["path"] for c in (await db.execute(query)).mappings().all() if c["id"] != UNKNOWN_ACCOUNT_ID}

async def categorize_transaction(transaction_id:int, target_id:int, db:AsyncSession, transfer_account_ids:set=None) -> bool:
    """Categorize a single temporary transaction's non-base leg as target_id, merging with an
    already-confirmed counterpart transfer entry instead of duplicating it if one is found.
    Returns False if the transaction doesn't exist / isn't a base-having temporary transaction."""
    if transfer_account_ids is None:
        query = select(models.AccountConfig.account_id)
        transfer_account_ids = set((await db.execute(query)).scalars())

    query = select(models.Transaction.id, models.Transaction.date, models.Transaction.source_raw_import_id,
                   models.Entry.account_id, models.Entry.amount_huf) \
            .join(models.Entry, models.Entry.transaction_id==models.Transaction.id) \
            .where(models.Transaction.id==transaction_id,
                   models.Entry.is_base==True)
    base = (await db.execute(query)).mappings().one_or_none()
    if not base:
        return False

    merged_entry_id = None
    if target_id in transfer_account_ids:
        # A placeholder leg for this same event, if it already exists, would be sitting on THIS
        # transaction's own account - the other side's own categorization would have pointed it
        # here. Exclude ones already resolved by an earlier merge (their raw_import_id now
        # points at their own account) so duplicate same-day/same-amount transfers each match a
        # distinct, still-unresolved counterpart.
        query = select(models.Entry.id) \
                .join(models.Transaction, models.Transaction.id==models.Entry.transaction_id) \
                .join(models.RawImport, models.RawImport.id==models.Entry.raw_import_id) \
                .where(models.Entry.account_id==base["account_id"],
                       models.Entry.is_base==False,
                       models.Transaction.is_temporary==False,
                       models.Transaction.date==base["date"],
                       models.Entry.amount_huf==base["amount_huf"],
                       models.RawImport.account_id!=models.Entry.account_id)
        merged_entry_id = (await db.execute(query)).scalar()

    if merged_entry_id:
        # An existing confirmed transaction on the target account already represents this same
        # transfer's other leg - link this raw row to it and drop the redundant one created
        # when this side was imported (cascades to its 2 entries).
        query = update(models.Entry).values(raw_import_id=base["source_raw_import_id"]).where(models.Entry.id==merged_entry_id)
        await db.execute(query)
        query = delete(models.Transaction).where(models.Transaction.id==base["id"])
        await db.execute(query)
    else:
        query = update(models.Transaction).values(is_temporary=False).where(models.Transaction.id==base["id"])
        await db.execute(query)

        query = select(models.Entry.id).where(models.Entry.raw_import_id==base["source_raw_import_id"],
                                              models.Entry.is_base==False)
        entry_ids = (await db.execute(query)).scalars().all()
        query = update(models.Entry).values(account_id=target_id).where(models.Entry.id.in_(entry_ids))
        await db.execute(query)

    return True

async def apply_rule(rule_id:int, db:AsyncSession) -> int:
    query = select(models.Rule).where(models.Rule.id==rule_id)
    rule = (await db.execute(query)).scalar_one()
    query = select(models.AccountConfig.account_id)
    transfer_account_ids = set((await db.execute(query)).scalars())

    query = select(models.RawImport) \
            .join(models.Entry, models.Entry.raw_import_id==models.RawImport.id) \
            .where(models.RawImport.account_id==rule.account_id,
                   models.Entry.account_id==UNKNOWN_ACCOUNT_ID)
    raw_imports = (await db.execute(query)).scalars().all()
    applied_count = 0
    for raw_import in raw_imports:
        target_id = is_match(json.loads(raw_import.raw_data), {rule.target_account_id:[json.loads(rule.conditions)]})
        if target_id != rule.target_account_id:
            continue

        query = select(models.Transaction.id).where(models.Transaction.source_raw_import_id==raw_import.id)
        transaction_id = (await db.execute(query)).scalar_one()
        await categorize_transaction(transaction_id, target_id, db, transfer_account_ids)

        applied_count += 1
    return applied_count

        