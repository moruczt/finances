import os
from dotenv import load_dotenv
load_dotenv()
import uuid
import importlib
import datetime as dt
import json
from typing import Annotated
from pydantic import BaseModel

from fastapi import FastAPI, Depends, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, insert, update, delete, text, func, and_
from sqlalchemy.orm import selectinload, joinedload, aliased
from sqlalchemy.exc import IntegrityError

import models
import utils
import ai
from utils import DB, REDIS, AuthedUser, log
from parsers.parser_utils import import_trs

utils.setup_logging()
app = FastAPI(root_path="/finances", title="Finances")
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_git_sha():
    git_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".git")
    try:
        with open(os.path.join(git_dir, "HEAD")) as f:
            head = f.read().strip()
        if not head.startswith("ref:"):
            return head[:7]
        ref = head.split(" ", 1)[1].strip()
        ref_path = os.path.join(git_dir, ref)
        if os.path.exists(ref_path):
            with open(ref_path) as f:
                return f.read().strip()[:7]
        with open(os.path.join(git_dir, "packed-refs")) as f:
            for line in f:
                parts = line.split()
                if len(parts) == 2 and parts[1] == ref:
                    return parts[0][:7]
    except Exception as err:
        log(f"Failed to resolve git sha: {err}", "warning")
    return "unknown"
GIT_SHA = get_git_sha()

def context_processors(request:Request):
    return {"user":getattr(request.state, "user", ""),
            "now":dt.datetime.today,
            "git_sha":GIT_SHA}
templates = Jinja2Templates(directory="templates", context_processors=[context_processors])

def format_currency(value):
    return f"{value:,.0f}".replace(",", " ") if value else 0
def format_date(value):
    return value.strftime("%Y-%m-%d")

custom_filters = {"format_currency": format_currency,
                  "format_date": format_date}
templates.env.filters.update(custom_filters)


class AccountNamePayload(BaseModel):
    name: str

class RuleItem(BaseModel):
    key: str
    regex: str

class NewRulePayload(BaseModel):
    rules: dict
    target_account_id: int
    transaction_id: int



@app.exception_handler(utils.AuthenticationRequiredException)
async def auth_exception_handler(request:Request, exc:utils.AuthenticationRequiredException):
    accept_header = request.headers.get("accept","")
    if "text/html" in accept_header:
        current_url = request.url.path + ("?" + request.url.query if request.url.query else "") 
        return RedirectResponse(url=request.url_for("page_login").include_query_params(next=current_url), status_code=303)
    else:
        return JSONResponse(status_code=401,
                            content={"success":False, "msg":"Not authenticated", "msgType":"error", "msgDur":4000})


@app.get("/", response_class=HTMLResponse)
async def page_dashboard(request:Request, db:DB, user:AuthedUser):
    last_import_sq = select(models.Import.account_id,
                            func.max(models.Import.created_at).label("last_import")) \
                     .group_by(models.Import.account_id).subquery()
    tx_stats_sq = select(models.Entry.account_id,
                         func.max(models.Transaction.date).label("last_transaction"),
                         func.count(models.Transaction.id).label("total_count"),
                         func.count(models.Transaction.id).filter(models.Transaction.is_temporary==True).label("uncategorized_count")) \
                  .join(models.Transaction, models.Transaction.id==models.Entry.transaction_id) \
                  .where(models.Entry.is_base==True) \
                  .group_by(models.Entry.account_id).subquery()

    query = select(models.Account.id,
                   models.Account.name,
                   models.Account.path,
                   last_import_sq.c.last_import,
                   tx_stats_sq.c.last_transaction,
                   tx_stats_sq.c.total_count,
                   tx_stats_sq.c.uncategorized_count) \
            .join(models.AccountConfig, models.AccountConfig.account_id==models.Account.id) \
            .outerjoin(last_import_sq, last_import_sq.c.account_id==models.Account.id) \
            .outerjoin(tx_stats_sq, tx_stats_sq.c.account_id==models.Account.id) \
            .order_by(models.Account.path)
    accounts = (await db.execute(query)).mappings().all()

    # Every transaction has exactly one is_base entry, and that entry's account is always one
    # of the importable accounts listed above, so summing the per-account totals here is exact.
    summary = {"total_count": sum(a["total_count"] or 0 for a in accounts),
              "uncategorized_count": sum(a["uncategorized_count"] or 0 for a in accounts)}

    return templates.TemplateResponse(
                request=request,
                name="dashboard.html",
                context={"accounts":accounts, "summary":summary})


