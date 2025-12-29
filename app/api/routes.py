from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
import uuid
from datetime import datetime, timezone
from app.api.twilio import router as twilio_router
from app.core.config import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
router.include_router(twilio_router)

class CreateCallRequest(BaseModel):
    phone_number: str = Field(..., description="E.164 preferred, e.g. +14155552671")
    gym_name: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    preferred_language: Optional[str] = None

class CreateCallResponse(BaseModel):
    call_id: str
    status: str
    twilio_call_sid: Optional[str] = None
    created_at: str

# MVP in-memory placeholder. We'll replace with Redis.
_CALLS: dict[str, dict] = {}

@router.post("/calls", response_model=CreateCallResponse)
async def create_call(req: CreateCallRequest):
    """
    Initiate an outbound call to a gym.
    
    This will:
    1. Call Twilio API to initiate the call
    2. When the gym answers, Twilio will POST to /v1/twilio/voice
    3. Our webhook returns TwiML to start audio streaming
    4. The WebSocket at /v1/twilio/stream handles the conversation
    """
    call_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Validate Twilio credentials are configured
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        raise HTTPException(
            status_code=500,
            detail="Twilio credentials not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN."
        )
    
    if not settings.twilio_from_number:
        raise HTTPException(
            status_code=500,
            detail="Twilio phone number not configured. Set TWILIO_FROM_NUMBER."
        )
    
    try:
        # Initialize Twilio client
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        
        # Make the outbound call
        # When the call is answered, Twilio will POST to our webhook
        logger.info(f"Initiating call to {req.phone_number} for gym: {req.gym_name or 'Unknown'}")
        
        call = client.calls.create(
            to=req.phone_number,
            from_=settings.twilio_from_number,
            url=f"{settings.public_base_url}/v1/twilio/voice",  # Twilio calls this when answered
            method='POST',
            status_callback=f"{settings.public_base_url}/v1/twilio/status",  # Optional: call status updates
            status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
            status_callback_method='POST',
        )
        
        logger.info(f"Call initiated successfully. Twilio SID: {call.sid}, Status: {call.status}")
        
        # Store call metadata
        _CALLS[call_id] = {
            "call_id": call_id,
            "twilio_call_sid": call.sid,
            "status": call.status,
            "created_at": now,
            "request": req.model_dump(),
            "result": None,
        }
        
        return {
            "call_id": call_id,
            "status": call.status,
            "twilio_call_sid": call.sid,
            "created_at": now
        }
    
    except TwilioRestException as e:
        logger.error(f"Twilio API error: {e.msg} (Code: {e.code})")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate call: {e.msg}"
        )
    except Exception as e:
        logger.error(f"Unexpected error initiating call: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to initiate call"
        )

@router.get("/calls/{call_id}")
def get_call(call_id: str):
    """
    Get the status and details of a call.
    """
    item = _CALLS.get(call_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Call {call_id} not found")
    return item


@router.post("/twilio/status")
async def twilio_status_callback(request: Request):
    """
    Twilio calls this endpoint with status updates during the call lifecycle.
    Events: initiated, ringing, answered, completed
    """
    try:
        form_data = await request.form()
        data = dict(form_data)
        
        call_sid = data.get("CallSid")
        call_status = data.get("CallStatus")
        
        logger.info(f"Call status update - SID: {call_sid}, Status: {call_status}")
        logger.debug(f"Full status data: {data}")
        
        # Update the call record if we can find it
        for call_id, call_data in _CALLS.items():
            if call_data.get("twilio_call_sid") == call_sid:
                call_data["status"] = call_status
                call_data["last_updated"] = datetime.now(timezone.utc).isoformat()
                logger.info(f"Updated call {call_id} status to {call_status}")
                break
        
        return {"ok": True}
    
    except Exception as e:
        logger.error(f"Error processing status callback: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}