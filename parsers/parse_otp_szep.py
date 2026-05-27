from io import BytesIO
import hashlib
import json

from openpyxl import load_workbook
from fastapi import UploadFile
from sqlalchemy import select, insert

import models
from utils import log


async def parse_otp_szep(file:UploadFile, db, import_id:int, account_id:int) -> dict:
    hash_cols = ["Dátum","Alszámla","Jóváírás","Terhelés","Ellenoldali név","Jogcím"]

    dates = []
    headers = {}
    data = []
    with BytesIO(file.read()) as f:
        wb = load_workbook(f, read_only=True, data_only=True, keep_links=False)
        ws = wb[wb.sheetnames[0]]

        for r, row in enumerate(ws.iter_rows(max_col=8, values_only=True)):
            for c, col in enumerate(row):
                if not r:
                    headers[c] = col
                else:
                    data.append({headers[c]:col})
                    if headers[c] == "Dátum":
                        dates.append(col)
    
    
    tr_data = {}
    hashes = []
    fingerprints = []
    for tr in data:
        hash_base = "|".join((tr[hc] for hc in hash_cols))
        hash = hashlib.sha256(hash_base.encode()).hexdigest()
        occurence = hashes.count(hash)
        fingerprint_base = f"{hash_base}|{occurence}"
        fingerprint = hashlib.sha256(fingerprint_base.encode()).hexdigest()
        fingerprints.append(fingerprint)
        tr_data[fingerprint] = json.dumps(tr)

    query = select(models.RawImport.row_hash).where(models.RawImport.row_hash.in_(fingerprints))
    existings = set(await db.execute(query).scalars())
    for row_hash, raw_data in tr_data.items():
        if row_hash in existings:
            log(f"HASH FOUND: {row_hash}\n{raw_data}")
            continue

        query = insert(models.RawImport).values(account_id=account_id,
                                                raw_data=raw_data,
                                                row_hash=row_hash,
                                                import_id=import_id).returning(models.RawImport.id)
        res = await db.execute(query)
        raw_import_id = res.scalar_one()

    return {"success":True, "row_count":len(fingerprints), "imported_count":len(fingerprints)-len(existings), "min_date":min(dates), "max_date":max(dates)}