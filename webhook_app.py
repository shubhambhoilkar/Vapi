import os
import uvicorn
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, Body
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel , Field
from dotenv import load_dotenv

load_dotenv()

# Configurations
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
COLLECTION_NAME_1 = os.getenv("COLLECTION_NAME_1")
COLLECTION_NAME_2 = os.getenv("COLLECTION_NAME_2")

# Database (mongoDB - Async)
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[DB_NAME]
collcetion = db[COLLECTION_NAME_1]

# FastAPI App
app = FastAPI(title= "Webhook Service", version= "1.0.0")

# Data Model
class WebhookEvent(BaseModel):
    source : str | None = None
    payload : Dict[str, Any]
    received_at : datetime = Field(default_factory= datetime.now)

# Webhook Endpoint
@app.post("/api/webhook")
async def received_webhook(payload : dict = Body(...)):
    try:
        payload["received_at"] = datetime.utcnow()
        payload["source"] = "swagger-ui"

        await collcetion.insert_one(payload)

        # return {"message": "Webhook received."}
    except Exception:
        raise HTTPException(status_code=400, detail = "Invalid JSON payload")
    
    if not payload:
        raise HTTPException(status_code= 400, detail="Empty Payload")

    return {"message": "Webhook received"}

# Health Check (optional but recommeded)
@app.get("/health")
async def health_check():
    return {"status":"ok"}

# Execution
if __name__ == "__main__":
    uvicorn.run("webhook_app:app", host = "localhost" , port= 9900)