## LOGIN
@app.get("/login", response_class=HTMLResponse)
async def page_login(request:Request, redis:REDIS):
    session_id = request.cookies.get("session_id")
    if session_id and await redis.get(f"session:{session_id}"):
        return RedirectResponse(url=request.url_for("page_dashboard"), status_code=303)
    return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={"error": request.query_params.get("error") == "1"})

@app.post("/login")
async def send_login(request:Request, username:Annotated[str,Form(...)], password:Annotated[str,Form(...)], redis:REDIS, db:DB, next:Annotated[str,Form(...)]=None):
    user = await utils.authenticate_user(username, password, db)
    if not user:
        # Redirect back to the login page directly (rather than raising
        # AuthenticationRequiredException) so the original next survives - that exception's
        # handler would otherwise rebuild next from this POST /login request's own path,
        # clobbering the destination the user was actually trying to reach.
        login_url = request.url_for("page_login").include_query_params(error="1")
        if next:
            login_url = login_url.include_query_params(next=next)
        return RedirectResponse(url=login_url, status_code=303)
    session_id = str(uuid.uuid4())
    expiry = os.getenv("SESSION_EXPIRY_SECS", 60*60)
    await redis.setex(f"session:{session_id}", expiry, user)
    resp = RedirectResponse(url=next or request.url_for("page_dashboard"), status_code=303)
    resp.set_cookie(key="session_id", value=session_id, httponly=True, domain=os.getenv("DOMAIN"), samesite="strict", secure=True, max_age=expiry)
    return resp

@app.post("/logout")
async def logout(request:Request, redis:REDIS):
    session_id = request.cookies.get("session_id")
    resp = RedirectResponse(url=request.url_for("page_login"), status_code=303)
    if session_id:
        resp.delete_cookie("session_id", httponly=True, domain=os.getenv("DOMAIN"), samesite="strict", secure=True)
        await redis.delete(f"session:{session_id}")
    return resp


## PAGES
@app.get("/import", response_class=HTMLResponse)
async def page_import(request:Request, db:DB, user:AuthedUser):
    query = select(models.Account.id, models.Account.name).join(models.AccountConfig, models.AccountConfig.account_id==models.Account.id)
    accounts = {a["id"]:a["name"] for a in (await db.execute(query)).mappings().all()}
    return templates.TemplateResponse(
                request=request,
                name="import.html",
                context={"accounts":accounts})

@app.get("/imports", response_class=HTMLResponse)
async def page_imports(request:Request, db:DB, user:AuthedUser):
    query = select(models.Import.created_at,
                   models.Import.file_name,
                   models.Import.row_count,
                   models.Import.imported_count,
                   models.Import.min_date,
                   models.Import.max_date,
                   models.Account.name).join(models.Account, models.Import.account_id==models.Account.id).order_by(models.Import.created_at.desc())
    imports = (await db.execute(query)).mappings().all()
    return templates.TemplateResponse(
                request=request,
                name="imports.html",
                context={"imports":imports})

@app.get("/transactions", response_class=HTMLResponse)
async def page_transactions(request:Request, db:DB, user:AuthedUser):
    query = select(models.Transaction) \
            .order_by(models.Transaction.date.desc()) \
            .limit(100) \
            .options(selectinload(models.Transaction.entries) \
                     .options(joinedload(models.Entry.raw_import),
                              joinedload(models.Entry.account)))

    transactions = (await db.execute(query)).scalars().all()
    return templates.TemplateResponse(
                request=request,
                name="transactions.html",
                context={"transactions":transactions})
 
