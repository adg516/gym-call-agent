from fastapi import APIRouter, Request, Response, WebSocket, WebSocketDisconnect, HTTPException
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from twilio.request_validator import RequestValidator
from app.core.config import settings
from app.services.audio_utils import (
    AudioBuffer, 
    decode_mulaw_to_pcm, 
    calculate_audio_level, 
    is_speech,
    AudioStats
)
import json
import base64
import logging
import asyncio
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def validate_twilio_signature(request: Request) -> bool:
    """
    Validates Twilio webhook signature using X-Twilio-Signature header.
    Returns True if valid or validation is disabled.
    Raises HTTPException if validation is enabled and signature is invalid.
    """
    if not settings.twilio_validate_signature:
        logger.info("Twilio signature validation is disabled")
        return True
    
    if not settings.twilio_auth_token:
        logger.warning("TWILIO_AUTH_TOKEN not set, cannot validate signature")
        return True
    
    validator = RequestValidator(settings.twilio_auth_token)
    
    # Get the signature from headers
    signature = request.headers.get("X-Twilio-Signature", "")
    
    # Construct the full URL
    url = str(request.url)
    
    # Get the POST parameters
    # For GET requests, params come from query string (already in URL)
    # For POST requests, we need the form data
    if request.method == "POST":
        # Note: request.form() is async and can only be called once
        # We'll need to handle this in the endpoint itself
        pass
    
    # For now, just log and allow through
    # Full validation requires accessing request body which can only be done once
    logger.info(f"Twilio signature validation requested but simplified implementation allows through")
    return True


@router.api_route("/twilio/voice", methods=["GET", "POST"])
async def twilio_voice(request: Request):
    """
    Twilio Voice webhook endpoint.
    When a call comes in, Twilio hits this endpoint.
    We respond with TwiML that starts Media Streams to our WebSocket.
    
    Configure in Twilio Console:
    "A CALL COMES IN" → Webhook POST to https://bidetking.ddns.net/v1/twilio/voice
    """
    logger.info(f"Twilio voice webhook called from {request.client.host if request.client else 'unknown'}")
    
    # Validate Twilio signature if enabled
    validate_twilio_signature(request)
    
    # Log request parameters for debugging (optional - can parse form/query params if needed)
    try:
        if request.method == "POST":
            # Try to read form data, but don't fail if it's not available
            form_data = await request.form()
            logger.info(f"Twilio webhook params: {dict(form_data)}")
    except Exception as e:
        logger.debug(f"Could not parse form data: {e}")
    
    # Build TwiML response
    vr = VoiceResponse()
    
    # Connect to our WebSocket for bidirectional audio streaming
    connect = Connect()
    stream = Stream(url=f"{settings.public_base_url.replace('http', 'ws')}/v1/twilio/stream")
    connect.append(stream)
    vr.append(connect)
    
    # Note: With <Connect><Stream>, the call stays open as long as the WebSocket is open.
    # No need for <Pause> - the WebSocket controls call duration.
    
    logger.info("Returning TwiML with Stream connection")
    return Response(content=str(vr), media_type="text/xml")


