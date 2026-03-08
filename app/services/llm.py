"""
LLM service for processing transcriptions and generating intelligent responses.
Uses OpenAI GPT-4o-mini for fast, cost-effective structured extraction.
"""

from openai import AsyncOpenAI
from app.core.config import settings
from app.services.conversation import ConversationState, GymInfo
import logging
import json
from typing import Optional

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with OpenAI LLM."""
    
    def __init__(self):
        """Initialize OpenAI client."""
        if not settings.openai_api_key:
            logger.warning("⚠️  OPENAI_API_KEY not set - LLM processing disabled")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info(f"✅ OpenAI client initialized (model: {settings.openai_model})")
    
    def is_enabled(self) -> bool:
        """Check if LLM is configured and enabled."""
        return self.client is not None
    
    async def process_transcription(
        self, 
        transcript: str, 
        conversation_state: ConversationState
    ) -> dict:
        """
        Process a transcription and extract gym information.
        
        Args:
            transcript: What the gym employee said
            conversation_state: Current conversation state
        
        Returns:
            dict with extracted_info and analysis
        """
        if not self.is_enabled():
            return {
                "error": "LLM not configured",
                "extracted_info": {}
            }
        
        try:
            # Build context from conversation history
            recent_context = conversation_state.get_recent_context(n=5)
            current_info = conversation_state.gym_info.to_dict()
            missing_fields = conversation_state.gym_info.get_missing_fields()
            
            # Create system prompt
            system_prompt = self._build_extraction_prompt(current_info, missing_fields)
            
            # Build user message
            user_message = f"""Recent conversation:
{recent_context}

Latest from gym: "{transcript}"

Extract any new information about hours, day pass pricing, classes, or drop-in policy."""
            
            # Call OpenAI with JSON mode for structured output
            response = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=500
            )
            
            # Parse response
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # Log token usage
            usage = response.usage
            logger.info(
                f"🤖 LLM processed transcription "
                f"(tokens: {usage.prompt_tokens}+{usage.completion_tokens}={usage.total_tokens})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing with LLM: {e}", exc_info=True)
            return {
                "error": str(e),
                "extracted_info": {}
            }
    
    def _build_extraction_prompt(self, current_info: dict, missing_fields: list[str]) -> str:
        """Build system prompt for information extraction."""
        return f"""You are an AI assistant analyzing phone call transcriptions with gym staff.

Your task: Extract specific information from what the gym employee says.

INFORMATION TO EXTRACT:
- hours: Operating hours (e.g., "6am-10pm Mon-Fri, 8am-8pm weekends")
- day_pass_price: Cost for a single-day pass (e.g., "$25", "Twenty-five dollars")
- classes: List of fitness classes offered (e.g., ["yoga", "spin", "pilates"])
- drop_in_policy: Policy for drop-in visits (e.g., "walk-ins welcome", "appointment required")

CURRENT INFORMATION COLLECTED:
{json.dumps(current_info, indent=2)}

STILL MISSING:
{', '.join(missing_fields) if missing_fields else 'None - we have all info!'}

