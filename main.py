
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .database import get_db
from . import models


app = FastAPI(title="Finances")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def page_dashboard():
    return {"status":"Online"}

@app.get("/import", response_class=HTMLResponse)
async def page_import(request:Request):
    return templates.TemplateResponse(
                request=request,
                name="import.html")

@app.get("/manual")
async def page_manual():
    return "MANUAL HTML"
 
@app.get("/categorise")
async def page_categorise():
    return "CATEGORISE HTML"