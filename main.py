import os
from dotenv import load_dotenv
load_dotenv()
import uuid
import importlib
from typing import Annotated

from fastapi import FastAPI, Depends, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, insert, update

import models
import utils
from utils import DB, REDIS, AuthedUser, log

utils.setup_logging()
app = FastAPI(root_path="/finances", title="Finances")
app.mount("/static", StaticFiles(directory="static"), name="static")

def context_processors(request:Request):
    return {"user":getattr(request.state, "user", "")}
templates = Jinja2Templates(directory="templates", context_processors=[context_processors])


@app.exception_handler(utils.AuthenticationRequiredException)
async def auth_exception_handler(request:Request, exc:utils.AuthenticationRequiredException):
    accept_header = request.headers.get("accept","")
    if "text/html" in accept_header:
        current_url = request.url.path + ("?" + request.url.query if request.url.query else "") 
        return RedirectResponse(url=request.url_for("page_login").include_query_params(next=current_url), status_code=303)
    else:
        return JSONResponse(status_code=401,
                            content={"detail":"Not authenticated",
                                     "action":"redirect_to_login"})


@app.get("/")
async def page_dashboard(user:AuthedUser):
    return {"status":"Online"}


## LOGIN
@app.get("/login", response_class=HTMLResponse)
async def page_login(request:Request):
    return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={})

@app.post("/login")
async def send_login(request:Request, username:Annotated[str,Form(...)], password:Annotated[str,Form(...)], redis:REDIS, db:DB, next:Annotated[str,Form(...)]=None):
    user = await utils.authenticate_user(username, password, db)
    if not user:
        raise utils.AuthenticationRequiredException("Invalid credentials")
    session_id = str(uuid.uuid4())
    await redis.setex(f"session:{session_id}", 60*60, user)
    resp = RedirectResponse(url=next or request.url_for("page_dashboard"), status_code=303)
    resp.set_cookie(key="session_id", value=session_id, httponly=True, domain=os.getenv("DOMAIN"), samesite="strict", secure=True)
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
    res = await db.execute(query)
    accounts = {a["id"]:a["name"] for a in res.mappings().all()}
    importLog = ""
    return templates.TemplateResponse(
                request=request,
                name="import.html",
                context={"accounts":accounts,
                         "importLog":importLog})

@app.get("/manual")
async def page_manual():
    return "MANUAL HTML"
 
@app.get("/categorise")
async def page_categorise():
    return "CATEGORISE HTML"


## APIs
@app.post("/api/accounts/{account_id}/import")
async def import_raw(account_id:int, db:DB, file:Annotated[UploadFile,File(...)]):
    query = select(models.AccountConfig.parser, models.AccountConfig.raw_extension).join(models.Account, models.Account.id==models.AccountConfig.account_id).where(models.Account.id==account_id)
    res = await db.execute(query)
    account_config = res.mappings().first()

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

    imported = await parser(file, db, import_id, account_id)

    query = update(models.Import).values(**imported).where(models.Import.id==import_id)
    await db.execute(query)

    await db.commit()

    return {"success":True, "msg":"File imported successfully", "msgType":"success", "msgDur":4000}
    
