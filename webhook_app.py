
import os
import uvicorn
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel , Field

# Configurations
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "OCR_Database"
COLLECTION_NAME = "Vapi_webhook"

# Database (mongoDB - Async)
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[DB_NAME]
collcetion = db[COLLECTION_NAME]

# FastAPI App
app = FastAPI(title= "Webhook Service", version= "1.0.0")

# Data Model
class WebhookEvent(BaseModel):
    source : str | None = None
    payload : Dict[str, Any]
    received_at : datetime = Field(default_factory= datetime.now)

# Webhook Endpoint
@app.post("/api/webhook")
async def received_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail = "Invalid JSON payload")
    
    if not payload:
        raise HTTPException(status_code= 400, detail="Empty Payload")
    
    event = WebhookEvent(
        source= request.headers.get("user-agent"),
        payload= payload
    )

    await collcetion.insert_one(event.model_dump())

    return {"message": "Webhook received"}

# Health Check (optional but recommeded)
@app.get("/health")
async def health_check():
    return {"status":"ok"}

# Execution
if __name__ == "__main__":
    uvicorn.run("webhok_app:app", host = "localhost" , port= 9900)