@app.get("/categorize")
async def page_categorise(request:Request, db:DB, user:AuthedUser):
    BaseEntry = aliased(models.Entry)
    query = select(models.Transaction) \
            .join(BaseEntry, and_(BaseEntry.transaction_id==models.Transaction.id, BaseEntry.is_base==True)) \
            .where(models.Transaction.is_temporary==True) \
            .order_by(models.Transaction.date.asc(), BaseEntry.account_id.asc()) \
            .options(selectinload(models.Transaction.entries) \
                     .options(joinedload(models.Entry.account)))
    transactions = (await db.execute(query)).scalars().all()

    categories = await utils.get_leaf_categories(db)
    return templates.TemplateResponse(
                request=request,
                name="categorize.html",
                context={"transactions":transactions,
                        "categories":categories})

@app.get("/manual")
async def page_manual():
    return "MANUAL HTML"

@app.get("/config", response_class=HTMLResponse)
async def page_config(request:Request, db:DB, user:AuthedUser):
    ChildAccount = aliased(models.Account)
    query = select(models.Account.id,
                   models.Account.name,
                   models.Account.path,
                   models.Account.side,
                   func.count(ChildAccount.id).label("child_count")) \
            .outerjoin(ChildAccount, ChildAccount.parent_id==models.Account.id) \
            .group_by(models.Account.id)
    rows = (await db.execute(query)).mappings().all()

    # "side" isn't a real accounts row - it's just a label baked into every root account's own
    # path (e.g. "Expenses:Fees"). Render one virtual header per side so there's somewhere to
    # attach a "+" for adding a genuinely new top-level (parent_id=NULL) account.
    accounts = [{"id":r["id"], "name":r["name"], "path":r["path"], "side":r["side"],
                "depth":r["path"].count(":"), "has_children":r["child_count"] > 0, "is_side":False} for r in rows]
    accounts += [{"id":None, "name":side.value, "path":side.value, "side":side,
                 "depth":0, "has_children":True, "is_side":True} for side in models.AccountSide]
    accounts.sort(key=lambda a: a["path"])

    return templates.TemplateResponse(
                request=request,
                name="config.html",
                context={"accounts":accounts})

## APIs
@app.post("/api/accounts/{account_id}/import")
async def import_raw(account_id:int, request:Request, db:DB, file:Annotated[UploadFile,File(...)], user:AuthedUser):
    query = select(models.AccountConfig.parser,
                   models.AccountConfig.raw_extension) \
                   .join(models.Account, models.Account.id==models.AccountConfig.account_id) \
                   .where(models.Account.id==account_id)
    account_config = (await db.execute(query)).mappings().first()

    if account_config is None:
        return {"success":False, "msg":"Missing account", "msgType":"error", "msgDur":4000}
    
    if not file.filename.endswith(f".{account_config['raw_extension']}"):
        return {"success":False, "msg":"Invalid file extension", "msgType":"error", "msgDur":4000}
    
    try:
        parser = getattr(importlib.import_module(f"parsers.{account_config['parser']}"), account_config['parser'])
    except (ImportError, AttributeError) as err:
        log(err)
        return {"success":False, "msg":"No parser available for the  account", "msgType":"error", "msgDur":4000}

    query = insert(models.Import).values(account_id=account_id, file_name=file.filename).returning(models.Import.id)
    res = await db.execute(query)
    import_id = res.scalar_one()

    data = await parser(file)
    imported = await import_trs(data, db, import_id, account_id)
    query = update(models.Import).values(**imported).where(models.Import.id==import_id)
    await db.execute(query)

    import_log = templates.env.get_template("snippets/import_log.html").render(imported=imported, now=dt.datetime.today)
    
    await db.commit()
    return {"success":True, "msg":"File imported successfully", "msgType":"success", "msgDur":4000, "result":{"import_log":import_log}}
    
    
