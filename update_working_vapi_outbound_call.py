import pandas as pd
import os , random
import httpx
import asyncio
from datetime import datetime , timedelta
from dotenv import load_dotenv

#Load Dorenv
load_dotenv()

# Required Configurations
VAPI_API_KEY = os.getenv("VAPI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
PHONE_NUMBER_ID =  os.getenv("PHONE_NUMBER_ID")

EXCEL_FILE = "call_data.xlsx"
SHEET_NAME = "call_queue"

# BATCH CONFIG
BATCH_SIZE = 2          # 2 calls at same time
TOTAL_BATCHES = 3       # 3 batches
BATCH_DELAY_SECONDS = 10  # 10 seconds gap
RETRY_GAP_HOURS = 24 # 24 Hours time gap

# VAPI API CALL
VAPI_URL = "https://api.vapi.ai/call/phone"

DEV_RANDOM_STATUSES = ["inprogress", "failure", "success", "error", "no-response"]

# VALIDATIONS
if not VAPI_API_KEY or not ASSISTANT_ID or not PHONE_NUMBER_ID:
    raise RuntimeError(
        "Missing VAPI credentials"
        "Set VAPI_API_KEY, ASSISTANT_ID, PHONE_NUMBER_ID"
    )

# Helpers
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
        print("Error in normalising phone number. ", e )

def is_valid_for_call(status_value) -> bool:
    try:
        if pd.isna(status_value):
            return True
        status = str(status_value).strip().lower()
        return status == "" or status == "queued"

    except Exception as e:
        print("Error in validating status. ", e )

# LOAD EXCEL
def load_excel():
    return pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME, dtype=str)

def save_excel(df):
    df.to_excel(EXCEL_FILE, sheet_name = SHEET_NAME, index = False)

    
# Dev: Async Status Update
async def dev_update_status_async(sr_no):
    await asyncio.sleep(random.randint(2,5))

    df = load_excel()
    random_status = random.choice(DEV_RANDOM_STATUSES)

    df.loc[df["sr_no"].astype(str) == str(sr_no), "status"] = random_status

    # Retry scheduling
    if random_status in ["no-response", "failure", "error"]:
        next_try = datetime.utcnow() + timedelta(hours = RETRY_GAP_HOURS)
        df.loc[df["sr_no"].astype(str) == str(sr_no), "next_try"] = next_try.isoformat()

        save_excel(df)
        print(
            f"DEV UPDATE | sr_no= {sr_no}"
            f"status = {random_status}"
        )
        

# MAKE SINGLE CALL
async def make_call(rows):
    try:
        phone = normalize_phone(rows["phone_number"])

        print("Starting VAPI outbound Call Test")
        print("Calling Sam: ")
        print("Name: ", rows["user_name"])
        print("Email: ", rows["email"])
        print("Phone: ", phone)
        # print("Time: ", datetime.utcnow().isoformat())

        payload = {
            "assistantId": ASSISTANT_ID,
            "phoneNumberId": PHONE_NUMBER_ID,
            "customer": {
                "number" : phone
            },
            "assistantOverrides" : {
                "variableValues" : {
                    "username" : rows["user_name"],
                    "userEmail" :rows["email"]
                }
            }
        }

        headers ={
            "Authorization" : f"Bearer {VAPI_API_KEY}",
            "Conetent-Type" : "applications/json"
        }

        try:
            with httpx.Client(timeout= 30) as client:
                response = client.post(url = VAPI_URL , json=payload, headers=headers)
            
            print("HTTP Status: ", response.status_code)
            print("Response JSON")
            print("Response received.\n",response.json())

            # Dev Mode: 
            asyncio.create_task(dev_update_status_async(rows["sr_no"]))

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
        # tasks = [make_call(row) for _, row in batch_df.iterrows()]

        await asyncio.gather(*tasks)
        print(f"Batch {batch_number} completed")

    except Exception as e:
        print("Error in Batch Process. ", e )

#MAIN EXECUTION
async def main():
    try:
        df = load_excel()
        print("\n📄 Excel Data Read Successfully")
        print(df)
        print("-" * 60)

        # queue_df = df[df["status"].apply(is_valid_for_call)].reset_index(drop=True)
        valid_df = df[df["status"].apply(is_valid_for_call)].reset_index(drop=True)
        valid_df = valid_df.head(BATCH_SIZE * TOTAL_BATCHES)
    
        if valid_df.empty:
            print("No Valid records found for Call")
            exit()

        # queue_df = queue_df.head(BATCH_SIZE * TOTAL_BATCHES)

        batches = [
            valid_df.iloc[i:i + BATCH_SIZE]
            for i in range(0, len(valid_df), BATCH_SIZE)
        ]
    except Exception as e:
        print("Fail to get the Data")

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
