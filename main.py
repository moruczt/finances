import os
from dotenv import load_dotenv
load_dotenv()
import uuid

from fastapi import FastAPI, Depends, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from redis.asyncio import Redis

from database import get_db, get_redis
import models
import utils


app = FastAPI(root_path="/finances", title="Finances")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.exception_handler(utils.AuthenticationRequiredException)
async def auth_exception_handler(request:Request, exc:utils.AuthenticationRequiredException):
    accept_header = request.headers.get("accept","")
    if "text/html" in accept_header:
        return RedirectResponse(url="/login", status_code=303)
    else:
        return JSONResponse(status_code=401,
                            content={"detail":"Not authenticated",
                                     "action":"redirect_to_login"})


@app.get("/")
async def page_dashboard(user:str=Depends(utils.auth_session)):
    return {"status":"Online"}

@app.get("/login", response_class=HTMLResponse)
async def page_login(request:Request):
    return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={})

@app.post("/login")
async def send_login(username: str = Form(...), password: str = Form(...), redis:Redis=Depends(get_redis)):
    user = utils.authenticate_user(username, password)
    if not user:
        raise utils.AuthenticationRequiredException("Invalid credentials")
    session_id = str(uuid.uuid4())
    await redis.setex(f"session:{session_id}", 60*60, user)
    resp = RedirectResponse(url="/dashboard", status_code=303)
    resp.set_cookie(key="session_id", value=session_id, httponly=True, domain=os.getenv("DOMAIN"), samesite="strict")
    return resp
    

@app.get("/import", response_class=HTMLResponse)
async def page_import(request:Request, db: Session = Depends(get_db)):
    accounts = {"1":"ErsteDebit",
                "2":"ErsteCredit",
                "3":"ErsteWizz",
                "4":"MbhDebit",
                "5":"MbhCredit"}
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
async def import_raw(account_id: int, db: Session = Depends(get_db), file: UploadFile = File(...)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()

    if account is None:
        return {"success":False, "msg":"Missing account", "msgType":"error", "msgDur":4000}
    
    if not file.filename.endswith((".csv",".xlsx")):
        return {"success":False, "msg":"Invalid file extension", "msgType":"error", "msgDur":4000}
    
    return {"success":True, "msg":"File imported successfully", "msgType":"success", "msgDur":4000}
    
