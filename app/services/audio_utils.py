"""
Audio utilities for processing Twilio Media Streams.

Twilio sends audio as:
- Encoding: μ-law (8-bit compressed)
- Sample rate: 8kHz
- Chunk size: 20ms = 160 bytes
- Format: Base64 encoded
"""
import base64
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# μ-law encoding/decoding constants
MULAW_BIAS = 0x84
MULAW_CLIP = 32635
MULAW_SCALE_BITS = 13


def _linear_to_mulaw(sample: int) -> int:
    """Convert a single 16-bit linear PCM sample to μ-law."""
    sign = (sample >> 8) & 0x80
    if sign:
        sample = -sample
    if sample > MULAW_CLIP:
        sample = MULAW_CLIP
    
    sample = sample + MULAW_BIAS
    exponent = 7
    for shift in range(7, -1, -1):
        if sample >= (0x100 << shift):
            exponent = shift
            break
    
    mantissa = (sample >> (exponent + 3)) & 0x0F
    mulaw = ~(sign | (exponent << 4) | mantissa)
    return mulaw & 0xFF


def _mulaw_to_linear(mulaw: int) -> int:
    """Convert a single μ-law byte to 16-bit linear PCM."""
    mulaw = int(~mulaw) & 0xFF
    sign = (mulaw & 0x80)
    exponent = (mulaw >> 4) & 0x07
    mantissa = mulaw & 0x0F
    
    sample = int(mantissa) << (int(exponent) + 3)
    sample += (0x80 << int(exponent))
    sample = sample - MULAW_BIAS
    
    if sign:
        sample = -sample
    
    # Clip to 16-bit range
    sample = max(-32768, min(32767, sample))
    return sample


class AudioBuffer:
    """
    Buffers incoming audio chunks for processing.
    
    Twilio sends 20ms chunks, but ASR typically wants longer segments (1-2 seconds).
    This class accumulates chunks until we have enough to process.
    """
    
    def __init__(self, sample_rate: int = 8000, target_duration_ms: int = 1000):
        """
        Args:
            sample_rate: Audio sample rate in Hz (8000 for Twilio)
            target_duration_ms: How much audio to buffer before processing
        """
        self.sample_rate = sample_rate
        self.target_duration_ms = target_duration_ms
        self.target_samples = (sample_rate * target_duration_ms) // 1000
        
        self.buffer = bytearray()
        self.total_bytes_received = 0
        self.total_chunks = 0
        
    def add_chunk(self, audio_bytes: bytes) -> Optional[bytes]:
        """
        Add audio chunk to buffer.
        
        Returns:
            Buffered audio if target duration reached, None otherwise
        """
        self.buffer.extend(audio_bytes)
        self.total_bytes_received += len(audio_bytes)
        self.total_chunks += 1
        
        # Check if we have enough audio
        if len(self.buffer) >= self.target_samples:
            # Extract target amount
            result = bytes(self.buffer[:self.target_samples])
            # Keep remainder
            self.buffer = self.buffer[self.target_samples:]
            return result
        
        return None
    
    def flush(self) -> Optional[bytes]:
        """Get any remaining audio in buffer."""
        if len(self.buffer) > 0:
            result = bytes(self.buffer)
            self.buffer = bytearray()
            return result
        return None
    
    def get_stats(self) -> dict:
        """Get buffer statistics."""
        return {
            "total_bytes": self.total_bytes_received,
            "total_chunks": self.total_chunks,
            "buffer_size": len(self.buffer),
            "duration_seconds": self.total_bytes_received / self.sample_rate,
        }


def decode_mulaw_to_pcm(mulaw_bytes: bytes) -> bytes:
    """
    Decode μ-law audio to linear PCM.
    
    Args:
        mulaw_bytes: μ-law encoded audio (8-bit)
        
    Returns:
        PCM audio (16-bit linear)
    """
    # Convert bytes to numpy array
    mulaw_array = np.frombuffer(mulaw_bytes, dtype=np.uint8)
    
    # Decode each sample
    pcm_array = np.array([_mulaw_to_linear(b) for b in mulaw_array], dtype=np.int16)
    
    return pcm_array.tobytes()


def encode_pcm_to_mulaw(pcm_bytes: bytes) -> bytes:
    """
    Encode linear PCM to μ-law.
    
    Args:
        pcm_bytes: PCM audio (16-bit linear)
        
    Returns:
        μ-law encoded audio (8-bit)
    """
    # Convert bytes to numpy array of 16-bit integers
    pcm_array = np.frombuffer(pcm_bytes, dtype=np.int16)
    
    # Encode each sample
    mulaw_array = np.array([_linear_to_mulaw(s) for s in pcm_array], dtype=np.uint8)
    
    return mulaw_array.tobytes()


def calculate_audio_level(pcm_bytes: bytes) -> float:
    """
    Calculate RMS (Root Mean Square) audio level.
    Useful for voice activity detection.
    
    Args:
        pcm_bytes: PCM audio (16-bit)
        
    Returns:
        RMS level (0.0 to 1.0)
    """
    if len(pcm_bytes) < 2:
        return 0.0
    
    # Convert bytes to numpy array of 16-bit integers
    audio_array = np.frombuffer(pcm_bytes, dtype=np.int16)
    
    # Calculate RMS
    rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
    
    # Normalize to 0-1 range (16-bit max = 32768)
    return min(rms / 32768.0, 1.0)


def is_speech(pcm_bytes: bytes, threshold: float = 0.02) -> bool:
    """
    Simple voice activity detection based on audio level.
    
    Args:
        pcm_bytes: PCM audio (16-bit)
        threshold: Minimum RMS level to consider as speech (0.0-1.0)
        
    Returns:
        True if audio contains speech
    """
    level = calculate_audio_level(pcm_bytes)
    return level > threshold


class AudioStats:
    """Track statistics about audio processing."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.total_frames = 0
        self.total_bytes = 0
        self.speech_frames = 0
        self.silence_frames = 0
        self.min_level = float('inf')
        self.max_level = 0.0
        self.avg_level = 0.0
        
    def update(self, frame_bytes: int, audio_level: float, is_speech: bool):
        """Update stats with new frame."""
        self.total_frames += 1
        self.total_bytes += frame_bytes
        
        if is_speech:
            self.speech_frames += 1
        else:
            self.silence_frames += 1
        
        self.min_level = min(self.min_level, audio_level)
        self.max_level = max(self.max_level, audio_level)
        
        # Running average
        self.avg_level = (
            (self.avg_level * (self.total_frames - 1) + audio_level) 
            / self.total_frames
        )
    
    def get_summary(self) -> dict:
        """Get statistics summary."""
        return {
            "total_frames": self.total_frames,
            "total_bytes": self.total_bytes,
            "duration_seconds": self.total_bytes / 8000,  # 8kHz sample rate
            "speech_frames": self.speech_frames,
            "silence_frames": self.silence_frames,
            "speech_ratio": self.speech_frames / max(self.total_frames, 1),
            "audio_levels": {
                "min": round(self.min_level, 3),
                "max": round(self.max_level, 3),
                "avg": round(self.avg_level, 3),
            }
        }

