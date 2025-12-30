"""
Text-to-Speech service for generating AI responses.
Uses ElevenLabs for natural conversational voice (preferred)
or falls back to OpenAI TTS.
"""

from app.core.config import settings
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class TTSService:
    """Service for text-to-speech conversion."""
    
    def __init__(self):
        """Initialize TTS client - prefers ElevenLabs for natural voice."""
        self.use_elevenlabs = False
        self.openai_client = None
        
        # ElevenLabs first (best quality) - use pcm_24000 for clean 3:1 ratio to 8kHz
        if settings.elevenlabs_api_key:
            self.use_elevenlabs = True
            logger.info(f"✅ ElevenLabs TTS initialized (voice: {settings.elevenlabs_voice_id})")
        elif settings.openai_api_key:
            from openai import AsyncOpenAI
            self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info(f"✅ OpenAI TTS initialized (voice: {settings.tts_voice})")
        else:
            logger.warning("⚠️  No TTS API key set - TTS disabled")
    
    def is_enabled(self) -> bool:
        """Check if TTS is configured and enabled."""
        return self.use_elevenlabs or self.openai_client is not None
    
    async def text_to_speech(self, text: str) -> Optional[bytes]:
        """
        Convert text to speech audio.
        
        Args:
            text: Text to speak
        
        Returns:
            PCM audio data (16-bit, 24kHz) or None on error
        """
        if not self.is_enabled():
            logger.warning("TTS not enabled, cannot generate speech")
            return None
        
        if not text or len(text.strip()) == 0:
            logger.warning("Empty text provided, skipping TTS")
            return None
        
        if self.use_elevenlabs:
            return await self._elevenlabs_tts(text)
        else:
            return await self._openai_tts(text)
    
    async def _elevenlabs_tts(self, text: str) -> Optional[bytes]:
        """Generate speech using ElevenLabs API with optimized settings for telephony."""
        try:
            # Add version marker for deployment verification
            logger.info(f"🔊 [v2.0-PCM] ElevenLabs generating: \"{text[:50]}...\" (length: {len(text)} chars)")
            
            # Break long text into smaller chunks (ElevenLabs best practice: <800 chars)
            if len(text) > 800:
                logger.warning(f"⚠️  Text too long ({len(text)} chars), truncating to 800 for better quality")
                text = text[:797] + "..."
            
            # CRITICAL: output_format must be in URL params, not JSON body
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}?output_format=pcm_24000"
            
            headers = {
                "xi-api-key": settings.elevenlabs_api_key,
                "Content-Type": "application/json",
            }
            
            # OPTIMIZED voice settings for telephony (based on ElevenLabs best practices)
            # - Higher stability (0.7) for consistent, clear speech on phone
            # - Lower similarity (0.65) to reduce artifacts  
            # - Disable style exaggeration (0.0) to prevent distortion
            # - Enable speaker boost for phone clarity
            payload = {
                "text": text,
                "model_id": settings.elevenlabs_model,
                "voice_settings": {
                    "stability": 0.7,           # Increased for consistency (was 0.5)
                    "similarity_boost": 0.65,   # Reduced to avoid artifacts (was 0.75)
                    "style": 0.0,               # Keep at 0 for phone calls
                    "use_speaker_boost": True   # Essential for phone clarity
                }
            }
            
            # Use longer timeout for TTS generation
            async with httpx.AsyncClient(timeout=45.0) as client:
                logger.info(f"   📡 URL: {url}")
                logger.debug(f"   Requesting ElevenLabs with model={settings.elevenlabs_model}, format=pcm_24000")
                response = await client.post(url, json=payload, headers=headers)
                
                # Log response details for debugging
                logger.debug(f"   Response status: {response.status_code}")
                logger.info(f"   🎵 Content-Type: {response.headers.get('content-type', 'not set')}")
                logger.debug(f"   Response headers: {dict(response.headers)}")
                
                response.raise_for_status()
                audio_data = response.content
            
            # Verify we got data
            if not audio_data or len(audio_data) == 0:
                logger.error("❌ ElevenLabs returned empty audio data")
                return None
            
            # Calculate expected duration (24kHz, 16-bit mono = 48000 bytes/sec)
            duration_sec = len(audio_data) / 48000
            logger.info(f"✅ ElevenLabs generated {len(audio_data)} bytes ({duration_sec:.2f}s @ 24kHz)")
            
            # Sanity check - audio should be at least 0.1 seconds
            if duration_sec < 0.1:
                logger.warning(f"⚠️  Generated audio seems too short ({duration_sec:.2f}s)")
            
            return audio_data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ ElevenLabs HTTP error {e.response.status_code}: {e.response.text}")
            return None
        except httpx.TimeoutException:
            logger.error(f"❌ ElevenLabs TTS timeout after 45s")
            return None
        except Exception as e:
            logger.error(f"❌ ElevenLabs TTS error: {e}", exc_info=True)
            return None
    
    async def _openai_tts(self, text: str) -> Optional[bytes]:
        """Generate speech using OpenAI TTS API (fallback)."""
        try:
            logger.info(f"🔊 OpenAI TTS generating: \"{text[:50]}...\" (length: {len(text)} chars)")
            
            # OpenAI TTS parameters for telephony
            response = await self.openai_client.audio.speech.create(
                model=settings.tts_model,       # tts-1-hd for better quality
                voice=settings.tts_voice,       # alloy, echo, fable, onyx, nova, shimmer
                input=text,
                response_format="pcm",          # Raw PCM data (16-bit, 24kHz)
                speed=settings.tts_speed,       # 1.0 = normal speed
            )
            
            audio_data = response.content
            
            # Verify we got data
            if not audio_data or len(audio_data) == 0:
                logger.error("❌ OpenAI returned empty audio data")
                return None
            
            # Calculate duration (24kHz, 16-bit mono = 48000 bytes/sec)
            duration_sec = len(audio_data) / 48000
            logger.info(f"✅ OpenAI generated {len(audio_data)} bytes ({duration_sec:.2f}s @ 24kHz)")
            
            return audio_data
            
        except Exception as e:
            logger.error(f"❌ OpenAI TTS error: {e}", exc_info=True)
            return None
    
    def get_sample_rate(self) -> int:
        """Get the sample rate of the TTS output."""
        # Both ElevenLabs (pcm_24000) and OpenAI output 24kHz = clean 3:1 to 8kHz
        return 24000


# Singleton instance
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get or create TTS service singleton."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
