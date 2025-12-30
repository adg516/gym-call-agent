"""
Conversation state management for gym call agent.
Tracks collected information and conversation flow.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime
import json


@dataclass
class GymInfo:
    """Structured information about the gym."""
    hours: Optional[str] = None
    day_pass_price: Optional[str] = None
    classes: Optional[list[str]] = None
    drop_in_policy: Optional[str] = None
    other_info: Optional[dict] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    def get_missing_fields(self) -> list[str]:
        """Return list of fields that are still None."""
        missing = []
        if self.hours is None:
            missing.append("hours")
        if self.day_pass_price is None:
            missing.append("day_pass_price")
        if self.classes is None or len(self.classes) == 0:
            missing.append("classes")
        if self.drop_in_policy is None:
            missing.append("drop_in_policy")
        return missing
    
    def is_complete(self) -> bool:
        """Check if we have all required information."""
        # Core info: hours and pricing are most important
        return self.hours is not None and self.day_pass_price is not None
    
    def completion_percentage(self) -> float:
        """Calculate what % of fields are filled."""
        total_fields = 4  # hours, price, classes, policy
        filled = sum([
            self.hours is not None,
            self.day_pass_price is not None,
            self.classes is not None and len(self.classes) > 0,
            self.drop_in_policy is not None
        ])
        return (filled / total_fields) * 100


@dataclass
class ConversationMessage:
    """A single message in the conversation."""
    speaker: str  # "gym" or "ai"
    text: str
    timestamp: str
    confidence: Optional[float] = None


@dataclass
class ConversationState:
    """State of the ongoing conversation with gym."""
    call_sid: str
    gym_name: Optional[str] = None
    gym_info: GymInfo = field(default_factory=GymInfo)
    conversation_history: list[ConversationMessage] = field(default_factory=list)
    questions_asked: list[str] = field(default_factory=list)
    transcriptions_processed: int = 0
    should_end_call: bool = False
    end_reason: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Phase 4: Speaking state management
    is_speaking: bool = False  # Is AI currently speaking?
    last_gym_speech_time: Optional[float] = None  # Timestamp of last gym speech
    last_ai_speech_time: Optional[float] = None  # Timestamp of last AI speech
    silence_frames: int = 0  # Count of consecutive silence frames
    
    def add_gym_message(self, text: str, confidence: float = None):
        """Add a message from gym staff."""
        import time
        msg = ConversationMessage(
            speaker="gym",
            text=text,
            timestamp=datetime.utcnow().isoformat(),
            confidence=confidence
        )
        self.conversation_history.append(msg)
        self.transcriptions_processed += 1
        self.last_gym_speech_time = time.time()
        self.silence_frames = 0  # Reset silence counter
    
    def add_ai_message(self, text: str):
        """Add a message from AI agent."""
        import time
        msg = ConversationMessage(
            speaker="ai",
            text=text,
            timestamp=datetime.utcnow().isoformat()
        )
        self.conversation_history.append(msg)
        self.last_ai_speech_time = time.time()
    
    def should_ai_speak(self, min_silence_seconds: float = 3.0) -> bool:
        """
        Check if AI should speak now based on silence detection.
        
        Args:
            min_silence_seconds: Minimum silence duration before AI speaks (default 3.0s)
        
        Returns:
            True if AI should speak
        """
        import time
        
        # Don't speak if already speaking
        if self.is_speaking:
            return False
        
        # Don't speak if we should end the call
        if self.should_end_call:
            return False
        
        # Always speak on first message (greeting)
        if self.transcriptions_processed == 0:
            return True
        
        # COOLDOWN: Don't speak if AI just spoke (prevent rapid repeats)
        if self.last_ai_speech_time is not None:
            time_since_ai_spoke = time.time() - self.last_ai_speech_time
            if time_since_ai_spoke < 4.0:  # 4 second cooldown after AI speaks
                return False
        
        # Check if enough time has passed since last gym speech
        if self.last_gym_speech_time is None:
            return True
        
        time_since_last_speech = time.time() - self.last_gym_speech_time
        return time_since_last_speech >= min_silence_seconds
    
    def reset_silence_counter(self):
        """Reset the silence frame counter."""
        self.silence_frames = 0
    
    def increment_silence(self):
        """Increment silence frame counter."""
        self.silence_frames += 1
    
    def get_recent_context(self, n: int = 5) -> str:
        """Get recent conversation history as formatted string."""
        recent = self.conversation_history[-n:]
        lines = []
        for msg in recent:
            speaker = "Gym" if msg.speaker == "gym" else "AI"
            lines.append(f"{speaker}: {msg.text}")
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging/storage."""
        return {
            "call_sid": self.call_sid,
            "gym_name": self.gym_name,
            "gym_info": self.gym_info.to_dict(),
            "conversation_history": [
                {
                    "speaker": msg.speaker,
                    "text": msg.text,
                    "timestamp": msg.timestamp,
                    "confidence": msg.confidence
                }
                for msg in self.conversation_history
            ],
            "questions_asked": self.questions_asked,
            "transcriptions_processed": self.transcriptions_processed,
            "should_end_call": self.should_end_call,
            "end_reason": self.end_reason,
            "started_at": self.started_at,
            "completion": f"{self.gym_info.completion_percentage():.0f}%"
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


# Global storage for active conversations (in-memory for Phase 3)
# TODO Phase 5: Move to Redis for persistence and scalability
_active_conversations: dict[str, ConversationState] = {}


def get_or_create_conversation(call_sid: str, gym_name: str = None) -> ConversationState:
    """Get existing conversation or create new one."""
    if call_sid not in _active_conversations:
        _active_conversations[call_sid] = ConversationState(
            call_sid=call_sid,
            gym_name=gym_name
        )
    return _active_conversations[call_sid]


def get_conversation(call_sid: str) -> Optional[ConversationState]:
    """Get conversation by call SID."""
    return _active_conversations.get(call_sid)


def remove_conversation(call_sid: str):
    """Remove conversation from memory (call ended)."""
    if call_sid in _active_conversations:
        del _active_conversations[call_sid]

