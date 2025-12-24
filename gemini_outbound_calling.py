import pandas as pd
import httpx
import gspread
import asyncio
import os , random
from dotenv import load_dotenv
from datetime import datetime , timedelta, timezone

# Required Configurations
VAPI_API_KEY = os.getenv("VAPI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
PHONE_NUMBER_ID =  os.getenv("PHONE_NUMBER_ID")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

EXCEL_FILE = "call_data.xlsx"
SHEET_NAME = "call_queue"

# Google Sheet Init
gc = gspread.service_account(filename = "vapi-481604-809d933f10b4.json")
sheet = gc.open_by_key("1M7Nhoh4Ms2K8uj4qcOZogvNSGZUI5OUKCrc1O5hhi0A").worksheet(SHEET_NAME)
print(sheet.get_all_records()[:1])

# Load Dotenv
load_dotenv()

# BATCH CONFIG
BATCH_SIZE = 2            # 2 calls at same time
TOTAL_BATCHES = 3         # 3 batches
BATCH_DELAY_SECONDS = 20  # 20 seconds gap
RETRY_GAP_HOURS = 24      # 24 Hours time gap

# VAPI API CALL
VAPI_URL = "https://api.vapi.ai/call/phone"

DEV_RANDOM_STATUSES = ["", "failure", "success", "error", "no-response"]

# VALIDATIONS
if not VAPI_API_KEY or not ASSISTANT_ID or not PHONE_NUMBER_ID:
    raise RuntimeError(
        "Missing VAPI credentials"
    )

# Helpers Functions
def normalize_phone(phone: str) -> str:
    try:
        phone = str(phone).strip()
        # Catch scientific notation early
        if "E+" in phone or "e+" in phone:
            raise ValueError(f"Invalid phone number from Excel: {phone}")

        phone = phone.replace(" ", "").replace("-", "")
        if not phone.startswith("+"):
            phone = "+" + phone

        if not phone[1:].isdigit():
            raise ValueError(f"Non-numeric phone number: {phone}")

        if len(phone) < 11:
            raise ValueError(f"Phone number too short: {phone}")

        return phone
    except Exception as e:
        raise ValueError(f"Phone normalization failed: {e}")
    
def parse_utc_datetime(value):
    if not value or pd.isna(value):
        return None
    
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))

        # applying UTC awareness
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)        
        return dt
    except Exception:
        return None

def get_sheet_and_index(sr_no):
    # sheet = gc.open_by_key(GOOGLE_SHEET_ID).worksheet("call_queue")
    records = sheet.get_all_records()

    for idx, row in enumerate(records, start=2):
        if str(row.get("sr_no")) == str(sr_no):
            return sheet, idx
    return None, None

def get_col_index(col_name):
    # sheet = gc.open_by_key(GOOGLE_SHEET_ID).worksheet("call_queue")
    headers = sheet.row_values(1)
    return headers.index(col_name) + 1

def get_tries(row):
    try:
        val = row.get("no_of_retry", 0)
        if pd.isna(val) or val =="":
            return 0
        return int(val)
    except Exception:
        return 0

def is_valid_for_call(row):
    raw_status = row.get("status", "")
    status = str(raw_status).strip().lower()

    tries = get_tries(row)
    if tries > 2:
        return False

    now = datetime.now(timezone.utc)

    called_at = parse_utc_datetime(row.get("called_at"))
    next_try = parse_utc_datetime(row.get("next_try"))

    # Empty or Nan or Queued  -> Call
    if (raw_status is None 
        or pd.isna(raw_status)
        or status == ""
        or status == "nan"
        or status == "queued"
    ):
        return True

    if status == "no-response":
        #condition 1: next_try exist
        if next_try:
            return next_try <= now
        
        #condition 2: fallback to called_at + 24hours
        if called_at:
            retry_time = called_at + timedelta(hours= RETRY_GAP_HOURS)
            return retry_time <= now
        return False
    
    # All Other Statuses:
    return False


# Load Google Sheet
def load_sheet():
    try:
        return pd.DataFrame(sheet.get_all_records())

    except gspread.exceptions.WorksheetNotFound:
        raise RuntimeError(f"Worksheet {SHEET_NAME} not found.")

    except gspread.exceptions.SpreadsheetNotFound:
        raise RuntimeError("Spreadsheet ID not found or not shared")

    except Exception as e:
        raise RuntimeError(f"Google Sheet Load Failed: {e}")

