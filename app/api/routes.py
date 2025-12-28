from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
import uuid
from datetime import datetime, timezone

router = APIRouter()

class CreateCallRequest(BaseModel):
    phone_number: str = Field(..., description="E.164 preferred, e.g. +14155552671")
    gym_name: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    preferred_language: Optional[str] = None

class CreateCallResponse(BaseModel):
    call_id: str
    status: str
    created_at: str

# MVP in-memory placeholder. We'll replace with Redis.
_CALLS: dict[str, dict] = {}

@router.post("/calls", response_model=CreateCallResponse)
def create_call(req: CreateCallRequest):
    call_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    _CALLS[call_id] = {
        "call_id": call_id,
        "status": "CREATED",
        "created_at": now,
        "request": req.model_dump(),
        "result": None,
    }

    # Later: enqueue worker + start Twilio call
    return {"call_id": call_id, "status": "CREATED", "created_at": now}

@router.get("/calls/{call_id}")
def get_call(call_id: str):
    item = _CALLS.get(call_id)
    if not item:
        return {"error": "not_found", "call_id": call_id}
    return item