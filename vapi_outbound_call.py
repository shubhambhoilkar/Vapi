import asyncio
import httpx
import pandas as pd
import os
import uuid
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Configuration
EXCEL_FILE = "call_data.xlsx"
CALL_QUEUE_SHEET = "call_queue"
CALL_BATCH_SHEET = "call_batches"

CONCURRENCY = 5
BATCH_DELAY_SECONDS = 300 # 5 MINS
RETRY_GAP_HOURS = 24

VAPI_API_KEY = os.getenv("VAPI_API_KEY", "")
ASSISTANT_ID = os.getenv("ASSISTANT_ID", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")

# EXCEL SETUP
def init_excel():
    if not os.path.exists(EXCEL_FILE):
        queue_df = pd.DataFrame(columns = ["sr_no",
                                            "user_name", 
                                            "phone_number", 
                                            "email", 
                                            "status", 
                                            "retry", 
                                            "next_try", 
                                            "request_id", 
                                            "updated_at"])

        batch_df = pd.DataFrame(columns= ["_id", 
                                          "name", 
                                          "phone_number", 
                                          "email", 
                                          "no_of_conversations", 
                                          "cost", 
                                          "status", 
                                          "created_at", 
                                          "updated_at", 
                                          "request_id", 
                                          "assistant_id", 
                                          "phone_number_id", 
                                          "call_type", 
                                          "retry_done"])
        
        with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
            queue_df.to_excel(writer, sheet_name=CALL_QUEUE_SHEET, index = False)
            batch_df.to_excel(writer, sheet_name= CALL_BATCH_SHEET, index = False)


def load_sheet(sheet):
    return pd.read_excel(EXCEL_FILE, sheet_name = sheet)

def save_sheet(df, sheet):
    with pd.ExcelWriter(EXCEL_FILE, engine= "openpyxl", mode = "a", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name = sheet, index = False)

# out-bound Call Execution
async def make_call(row, queue_df):
    now = datetime.now(timezone.utc)
    sr_no = row["Sr_no"]

    try :
        async with httpx.AsyncClient(timeout= 30) as client:
            payload = {
                "assistantId": ASSISTANT_ID,
                "phoneNumberId" : PHONE_NUMBER_ID,
                "customer" : {"number": f"+{int(row["phone_number"])}"},
                "assitantOverrides":{
                    "variableValues": {
                        "username": row["user_name"],
                        "userEmail": row["email"]
                    }
                }   
            }
            headers ={
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Conetent-Type" : "application/json"
            }

            # Mark in-progress
            queue_df.loc[queue_df.Sr_no == sr_no, ["status", "updated_at"]]= [
                "in-progress", now
            ]
            save_sheet(queue_df, CALL_QUEUE_SHEET)

            resp = await client.post(VAPI_API_KEY, json =payload, headers= headers)
            data = resp.json()

            outcome = "success"

            queue_df.loc[queue_df.Sr_no == sr_no, [
                "status", "request_id", "updated_at"
            ]] =[outcome, data.get("id"), now]

            save_sheet(queue_df, CALL_QUEUE_SHEET)
            await save_batch_entry(row, outcome, data.get("id"))

    except Exception as e:
        queue_df.loc[queue_df.Sr_no == sr_no, ["status", "updated_at"]] = [
            "error", now
        ]

        save_sheet(queue_df, CALL_QUEUE_SHEET)
        await save_batch_entry(row, "error", None)

# BATCH TABLE ENTRY
async def save_batch_entry(row, status, request_id):
    batch_df = load_sheet(CALL_BATCH_SHEET)
    now = datetime.now(timezone.utc)

    entry = {
        "_id": str(uuid.uuid4()),
        "name" : row["user_name"],
        "phone_number" : row["phone_number"],
        "email": row["email"],
        "no_of_conversations": 1,
        "cost":0,
        "status" : status,
        "created_at" : now,
        "updated_at" : now,
        "request_id" : request_id,
        "assistant_id" : ASSISTANT_ID,
        "phone_number_id" : PHONE_NUMBER_ID,
        "call_type" : "outbound",
        "retry_done" : status != "no-response"
    }

    batch_df = pd.concat([batch_df, pd.DataFrame([entry])], ignore_index= True)
    save_sheet(batch_df, CALL_BATCH_SHEET)

# BATCH PROCESSOR
async def process_batch():
    queue_df = load_sheet(CALL_QUEUE_SHEET)
    now =  datetime.now(timezone.utc)

    eligible = queue_df[
        (queue_df["status"].isin(["queue", "no-response"])) &
        (
            queue_df["next_try"].isna() |
            (pd.to_datetime(queue_df["next_try"], utc = True) <= now)
        )
    ].head(CONCURRENCY)

    if eligible.empty:
        return
    
    sem = asyncio.Semaphore(CONCURRENCY)

    async def wrapper(row):
        async with sem:
            await make_call(row, queue_df)

        await asyncio.gather(*[
            wrapper(row for _, row in eligible.iterrows())
        ])

# SCHEDULER
async def main():
    init_excel()
    scheduler = AsyncIOScheduler(timezone = timezone.utc)
    scheduler.add_job(process_batch, "interval", seconds = BATCH_DELAY_SECONDS)
    scheduler.start()

    print("Excel Call Scheduler Started")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
