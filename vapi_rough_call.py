import httpx
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Required Configurations

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
PHONE_NUMBER_ID =  os.getenv("PHONE_NUMBER_ID")

TO_PHONE_NUMBER = "+YOUR NUMBER"

# VALIDATIONS
if not VAPI_API_KEY or not ASSISTANT_ID or not PHONE_NUMBER_ID:
    raise RuntimeError(
        "Missing VAPI credentials"
        "Set VAPI_API_KEY, ASSISTANT_ID, PHONE_NUMBER_ID"
    )

print("Starting VAPI outbound Call Test")
print("Calling Sam: ", TO_PHONE_NUMBER)
print("Time: ", datetime.utcnow().isoformat())

#API CALL
url = "https://api.vapi.ai/call/phone"

payload = {
    "assistantId": ASSISTANT_ID,
    "phoneNumberId": PHONE_NUMBER_ID,
    "customer": {
        "number" : TO_PHONE_NUMBER
    },
    "assistantOverrides" : {
        "variableValues" : {
            "username" : "Sam",
            "userEmail" : "shubham.bhoilkar@fortune4.in"
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
