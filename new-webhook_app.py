import os
import uvicorn
from typing import Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Body
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import ObjectId

load_dotenv()

# Configurations
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
OBD_ITEMS = os.getenv("OBD_ITEMS")
OBD_CALLS = os.getenv("OBD_CALLS")

mapping = {"main_sheet": "694baa09b068d6e7232dcb8a"}
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection_odb_calls = db[OBD_CALLS]
collection_odb_call_items = db[OBD_ITEMS]

app = FastAPI(title= "Webhook Service", version= "1.0.0")

# Helper Functions
def is_valid_object_id(value: str) -> bool:
    try:
        ObjectId(value)
        return True
    except Exception:
        return False

# Webhook Endpoint
@app.post("/api/out-bound-call-item")
async def out_bound_call_item(payload: Dict[str, Any] = Body(...)):

    # 1. Extract required fields
    source = payload.get("source", {})
    sheet_name = source.get("sheet_name")
    excel_object_id = ObjectId(mapping[sheet_name])

    if not sheet_name:
        raise HTTPException(status_code=400, detail="Sheet Name is required")

    if not is_valid_object_id(mapping[sheet_name]):
        raise HTTPException(status_code=400, detail="Invalid sheet_name ObjectId")

    # 2. Find Parent Document
    document = collection_odb_calls.find_one({"_id": excel_object_id})

    if not document:
        raise HTTPException(status_code=404, detail= f"Sheet Name {sheet_name} not found in out_bound_calls.")

    if document["_id"] == excel_object_id:
        print("Sheet available in out_bound_calls, therefore entry can be done.")

    # 3. Extract and Normalize Records
    records = payload.get("records")
    print("records: ",records)
    if not records:
        raise HTTPException(status_code=400, detail="records field is required.")
    
    # Normalize : Dict ->list
    if isinstance(records, dict):
        records = [records]

    if not isinstance(records, list):
        raise HTTPException(status_code= 400, detail= "Records must be in Dictionary or in list of Dictionary format.")

    # 4. Validate and Build documents
    documents = []
    now = datetime.now()

    for record in records:
        if not isinstance(record, dict):
            raise HTTPException(status_code=400, detail="Each record must be a dictionary.")
        
        data = record.get("data")
        print("data: ", data)

        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail= "record data must be dictionary.")
        
        doc ={
             "excel_id": excel_object_id,
             "name" : data.get("Name"),
             "phone" : str(data.get("Phone")),
             "email" : data.get("Email"),
             "row_number" : record.get("row_number"),
             "event_id" : record.get("event_id"),
             "sheet_name" : source.get("sheet_name"),
             "hash" : record.get("hash"),
             "status" :"queued",
             "no_of_conversation": 0,
             "cost": 0,
             "count_status": False,
             "isDeleted": False,
             "createdAt": now,
             "updatedAt": now
        }
        documents.append(doc)

    # 5. Insert Into Mongo DB       
    if len(documents) == 1:
        collection_odb_call_items.insert_one(documents[0])
        inserted_count = 1
    else:
        result = collection_odb_call_items.insert_many(documents)
        inserted_count = len(result.inserted_ids)

    # 6. Update Parent Collection field after Data Inserted into the Mong DB Collections
    collection_odb_calls.update_one(
        {"_id": excel_object_id},
        {
             "$set":{
                 "processed": False,
                 "updated_at": datetime.now()
                 }
        }
        
    )
    print("Parent out_bound_calls updated: processed = false.")
    
    # 7. Response
    return {
        "message" : "Records inserted and Parent updated succesfully",
        "sheet_name" : sheet_name,
        "inserted_records" : inserted_count,
        "processed" : False
    }

# Health Check (optional but recommeded)
@app.get("/health")
async def health_check():
    return {"status":"ok"}

# Main Execution
if __name__ == "__main__":
    uvicorn.run("new-webhook_app:app", host = "localhost" , port= 9900, reload= True)
