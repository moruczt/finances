from io import BytesIO
import hashlib
import json

from openpyxl import load_workbook
from fastapi import UploadFile
from sqlalchemy import select

import models
from utils import log


def parse_otp_szep(file:UploadFile, db, import_id:int):
    hashes = []
    fingerprints = []
    hash_cols = ["Dátum","Alszámla","Jóváírás","Terhelés","Ellenoldali név","Jogcím"]
    with BytesIO(file.read()) as f:
        wb = load_workbook(f, read_only=True, data_only=True, keep_links=False)
        ws = wb[wb.sheetnames[0]]

        headers = {}
        data = []
        for r, row in enumerate(ws.iter_rows(max_col=8, values_only=True)):
            for c, col in enumerate(row):
                if not r:
                    headers[c] = col
                else:
                    data.append({headers[c]:col})
    
    tr_data = {}
    for tr in data:
        hash_base = "|".join((tr[hc] for hc in hash_cols))
        hash = hashlib.sha256(hash_base.encode()).hexdigest()
        occurence = hashes.count(hash)
        fingerprint_base = f"{hash_base}|{occurence}"
        fingerprint = hashlib.sha256(fingerprint_base.encode()).hexdigest()
        fingerprints.append(fingerprint)
        tr_data[fingerprint] = json.dumps(tr)

    query = select(models.RawImport.row_hash).where(models.RawImport.row_hash.in_(fingerprints))
    existings = set(db.execute(query).scalars())
    for row_hash, raw_data in tr_data.items():
        if row_hash in existings:
            log(f"HASH FOUND: {row_hash}\n{raw_data}")
            continue

    return