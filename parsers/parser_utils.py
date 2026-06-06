import json
from collections import defaultdict

from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio.session import AsyncSession
import pandas as pd
from pandas import DataFrame

import models
from utils import log
import utils


async def import_trs(data:DataFrame, db:AsyncSession, import_id:int, account_id:int):
    query = select(models.RawImport.row_hash).where(models.RawImport.row_hash.in_(data["_fingerprint"].tolist()))
    existings = set((await db.execute(query)).scalars())
    orig_size = data.shape[0]
    data = data[~data["_fingerprint"].isin(existings)]
    if not data.size:
        return {"success":True, "row_count":orig_size, "imported_count":0, "min_date":None, "max_date":None}
    data["_source"] = "import"
    import_data = data[filter(lambda c: not c.startswith("_"), data.columns)].fillna("").apply(lambda tr: json.dumps(tr.to_dict()), axis=1).to_frame("raw_data")
    import_data["account_id"] = account_id
    import_data["row_hash"] = data["_fingerprint"]
    import_data["import_id"] = import_id
    query = insert(models.RawImport).values(import_data.to_dict("records")).returning(models.RawImport.id, models.RawImport.row_hash)
    ids = pd.DataFrame((await db.execute(query)).mappings().all())
    data = data.merge(ids, left_on="_fingerprint", right_on="row_hash")
    data.drop(["row_hash"], axis=1, inplace=True)
    data.rename({"id":"_raw_id"}, axis=1, inplace=True)

    query = select(models.Rule.target_account_id, models.Rule.conditions).where(models.Rule.account_id==account_id)
    rules = defaultdict(list)
    for r in (await db.execute(query)).mappings().all():
        rules[r["target_account_id"]].append(json.loads(r["conditions"]))
    query = select(models.AccountConfig.account_id)
    transfer_account_ids = (await db.execute(query)).scalars()
    log(rules)
    data["_target_account_id"] = data.apply(lambda tr: utils.is_match(tr, rules), axis=1)
    log(data[["Ellenoldali név","_target_account_id"]])

    for _, tr in data.iterrows():
        direction = None
        if tr["_target_account_id"] in transfer_account_ids:
            ##TODO: TEST IT !!!
            query = select(models.Entry.id).join(models.Transaction, models.Transaction.id==models.Entry.transaction_id).where(models.Transaction.is_temporary==True,
                                                  models.Transaction.date==tr["_date"],
                                                  models.Entry.account_id==account_id,
                                                  models.Entry.amount_huf==-tr["_amount_huf"])
            entry_id = (await db.execute(query)).scalar()
            if entry_id:
                query = update(models.Entry).values(raw_import_id=tr["_raw_id"]).where(models.Entry.id==entry_id)
                await db.execute(query)
                continue
            direction = "TRANSFER"
            
        query = insert(models.Transaction).values(date=tr["_date"],
                                                  description=tr["_description"],
                                                  direction=direction or ("INCOMING" if tr["_amount"] > 0 else "OUTGOING"),
                                                  source_raw_import_id=tr["_raw_id"],
                                                  source="import",
                                                  is_temporary=tr["_target_account_id"]==utils.UNKNOWN_ACCOUNT_ID).returning(models.Transaction.id)
        tr["_tr_id"] = (await db.execute(query)).scalar_one()

        entry_data = [{"transaction_id":tr["_tr_id"],
                        "account_id":account_id,
                        "raw_import_id":tr["_raw_id"],
                        "is_base":True,
                        "amount_huf":tr["_amount"],
                        "amount_orig":tr["_amount_orig"],
                        "exchange_rate":tr["_exchange_rate"],
                        "currency":tr["_currency"]},
                      {"transaction_id":tr["_tr_id"],
                        "account_id":tr["_target_account_id"],
                        "raw_import_id":tr["_raw_id"],
                        "is_base":False,
                        "amount_huf":-tr["_amount"],
                        "amount_orig":-tr["_amount_orig"],
                        "exchange_rate":tr["_exchange_rate"],
                        "currency":tr["_currency"]}]
        query = insert(models.Entry).values(entry_data)
        await db.execute(query)
    
    return {"success":True, "row_count":orig_size, "imported_count":data.shape[0], "min_date":data["_date"].min(), "max_date":data["_date"].max()}