@app.get("/api/transactions/{transaction_id}")
async def fetch_transaction(transaction_id:int, request:Request, db:DB, user:AuthedUser):
    query = select(models.Transaction) \
            .where(models.Transaction.is_temporary==True,
                   models.Transaction.id == transaction_id) \
            .options(selectinload(models.Transaction.entries) \
                     .options(joinedload(models.Entry.raw_import),
                              joinedload(models.Entry.account)))
    tr = (await db.execute(query)).scalars().first()
    transaction = {"id": tr.id,
                   "date": tr.date.strftime("%Y-%m-%d"),
                   "description": tr.description,
                   "source_account": tr.base_account_name,
                   "amount": format_currency(tr.amount),
                   "raw_json": tr.raw_imports[0].details}
    return {"success":True, "result":{"transaction":transaction}}

@app.get("/api/transactions/{transaction_id}/suggest-category")
async def suggest_transaction_category(transaction_id:int, request:Request, db:DB, user:AuthedUser):
    query = select(models.Transaction) \
            .where(models.Transaction.is_temporary==True,
                   models.Transaction.id == transaction_id) \
            .options(selectinload(models.Transaction.entries) \
                     .options(joinedload(models.Entry.raw_import)))
    tr = (await db.execute(query)).scalars().first()
    if not tr:
        return {"success":False, "result":{"category_id":None}}

    categories = await utils.get_leaf_categories(db)
    category_id = await ai.suggest_category(tr.raw_imports[0].details, categories)

    return {"success":True, "result":{"category_id":category_id}}

@app.post("/api/accounts/{parent_id}/children")
async def add_child_account(parent_id:int, payload:AccountNamePayload, request:Request, db:DB, user:AuthedUser):
    name = payload.name.strip()
    if not name:
        return {"success":False, "msg":"Name is required", "msgType":"error", "msgDur":4000, "result":{}}
    if ":" in name:
        return {"success":False, "msg":"Account name cannot contain ':'", "msgType":"error", "msgDur":4000, "result":{}}

    query = select(models.Account.path, models.Account.side).where(models.Account.id==parent_id)
    parent = (await db.execute(query)).mappings().first()
    if not parent:
        return {"success":False, "msg":"Parent account not found", "msgType":"error", "msgDur":4000, "result":{}}

    try:
        query = insert(models.Account).values(parent_id=parent_id,
                                              name=name,
                                              side=parent["side"],
                                              path=f"{parent['path']}:{name}").returning(models.Account.id)
        new_id = (await db.execute(query)).scalar_one()
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return {"success":False, "msg":"An account with that name already exists here", "msgType":"error", "msgDur":4000, "result":{}}

    return {"success":True, "msg":"Account created", "msgType":"success", "msgDur":3000, "result":{"id":new_id}}

@app.post("/api/accounts/roots/{side}/children")
async def add_root_account(side:models.AccountSide, payload:AccountNamePayload, request:Request, db:DB, user:AuthedUser):
    name = payload.name.strip()
    if not name:
        return {"success":False, "msg":"Name is required", "msgType":"error", "msgDur":4000, "result":{}}
    if ":" in name:
        return {"success":False, "msg":"Account name cannot contain ':'", "msgType":"error", "msgDur":4000, "result":{}}

    try:
        query = insert(models.Account).values(parent_id=None,
                                              name=name,
                                              side=side,
                                              path=f"{side.value}:{name}").returning(models.Account.id)
        new_id = (await db.execute(query)).scalar_one()
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return {"success":False, "msg":"An account with that name already exists here", "msgType":"error", "msgDur":4000, "result":{}}

    return {"success":True, "msg":"Account created", "msgType":"success", "msgDur":3000, "result":{"id":new_id}}

