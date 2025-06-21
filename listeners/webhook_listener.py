import json
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional

app = FastAPI()

class WebhookPayload(BaseModel):
    event_type: str
    charge_id: str
    customer_id: str
    amount: float
    currency: str
    status: str
    payment_method: Optional[str] = None
    external_charge_id: Optional[str] = None
    split_instructions: Optional[Dict[str, Any]] = None
    created_at: str
    metadata: Optional[Dict[str, Any]] = None


@app.post("/api/webhook")
async def webhook_listener(payload: WebhookPayload):
    """
    Listen for webhook events from the Payments API
    """
    print(f"Received webhook event: {payload.event_type}")
    # Pydantic automatically validates the payload, so we can access attributes directly
    print(payload.model_dump_json(indent=2))

    # Process the event based on its type
    if payload.event_type == "charge.succeeded":
        # Handle successful charge
        print("Processing successful charge...")
    elif payload.event_type == "charge.failed":
        # Handle failed charge
        print("Processing failed charge...")

    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001) 