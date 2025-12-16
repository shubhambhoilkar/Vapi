import pandas as pd
import os
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Required Configurations
VAPI_API_KEY = os.getenv("VAPI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
PHONE_NUMBER_ID =  os.getenv("PHONE_NUMBER_ID")

EXCEL_FILE = "call_data.xlsx"
SHEET_NAME = "call_queue"

#API CALL
url = "https://api.vapi.ai/call/phone"

TO_PHONE_NUMBER = "YOUR NUMBER"

# VALIDATIONS
if not VAPI_API_KEY or not ASSISTANT_ID or not PHONE_NUMBER_ID:
    raise RuntimeError(
        "Missing VAPI credentials"
        "Set VAPI_API_KEY, ASSISTANT_ID, PHONE_NUMBER_ID"
    )

df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME, dtype=str)

print("\n📄 Excel Data Read Successfully")
print(df)
print("-" * 50)

# Process Rows

for _, rows in df.iterrows():
    status = str(rows.get("status", "")).strip().lower()
    if status != "queued":
        continue

    raw_phone = str(rows["phone_number"]).strip()
    phone = raw_phone.replace(" ", "").replace("-", "")

    if not phone.startswith("+"):
        phone = "+" + phone


    print("Starting VAPI outbound Call Test")
    print("Calling Sam: ")
    print("Name: ", rows["user_name"])
    print("Email: ", rows["email"])
    print("Phone: ", phone)
    print("Time: ", datetime.utcnow().isoformat())


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
            response = client.post(url, json=payload, headers=headers)
        
        print("HTTP Status: ", response.status_code)
        print("Response JSON")
        print(response.json())

    except Exception as e:
        print("Exception while making call: ",str(e))

    finally:
        print("Complete with calling Sam!")

        break