@app.patch("/api/accounts/{account_id}")
async def rename_account(account_id:int, payload:AccountNamePayload, request:Request, db:DB, user:AuthedUser):
    name = payload.name.strip()
    if not name:
        return {"success":False, "msg":"Name is required", "msgType":"error", "msgDur":4000, "result":{}}
    if ":" in name:
        return {"success":False, "msg":"Account name cannot contain ':'", "msgType":"error", "msgDur":4000, "result":{}}

    query = select(models.Account.path, models.Account.parent_id).where(models.Account.id==account_id)
    account = (await db.execute(query)).mappings().first()
    if not account:
        return {"success":False, "msg":"Account not found", "msgType":"error", "msgDur":4000, "result":{}}

    old_path = account["path"]
    if account["parent_id"] is not None:
        query = select(models.Account.path).where(models.Account.id==account["parent_id"])
        parent_path = (await db.execute(query)).scalar_one()
        new_path = f"{parent_path}:{name}"
    else:
        new_path = name

    try:
        query = update(models.Account).values(name=name, path=new_path).where(models.Account.id==account_id)
        await db.execute(query)

        if new_path != old_path:
            # Account.path is a materialized "Root:Section:Name" string, not derived on read -
            # cascade the prefix change to every descendant.
            query = select(models.Account.id, models.Account.path)
            all_accounts = (await db.execute(query)).mappings().all()
            prefix = old_path + ":"
            for a in all_accounts:
                if a["id"] != account_id and a["path"].startswith(prefix):
                    new_child_path = new_path + a["path"][len(old_path):]
                    await db.execute(update(models.Account).values(path=new_child_path).where(models.Account.id==a["id"]))

        await db.commit()
    except IntegrityError:
        await db.rollback()
        return {"success":False, "msg":"An account with that name already exists here", "msgType":"error", "msgDur":4000, "result":{}}

    return {"success":True, "msg":"Account renamed", "msgType":"success", "msgDur":3000, "result":{}}

@app.post("/api/rules")
async def apply_rule(payload:NewRulePayload, request:Request, db:DB, user:AuthedUser):
    query = select(models.Account.id) \
            .join(models.RawImport, models.RawImport.account_id==models.Account.id) \
            .join(models.Transaction, models.Transaction.source_raw_import_id==models.RawImport.id) \
            .where(models.Transaction.id==payload.transaction_id,
                   models.Transaction.is_temporary==True)
    account_id = (await db.execute(query)).scalar_one()
    if not account_id:
        return {"success":False, "msg":"Uncategorized transaction not found", "msgType":"error", "msgDur":4000, "result":{}}

    if not payload.rules:
        # No match pattern was built - categorize only this one transaction instead of saving a
        # rule that (with no conditions to check) would otherwise match every uncategorized
        # transaction for this account.
        await utils.categorize_transaction(payload.transaction_id, payload.target_account_id, db)
        await db.commit()
        return {"success":True, "msg":"Transaction successfully categorized", "msgType":"success", "msgDur":4000, "result":{"id":None, "applied_count":1}}

    query = insert(models.Rule).values(account_id=account_id,
                                        target_account_id=payload.target_account_id,
                                        conditions=json.dumps(payload.rules)).returning(models.Rule.id)
    new_id = (await db.execute(query)).scalar_one()

    applied_count = await utils.apply_rule(new_id, db)
    await db.commit()
    return {"success":True, "msg":"Transaction successfully categorized", "msgType":"success", "msgDur":4000, "result":{"id":new_id, "applied_count":applied_count}}

@app.delete("/api/wipe")
async def wipe_db(db:DB, user:AuthedUser):
    await db.execute(delete(models.Transaction))
    await db.execute(delete(models.RawImport))
    await db.execute(delete(models.Import))
    # await db.execute(delete(models.Rule))
    await db.execute(text("SELECT setval(pg_get_serial_sequence('entries', 'id'), 1, false);"))
    await db.execute(text("SELECT setval(pg_get_serial_sequence('transactions', 'id'), 1, false);"))
    await db.execute(text("SELECT setval(pg_get_serial_sequence('raw_imports', 'id'), 1, false);"))
    await db.execute(text("SELECT setval(pg_get_serial_sequence('imports', 'id'), 1, false);"))
    # await db.execute(text("SELECT setval(pg_get_serial_sequence('rules', 'id'), 1, false);"))
    await db.commit()

    return {"success":True, "msg":"Database was successfully wiped", "msgType":"success", "msgDur":4000, "result":{}}
    