INSTRUCTIONS:
1. Extract ONLY information explicitly stated in the transcript
2. Do NOT make assumptions or infer information
3. If something is unclear, mark it as null
4. Normalize prices to format like "$25"
5. Return ONLY newly extracted info (don't repeat what we already have)

RESPONSE FORMAT (JSON):
{{
    "extracted_info": {{
        "hours": "string or null",
        "day_pass_price": "string or null",
        "classes": ["list", "of", "classes"] or null,
        "drop_in_policy": "string or null"
    }},
    "confidence": "high|medium|low",
    "notes": "any clarifications or uncertainties"
}}

Example responses:

Input: "We're open from 6 in the morning until 10 at night"
Output: {{"extracted_info": {{"hours": "6am-10pm"}}, "confidence": "high", "notes": "Hours stated clearly"}}

Input: "Day passes are twenty-five bucks"
Output: {{"extracted_info": {{"day_pass_price": "$25"}}, "confidence": "high", "notes": "Price stated clearly"}}

Input: "Yeah, we have yoga and spin classes"
Output: {{"extracted_info": {{"classes": ["yoga", "spin"]}}, "confidence": "high", "notes": "Two classes mentioned"}}

Input: "Hmm, let me check on that"
Output: {{"extracted_info": {{}}, "confidence": "low", "notes": "No information provided yet"}}"""
    
    async def should_end_call(self, conversation_state: ConversationState) -> tuple[bool, str]:
        """
        Decide if we have enough information to end the call.
        
        Returns:
            (should_end, reason)
        """
        if not self.is_enabled():
            # Fallback logic without LLM
            return self._fallback_should_end(conversation_state)
        
        try:
            gym_info = conversation_state.gym_info
            missing = gym_info.get_missing_fields()
            completion = gym_info.completion_percentage()
            
            # Simple rule-based logic - only care about hours and price
            
            # If we have hours and price, we're done!
            if gym_info.hours and gym_info.day_pass_price:
                return True, "Got hours and price - we're good!"
            
            # If we've had 6+ exchanges and still missing info, give up
            if conversation_state.transcriptions_processed >= 6:
                return True, "Max transcriptions reached"
            
            # Keep going
            return False, f"Still need info"
            
        except Exception as e:
            logger.error(f"Error in should_end_call: {e}")
            return False, "Error in decision logic"
    
    def _fallback_should_end(self, conversation_state: ConversationState) -> tuple[bool, str]:
        """Fallback logic when LLM is not configured."""
        gym_info = conversation_state.gym_info
        
        # End if we have hours and price
        if gym_info.hours and gym_info.day_pass_price:
            return True, "Got hours and price"
        
        # End after 6 transcriptions (shorter call)
        if conversation_state.transcriptions_processed >= 6:
            return True, "Max transcriptions reached"
        
        return False, "Collecting information"
    
    async def generate_response(self, conversation_state: ConversationState) -> Optional[str]:
        """
        Generate an appropriate response based on conversation state.
        Decides what to ask next or how to end the call.
        
        Args:
            conversation_state: Current conversation state
        
        Returns:
            Text response to speak, or None if shouldn't speak
        """
        if not self.is_enabled():
            return self._fallback_generate_response(conversation_state)
        
        try:
            gym_info = conversation_state.gym_info
            missing_fields = gym_info.get_missing_fields()
            recent_context = conversation_state.get_recent_context(n=5)
            
            if should_end:
                return "Thanks!"
            
            # FIRST MESSAGE: Opening greeting with AI disclosure
            if conversation_state.transcriptions_processed == 0:
                return "Hey! Um... this is an AI calling on behalf of a visitor... I was just wondering if you could help me out real quick with your hours?"
            
            # After gym has spoken, use LLM to decide next question
            # Build list of what AI has already asked
            ai_messages = [msg.text for msg in conversation_state.conversation_history if msg.speaker == "ai"]
            
            system_prompt = """You are a real person making a casual phone call to a gym.

Your goal: Get hours and day pass price. That's it.

SPEAKING STYLE - Sound HUMAN and INDIRECT:
- Use lots of fillers: "uh", "um", "like", "so"
- Be indirect and soft: "I was just wondering...", "if you don't mind..."
- Natural pauses with "..."
- Hesitations and politeness
- Contractions: "you're", "what's", "I'm"

RULES:
1. Keep it SHORT - 12-18 words max
2. Use 2-3 filler words per response
3. Add "..." for natural pauses
4. Be INDIRECT - don't ask directly
5. Only ask about: HOURS and DAY PASS PRICE

GOOD EXAMPLES (INDIRECT):
✅ "Hey, so um... I was just curious what your hours might be?"
✅ "Oh great! And uh... if you don't mind, what's like the day pass situation?"
✅ "Perfect! So um... I was wondering like... what time do you guys open?"
✅ "Nice! Just curious... like... what would a day pass run me?"

BAD EXAMPLES (TOO DIRECT):
❌ "What are your hours?" (too direct!)
❌ "How much is a day pass?" (too abrupt!)

Return ONLY the text to speak."""

            user_message = f"""CONVERSATION SO FAR:
{recent_context}

AI HAS ALREADY SAID:
{chr(10).join(f'- "{msg}"' for msg in ai_messages)}

INFORMATION COLLECTED:
- Hours: {gym_info.hours if gym_info.hours else '(not yet)'}
- Day pass price: {gym_info.day_pass_price if gym_info.day_pass_price else '(not yet)'}

Generate ONE short, INDIRECT response with lots of filler words. Do NOT repeat any question from "AI HAS ALREADY SAID".
ONLY ask about hours or day pass price - nothing else!
Be soft and indirect - use phrases like "I was wondering..." or "if you don't mind..."."""

            response = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.5,
                max_tokens=40
            )
            
            generated_text = response.choices[0].message.content.strip()
            
            # Clean up quotes
            if generated_text.startswith('"') and generated_text.endswith('"'):
                generated_text = generated_text[1:-1]
            
            # Safety check: Don't repeat if this exact text was already said
            if generated_text in ai_messages:
                logger.warning(f"⚠️ LLM tried to repeat: '{generated_text}' - skipping")
                return None
            
            logger.info(f"🤖 Generated: \"{generated_text}\"")
            return generated_text
            
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return self._fallback_generate_response(conversation_state)
    
    def _fallback_generate_response(self, conversation_state: ConversationState) -> Optional[str]:
        """Simple rule-based response generation when LLM is not available."""
        gym_info = conversation_state.gym_info
        
        # Check if we should end
        should_end, reason = self._fallback_should_end(conversation_state)
        if should_end:
            return "Thanks!"
        
        # Get what AI has already said to avoid repeats
        ai_messages = [msg.text.lower() for msg in conversation_state.conversation_history if msg.speaker == "ai"]
        
        def already_asked(keyword: str) -> bool:
            return any(keyword in msg for msg in ai_messages)
        
        # First message with AI disclosure
        if conversation_state.transcriptions_processed == 0:
            return "Hey! Um... this is an AI calling on behalf of a visitor... I was just wondering if you could help me out real quick with your hours?"
        
        # Only ask about hours and price - be indirect and soft
        if not gym_info.hours and not already_asked("hours"):
            return "So um... I was just curious like... what are your hours?"
        elif not gym_info.day_pass_price and not already_asked("day pass") and not already_asked("price"):
            return "Oh great! And uh... if you don't mind, what's like the day pass situation?"
        
        # We have everything
        return "Thanks!"


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

