from io import BytesIO
import hashlib

import pandas as pd
from pandas import DataFrame
from fastapi import UploadFile


HASH_COLS = ["Dátum","Alszámla","Jóváírás","Terhelés","Ellenoldali név","Jogcím"]


async def parse_otp_szep(file:UploadFile) -> DataFrame:
    with BytesIO(await file.read()) as f:
        data = pd.read_excel(f)

    data["_hash"] = data.apply(lambda tr: hashlib.sha256("|".join(str(tr[hc]) for hc in HASH_COLS).encode()).hexdigest(), axis=1)
    data["_occurence"] = data.groupby("_hash").cumcount()
    data["_fingerprint"] = data.apply(lambda tr: hashlib.sha256(f"{tr['_hash']}|{tr['_occurence']}".encode()).hexdigest(), axis=1)
    data["_date"] = data["Dátum"]
    data["_description"] = ""
    data["_amount"] = data["Jóváírás"].fillna(0) - data["Terhelés"].fillna(0)
    data["_amount_orig"] = data["_amount"]
    data["_currency"] = "HUF"
    data["_exchange_rate"] = 1
    return data