@router.websocket("/twilio/stream")
async def twilio_stream_ws(ws: WebSocket):
    """
    Twilio Media Streams WebSocket endpoint.
    
    Receives audio from the call and can send audio back.
    
    Message format from Twilio:
    - start: { "event": "start", "streamSid": "...", "callSid": "...", ... }
    - media: { "event": "media", "media": { "payload": "<base64-mulaw>", ... } }
    - stop: { "event": "stop", ... }
    
    PHASE 2: Forward audio to Deepgram ASR for transcription ✅
    TODO Phase 3: Send ASR transcriptions to LLM
    TODO Phase 4: Convert LLM responses to audio with TTS
    TODO Phase 5: Send audio back to Twilio
    """
    await ws.accept()
    logger.info("Twilio Media Stream WebSocket connected")
    
    # Initialize audio processing
    audio_buffer = AudioBuffer(sample_rate=8000, target_duration_ms=1000)
    audio_stats = AudioStats()
    
    stream_sid = None
    call_sid = None
    media_count = 0
    speech_segments = []
    
    # Initialize Deepgram connection
    deepgram_connection = None
    transcription_buffer = []  # Store all transcriptions
    
    # Check if Deepgram is configured
    if not settings.deepgram_api_key:
        logger.warning("⚠️  DEEPGRAM_API_KEY not set - transcription disabled")
    else:
        try:
            # Create Deepgram client
            config = DeepgramClientOptions(
                verbose=logging.DEBUG,
            )
            deepgram = DeepgramClient(settings.deepgram_api_key, config)
            
            # Connect to Deepgram's live transcription
            deepgram_connection = deepgram.listen.asynclive.v("1")
            
            # Define transcription event handlers
            async def on_message(*args, **kwargs):
                logger.info(f"📥 on_message called! args={len(args)}, kwargs keys={list(kwargs.keys())}")
                try:
                    # First arg is the client (self), second arg is the result
                    result = args[1] if len(args) > 1 else kwargs.get('result')
                    logger.info(f"   Result type: {type(result)}")
                    sentence = result.channel.alternatives[0].transcript
                    if len(sentence) > 0:
                        confidence = result.channel.alternatives[0].confidence
                        is_final = result.is_final
                        speech_final = result.speech_final
                        
                        # Log with different markers for interim vs final
                        if is_final:
                            logger.info(f"🎤 FINAL [{confidence:.2f}]: {sentence}")
                        else:
                            logger.debug(f"🎤 interim [{confidence:.2f}]: {sentence}")
                        
                        # Store all results (we'll filter later for file saving)
                        transcription_buffer.append({
                            "text": sentence,
                            "confidence": confidence,
                            "is_final": is_final,
                            "speech_final": speech_final
                        })
                except Exception as e:
                    logger.error(f"Error processing transcription: {e}", exc_info=True)
            
            async def on_error(*args, **kwargs):
                # First arg is the client (self), second arg is the error
                error_data = args[1] if len(args) > 1 else kwargs.get('error')
                logger.error(f"❌ Deepgram error: {error_data}")
                logger.error(f"   Error type: {type(error_data)}")
                logger.error(f"   Error args: {args}")
                logger.error(f"   Error kwargs: {kwargs}")
            
            async def on_close(*args, **kwargs):
                logger.info("🔌 Deepgram connection closed")
            
            # Register event handlers
            deepgram_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            deepgram_connection.on(LiveTranscriptionEvents.Error, on_error)
            deepgram_connection.on(LiveTranscriptionEvents.Close, on_close)
            
            # Configure transcription options
            options = LiveOptions(
                model="nova-2",
                language="en-US",
                encoding="mulaw",  # Deepgram can handle μ-law directly!
                sample_rate=8000,
                channels=1,
                punctuate=True,
                interim_results=True,  # Get partial results while speaking
                smart_format=True,
                endpointing=500,  # Wait 500ms of silence before finalizing an utterance
                utterance_end_ms=1000,  # Wait 1000ms of silence before considering speech finished
                vad_events=True,  # Get voice activity detection events
            )
            
            # Start the connection
            if await deepgram_connection.start(options):
                logger.info("✅ Deepgram live transcription started")
            else:
                logger.error("❌ Failed to start Deepgram connection")
                deepgram_connection = None
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Deepgram: {e}", exc_info=True)
            deepgram_connection = None
    
    try:
        while True:
            msg = await ws.receive_text()
            event = json.loads(msg)
            event_type = event.get("event")
            
            if event_type == "start":
                stream_sid = event.get("streamSid")
                start_data = event.get("start", {})
                call_sid = start_data.get("callSid")
                
                logger.info(f"📞 Stream started")
                logger.info(f"   Stream SID: {stream_sid}")
                logger.info(f"   Call SID: {call_sid}")
                logger.info(f"   Media format: {start_data.get('mediaFormat', {})}")
                
            elif event_type == "connected":
                # Twilio sends this when WebSocket first connects
                logger.info(f"🔌 WebSocket connected to Twilio")
                
            elif event_type == "media":
                media_count += 1
                media_data = event.get("media", {})
                
                # Get base64 encoded μ-law audio
                payload_b64 = media_data.get("payload", "")
                timestamp = media_data.get("timestamp")
                
                # Decode from base64
                mulaw_bytes = base64.b64decode(payload_b64)
                
                # Convert μ-law to PCM for processing
                pcm_bytes = decode_mulaw_to_pcm(mulaw_bytes)
                
                # Calculate audio level and detect speech
                audio_level = calculate_audio_level(pcm_bytes)
                has_speech = is_speech(pcm_bytes, threshold=0.02)
                
                # Update statistics
                audio_stats.update(len(mulaw_bytes), audio_level, has_speech)
                
                # Add to buffer
                buffered_audio = audio_buffer.add_chunk(mulaw_bytes)
                
                # Log periodically (every 50 frames = ~1 second)
                if media_count % 50 == 0:
                    logger.debug(
                        f"📊 Frame {media_count}: "
                        f"Level={audio_level:.3f}, "
                        f"Speech={'🗣️ YES' if has_speech else '🤫 silence'}, "
                        f"Buffer={len(audio_buffer.buffer)} bytes"
                    )
                
                # When we have a full buffer (1 second of audio)
                if buffered_audio:
                    # Convert to PCM for analysis
                    buffered_pcm = decode_mulaw_to_pcm(buffered_audio)
                    overall_level = calculate_audio_level(buffered_pcm)
                    is_speech_segment = is_speech(buffered_pcm, threshold=0.02)
                    
                    if is_speech_segment:
                        speech_segments.append({
                            "timestamp": timestamp,
                            "duration_ms": 1000,
                            "level": overall_level,
                            "frame_number": media_count
                        })
                        logger.info(
                            f"🗣️  Speech segment detected! "
                            f"Level={overall_level:.3f}, "
                            f"Segment #{len(speech_segments)}"
                        )
                    
                    # PHASE 2: Send buffered audio to Deepgram ASR ✅
                    if deepgram_connection:
                        try:
                            # Send μ-law audio directly to Deepgram
                            # (No need to convert to PCM - Deepgram handles μ-law!)
                            await deepgram_connection.send(buffered_audio)
                            logger.debug(f"📤 Sent {len(buffered_audio)} bytes to Deepgram")
                        except Exception as e:
                            logger.error(f"Error sending audio to Deepgram: {e}", exc_info=True)
                
            elif event_type == "stop":
                logger.info(f"🛑 Stream stopped - {stream_sid}")
                
                # Flush any remaining audio
                remaining = audio_buffer.flush()
                if remaining:
                    logger.info(f"Flushed {len(remaining)} bytes of remaining audio")
                    # Send remaining audio to Deepgram
                    if deepgram_connection and remaining:
                        try:
                            await deepgram_connection.send(remaining)
                        except Exception as e:
                            logger.error(f"Error sending final audio to Deepgram: {e}")
                
                # Tell Deepgram we're done sending audio and to finalize everything
                if deepgram_connection:
                    try:
                        # Send CloseStream to force Deepgram to finalize all pending transcriptions
                        logger.info("📤 Sending CloseStream to Deepgram...")
                        await deepgram_connection.send(json.dumps({"type": "CloseStream"}))
                        logger.info("✅ CloseStream sent")
                    except Exception as e:
                        logger.error(f"Error sending CloseStream: {e}")
                
                # Wait longer for Deepgram to finish processing and send final results
                if deepgram_connection:
                    logger.info("⏳ Waiting for final transcriptions (5 seconds)...")
                    await asyncio.sleep(5)  # Increased from 2 to 5 seconds
                
                # Print final statistics
                stats = audio_stats.get_summary()
                buffer_stats = audio_buffer.get_stats()
                
                logger.info("=" * 60)
                logger.info("📊 CALL STATISTICS")
                logger.info("=" * 60)
                logger.info(f"Total frames received: {stats['total_frames']}")
                logger.info(f"Total audio duration: {stats['duration_seconds']:.2f} seconds")
                logger.info(f"Speech frames: {stats['speech_frames']} ({stats['speech_ratio']:.1%})")
                logger.info(f"Silence frames: {stats['silence_frames']}")
                logger.info(f"Audio levels - Min: {stats['audio_levels']['min']}, "
                          f"Max: {stats['audio_levels']['max']}, "
                          f"Avg: {stats['audio_levels']['avg']}")
                logger.info(f"Speech segments detected: {len(speech_segments)}")
                
                # Print transcription summary
                if transcription_buffer:
                    logger.info("=" * 60)
                    logger.info("📝 TRANSCRIPTION SUMMARY")
                    logger.info("=" * 60)
                    logger.info(f"Total transcriptions: {len(transcription_buffer)}")
                    
                    # Filter to only final results for summary
                    final_transcriptions = [t for t in transcription_buffer if t.get("is_final")]
                    logger.info(f"Final transcriptions: {len(final_transcriptions)}")
                    logger.info("")
                    logger.info("Full conversation (final only):")
                    for i, trans in enumerate(final_transcriptions, 1):
                        confidence = trans.get('confidence', 0)
                        logger.info(f"  [{i}] [{confidence:.2f}] {trans['text']}")
                    logger.info("=" * 60)
                    
                    # Save transcript to file (only final transcriptions)
                    if final_transcriptions:
                        try:
                            import os
                            from datetime import datetime
                            
                            # Create transcripts directory if it doesn't exist
                            transcripts_dir = "/app/transcripts"
                            os.makedirs(transcripts_dir, exist_ok=True)
                            
                            # Generate filename with timestamp and call SID
                            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                            filename = f"{transcripts_dir}/transcript_{timestamp}_{call_sid}.txt"
                            
                            # Write transcript to file
                            with open(filename, 'w') as f:
                                f.write(f"Call Transcript\n")
                                f.write(f"=" * 60 + "\n")
                                f.write(f"Call SID: {call_sid}\n")
                                f.write(f"Stream SID: {stream_sid}\n")
                                f.write(f"Timestamp: {timestamp}\n")
                                f.write(f"Duration: {stats['duration_seconds']:.2f} seconds\n")
                                f.write(f"Speech frames: {stats['speech_frames']} ({stats['speech_ratio']:.1%})\n")
                                f.write(f"Total transcriptions (including interim): {len(transcription_buffer)}\n")
                                f.write(f"Final transcriptions: {len(final_transcriptions)}\n")
                                f.write(f"\n")
                                f.write(f"Transcription (final results only):\n")
                                f.write(f"-" * 60 + "\n")
                                for i, trans in enumerate(final_transcriptions, 1):
                                    confidence = trans.get('confidence', 0)
                                    f.write(f"[{i}] [{confidence:.2f}] {trans['text']}\n")
                                f.write(f"=" * 60 + "\n")
                            
                            logger.info(f"💾 Transcript saved to: {filename}")
                        except Exception as e:
                            logger.error(f"Failed to save transcript: {e}")
                    else:
                        logger.info("No final transcriptions to save (only interim results received)")
                else:
                    logger.info("No transcriptions received")
                logger.info("=" * 60)
                
                break
            
            else:
                logger.warning(f"⚠️  Unknown event type: {event_type}")
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected - {stream_sid}, frames: {media_count}")
    except Exception as e:
        logger.error(f"❌ Error in Media Stream WebSocket: {e}", exc_info=True)
    finally:
        # Close Deepgram connection
        if deepgram_connection:
            try:
                await deepgram_connection.finish()
                logger.info("✅ Deepgram connection closed")
            except Exception as e:
                logger.error(f"Error closing Deepgram: {e}")
        
        # Ensure the Twilio socket is closed cleanly
        try:
            await ws.close()
            logger.info(f"✅ WebSocket closed - {stream_sid}")
        except Exception:
            pass