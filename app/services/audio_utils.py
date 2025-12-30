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
from scipy import signal
import audioop  # Python's built-in audio operations (more reliable for μ-law)

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
    # Use Python's built-in audioop for reliable μ-law decoding
    try:
        return audioop.ulaw2lin(mulaw_bytes, 2)
    except audioop.error as e:
        logger.error(f"audioop.ulaw2lin failed: {e}, falling back to manual decoding")
        # Fallback to manual decoding if audioop fails
        mulaw_array = np.frombuffer(mulaw_bytes, dtype=np.uint8)
        pcm_array = np.array([_mulaw_to_linear(b) for b in mulaw_array], dtype=np.int16)
        return pcm_array.tobytes()


def encode_pcm_to_mulaw(pcm_bytes: bytes) -> bytes:
    """
    Encode linear PCM to μ-law.
    
    Args:
        pcm_bytes: PCM audio (16-bit linear, mono)
        
    Returns:
        μ-law encoded audio (8-bit)
    """
    # Use Python's built-in audioop for reliable μ-law encoding
    # lin2ulaw expects (fragment, width) where width=2 for 16-bit audio
    try:
        return audioop.lin2ulaw(pcm_bytes, 2)
    except audioop.error as e:
        logger.error(f"audioop.lin2ulaw failed: {e}, falling back to manual encoding")
        # Fallback to manual encoding if audioop fails
        pcm_array = np.frombuffer(pcm_bytes, dtype=np.int16)
        mulaw_array = np.array([_linear_to_mulaw(s) for s in pcm_array], dtype=np.uint8)
        return mulaw_array.tobytes()


def resample_audio(pcm_bytes: bytes, orig_rate: int, target_rate: int) -> bytes:
    """
    Resample PCM audio from one sample rate to another with high quality anti-aliasing.
    Uses scipy.signal.resample_poly with optimized filter for telephony.
    
    Args:
        pcm_bytes: PCM audio (16-bit linear mono)
        orig_rate: Original sample rate in Hz (e.g., 22050, 24000)
        target_rate: Target sample rate in Hz (e.g., 8000)
    
    Returns:
        Resampled PCM audio (16-bit linear mono)
    """
    from math import gcd
    
    if orig_rate == target_rate:
        return pcm_bytes
    
    # Verify we have data
    if len(pcm_bytes) == 0:
        logger.warning("resample_audio: received empty audio")
        return pcm_bytes
    
    # Convert bytes to numpy array (float32 for high-precision processing)
    pcm_array = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
    
    # Normalize to -1.0 to 1.0 range for better processing
    pcm_array = pcm_array / 32768.0
    
    # Calculate rational resampling factors
    # resample_poly(x, up, down) upsamples by 'up', then downsamples by 'down'
    # with proper anti-aliasing filter
    common = gcd(orig_rate, target_rate)
    up = target_rate // common      # e.g., 8000/8000 = 1
    down = orig_rate // common      # e.g., 24000/8000 = 3
    
    logger.debug(f"🔄 Resampling {orig_rate}Hz → {target_rate}Hz (up={up}, down={down}, ratio={down/up:.2f}:1)")
    
    try:
        # For 24kHz -> 8kHz (3:1 ratio), this is a simple decimation
        # resample_poly applies proper low-pass FIR anti-aliasing filter
        # window parameter controls filter quality (default is good for telephony)
        resampled = signal.resample_poly(pcm_array, up, down, window='hamming')
        
        logger.debug(f"   Input: {len(pcm_array)} samples, Output: {len(resampled)} samples")
        
    except Exception as e:
        logger.warning(f"⚠️  resample_poly failed: {e}, falling back to basic resample")
        num_samples = int(len(pcm_array) * target_rate / orig_rate)
        resampled = signal.resample(pcm_array, num_samples)
    
    # Denormalize back to int16 range
    resampled = resampled * 32768.0
    
    # Clip to prevent overflow and convert to int16
    resampled = np.clip(resampled, -32768, 32767).astype(np.int16)
    
    return resampled.tobytes()


def normalize_audio(pcm_bytes: bytes, target_peak: float = 0.9) -> bytes:
    """
    Normalize audio to prevent clipping while maintaining quality.
    
    Args:
        pcm_bytes: PCM audio (16-bit linear)
        target_peak: Target peak level (0.0-1.0), default 0.9 to avoid clipping
    
    Returns:
        Normalized PCM audio (16-bit linear)
    """
    if len(pcm_bytes) < 2:
        return pcm_bytes
    
    # Convert to numpy array
    pcm_array = np.frombuffer(pcm_bytes, dtype=np.int16)
    
    # Find current peak
    current_peak = np.abs(pcm_array).max()
    
    if current_peak == 0:
        logger.debug("normalize_audio: silent audio, skipping normalization")
        return pcm_bytes
    
    # Calculate normalization factor
    target_level = target_peak * 32767
    gain = target_level / current_peak
    
    # Only normalize if we need to reduce volume (prevent clipping)
    # or if volume is very low (< 50%)
    if gain < 1.0 or current_peak < 16384:
        logger.debug(f"🔊 Normalizing audio: peak {current_peak} → {int(target_level)} (gain={gain:.2f}x)")
        normalized = (pcm_array.astype(np.float32) * gain).astype(np.int16)
        return normalized.tobytes()
    
    return pcm_bytes


def convert_pcm16_to_mulaw_8khz(pcm_bytes: bytes, orig_sample_rate: int = 24000) -> bytes:
    """
    Convert PCM audio to μ-law format at 8kHz (for Twilio).
    This is the main function for TTS output conversion with quality optimizations.
    
    Pipeline:
    1. Normalize audio to prevent clipping
    2. Resample from orig_sample_rate (e.g., 24kHz) to 8kHz with anti-aliasing
    3. Encode to μ-law format
    
    Args:
        pcm_bytes: PCM audio (16-bit linear mono)
        orig_sample_rate: Original sample rate in Hz (default 24000 for ElevenLabs/OpenAI)
    
    Returns:
        μ-law encoded audio at 8kHz (8-bit)
    """
    # Ensure buffer is even length (16-bit PCM = 2 bytes per sample)
    if len(pcm_bytes) % 2 != 0:
        logger.debug("Padding odd-length audio buffer")
        pcm_bytes = pcm_bytes + b'\x00'  # Pad with silence
    
    orig_len = len(pcm_bytes)
    
    # Step 1: Normalize to prevent clipping (critical for avoiding static!)
    pcm_normalized = normalize_audio(pcm_bytes, target_peak=0.85)
    
    # Step 2: Resample to 8kHz with proper anti-aliasing
    if orig_sample_rate != 8000:
        logger.debug(f"🔄 Resampling {orig_sample_rate}Hz → 8000Hz ({orig_len} bytes)")
        pcm_8khz = resample_audio(pcm_normalized, orig_sample_rate, 8000)
        logger.debug(f"✓ Resampled: {len(pcm_8khz)} bytes (ratio: {orig_len/len(pcm_8khz):.2f}x)")
    else:
        pcm_8khz = pcm_normalized
    
    # Step 3: Encode to μ-law using audioop (reliable built-in encoder)
    mulaw_bytes = encode_pcm_to_mulaw(pcm_8khz)
    
    # Log conversion stats
    duration_ms = len(mulaw_bytes) / 8  # 8 bytes = 1ms at 8kHz mono μ-law
    logger.info(f"🔊 Audio converted: {orig_len}B PCM@{orig_sample_rate}Hz → {len(mulaw_bytes)}B μ-law@8kHz ({duration_ms:.0f}ms)")
    
    return mulaw_bytes


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