# Dev: Async Status Update
async def dev_update_status_async(sr_no):
    await asyncio.sleep(random.randint(2,5))

    df = load_sheet()
    random_status = random.choice(DEV_RANDOM_STATUSES)

    df.loc[df["sr_no"].astype(str) == str(sr_no), "status"] = random_status

    # Retry scheduling
    if random_status in ["success", "in-progress", "no-response", "failure", "error"]:
        next_try = datetime.now(timezone.utc) + timedelta(hours = RETRY_GAP_HOURS)
        df.loc[
            df["sr_no"].astype(str) == str(sr_no),
            "next_try"] = next_try.isoformat()

    save_sheet(df)
    print(
            f"DEV UPDATE | sr_no= {sr_no}"
            f"status = {random_status}"
        )        

# MAKE SINGLE CALL
async def make_call(rows):
    sheet, row_idx = get_sheet_and_index(sr_no)

    if not sheet:
        print(f"Row not found in Google Sheet for sr_no ={sr_no}")
        return
    
    current_tries = sheet.cell(row_idx, get_col_index("no_of_tries")).value
    current_tries = int(current_tries) if current_tries else 0

    updates = {
        "no_of_tries": current_tries + 1,
        "called_at": called_at,
        "update_at" : updated_at,
        "request_id" : request_id
    }

    try:
        phone = normalize_phone(rows["phone_number"])
        sr_no = rows["sr_no"]

        print("Starting VAPI outbound Call Test")
        print("Calling Sam: ")

        payload = {
            "assistantId": ASSISTANT_ID,
            "phoneNumberId": PHONE_NUMBER_ID,
            "customer": {
                "number" : phone},
            "assistantOverrides" : {
                "variableValues" : {
                    "username" : rows["user_name"],
                    "userEmail" :rows["email"]
                }
            }
        }

        headers ={
            "Authorization" : f"Bearer {VAPI_API_KEY}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout= 30) as client:
                response = await client.post(url = VAPI_URL , 
                                            json=payload, 
                                            headers=headers)
            
            print("HTTP Status: ", response.status_code)
            print("Response JSON")
            response_data = response.json()
            print("Response received.\n",response_data,"\n")

            # new code:
            request_id = response_data.get("id")
            called_at = response_data.get("createdAt")
            updated_at = response_data.get("updatedAt")

            # Load and update the Excel Sheet
            df = load_sheet()
            if "no_of_tries" not in df.columns:
                df["no_of_tries"] = 0
            
            mask = df["sr_no"].astype(str) == str(sr_no)

            # Increment tries
            current_tries = int(df.loc[mask, "no_of_tries"].fillna(0).iloc[0])
            df.loc[mask, "no_of_tries"] = current_tries + 1

            # Save Vapi Data:
            df.loc[mask, "called_at"] = called_at
            df.loc[mask, "request_id"] = request_id
            df.loc[mask, "updated_at"] = updated_at

            save_sheet(df)

            # Dev Mode: 
            asyncio.create_task(dev_update_status_async(sr_no))

        except Exception as e:
            print("Exception while making call: ",str(e))

    except Exception as e:
        print("Error whlie making vapi Call. ", e)
    finally:
        print("Complete Calling Exception.")

# PROCESS SINGLE BATCH
async def process_batch(batch_df, batch_number):
    try:
        print(f"\n Starting Batch {batch_number} ({len(batch_df)} concurrent calls)")
        print(batch_df[["user_name", "phone_number"]])

        tasks = []
        for _, row in batch_df.iterrows():
            tasks.append(make_call(row))

        await asyncio.gather(*tasks)
        print(f"Batch {batch_number} completed")

    except Exception as e:
        print("Error in Batch Process. ", e )

#MAIN EXECUTION
async def main():
    print("Excel Call Scheduler Started.")
    try:
        df = load_sheet()

        print("\n📄 Excel Data Read Successfully")
        print(df)
        print("-" * 60)

        valid_df = df[df.apply(is_valid_for_call, axis =1)].reset_index(drop= True)

        if valid_df.empty:
            print("No Valid records found for Call")
            return 
        
        valid_df = valid_df.head(BATCH_SIZE * TOTAL_BATCHES)
    
        batches = [
            valid_df.iloc[i:i + BATCH_SIZE]
            for i in range(0, len(valid_df), BATCH_SIZE)
        ]
    
    except Exception as e:
        print("Fail to get the Data", e )
        return

    try:
        for idx, batch in enumerate(batches[:TOTAL_BATCHES],start=1):
            await process_batch(batch, idx)

            if idx < TOTAL_BATCHES:
                print(f"\n Waiting {BATCH_DELAY_SECONDS} seconds before next batch...\n")
                await asyncio.sleep(BATCH_DELAY_SECONDS)

        print("\n All Batches copmleted successfully!")

    except Exception as e:
        print("Error in Main Execution. ", e )

# Main Run the file 
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("Fail to run the file. ", e )
