from io import BytesIO
import hashlib

import pandas as pd
from pandas import DataFrame
from fastapi import UploadFile


HASH_COLS = ["Amount","Booking Info","Category","Transaction Type","Partner Name","Partner Account Number","Booking Reference","Narrative","Valuation Date","Card Location","Balance"]


async def parse_erste(file:UploadFile) -> DataFrame:
    with BytesIO(await file.read()) as f:
        data = pd.read_csv(f, sep=";", thousands=",", decimal=".", encoding="utf-16", date_format="%Y.%m.%d", parse_dates=["Valuation Date"])

    data["_hash"] = data.apply(lambda tr: hashlib.sha256("|".join(str(tr[hc]) for hc in HASH_COLS).encode()).hexdigest(), axis=1)
    data["_occurence"] = data.groupby("_hash").cumcount()
    data["_fingerprint"] = data.apply(lambda tr: hashlib.sha256(f"{tr['_hash']}|{tr['_occurence']}".encode()).hexdigest(), axis=1)
    data["_date"] = data["Valuation Date"]
    data["_description"] = ""
    data["_amount"] = data["Amount"]
    data["_amount_orig"] = data["_amount"]
    data["_currency"] = "HUF"
    data["_exchange_rate"] = 1
    return data
