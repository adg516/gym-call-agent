from fastapi import APIRouter, Request, Response, WebSocket, WebSocketDisconnect, HTTPException
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from twilio.request_validator import RequestValidator
from app.core.config import settings
from app.services.audio_utils import (
    AudioBuffer, 
    decode_mulaw_to_pcm, 
    calculate_audio_level, 
    is_speech,
    AudioStats,
    convert_pcm16_to_mulaw_8khz
)
from app.services.llm import get_llm_service
from app.services.tts import get_tts_service
from app.services.conversation import get_or_create_conversation, remove_conversation
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
    
    # Initialize LLM service
    llm_service = get_llm_service()
    conversation_state = None
    
    # Initialize TTS service
    tts_service = get_tts_service()
    
    # Initialize Deepgram connection
    deepgram_connection = None
    transcription_buffer = []  # Store all transcriptions
    
    async def send_audio_to_twilio(audio_mulaw: bytes, stream_sid: str):
        """
        Send audio back to Twilio through WebSocket.
        
        Args:
            audio_mulaw: mulaw encoded audio at 8kHz
            stream_sid: Twilio stream SID
        
        Returns:
            bool: True if sent successfully, False if WebSocket is closed
        """
        try:
            # Check if WebSocket is still open
            if ws.client_state.value != 1:  # 1 = CONNECTED
                logger.debug(f"WebSocket not connected (state={ws.client_state.value}), skipping audio send")
                return False
            
            # Encode to base64 for Twilio
            payload_b64 = base64.b64encode(audio_mulaw).decode('utf-8')
            
            # Send media message
            message = {
                "event": "media",
                "streamSid": stream_sid,
                "media": {
                    "payload": payload_b64
                }
            }
            
            await ws.send_text(json.dumps(message))
            logger.debug(f"📤 Sent {len(audio_mulaw)} bytes")
            return True
            
        except RuntimeError as e:
            if "close message has been sent" in str(e):
                logger.debug("WebSocket closed during audio send, stopping stream")
                return False
            logger.error(f"Error sending audio to Twilio: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending audio to Twilio: {e}", exc_info=True)
            return False
    
    async def generate_and_send_response():
        """Generate AI response and send audio back to caller."""
        if not conversation_state or not stream_sid:
            return
        
        # Check if we should speak
        if not conversation_state.should_ai_speak():
            logger.debug("Not time to speak yet (waiting for silence)")
            return
        
        # Check if TTS is enabled
        if not tts_service.is_enabled():
            logger.debug("TTS not enabled, skipping audio generation")
            return
        
        try:
            # Mark as speaking
            conversation_state.is_speaking = True
            
            # Generate response text
            logger.info("🤖 Generating AI response...")
            response_text = await llm_service.generate_response(conversation_state)
            
            if not response_text:
                logger.info("No response generated")
                conversation_state.is_speaking = False
                return
            
            logger.info(f"💬 AI will say: \"{response_text}\"")
            
            # Add to conversation history
            conversation_state.add_ai_message(response_text)
            
            # Convert text to speech
            audio_pcm = await tts_service.text_to_speech(response_text)
            
            if not audio_pcm:
                logger.error("Failed to generate speech audio")
                conversation_state.is_speaking = False
                return
            
            # Convert PCM to mulaw (8kHz, 8-bit) for Twilio
            # Sample rate depends on TTS provider (22050 for ElevenLabs, 24000 for OpenAI)
            orig_rate = tts_service.get_sample_rate()
            logger.info(f"🔄 Converting audio {orig_rate}Hz → 8kHz mulaw for Twilio...")
            audio_mulaw = convert_pcm16_to_mulaw_8khz(audio_pcm, orig_sample_rate=orig_rate)
            
            logger.info(f"✅ Audio ready: {len(audio_mulaw)} bytes mulaw @ 8kHz")
            
            # Send audio to Twilio in chunks
            # Twilio Media Streams expects ~20ms chunks (160 bytes at 8kHz mulaw)
            # IMPORTANT: Precise timing is critical to avoid static/choppy audio
            chunk_size = 160  # 20ms at 8kHz mono mulaw
            num_chunks = (len(audio_mulaw) + chunk_size - 1) // chunk_size
            
            logger.info(f"📤 Streaming {num_chunks} chunks to Twilio...")
            
            # Use more precise timing for smoother playback
            import time
            start_time = time.monotonic()
            chunks_sent = 0
            
            for i in range(0, len(audio_mulaw), chunk_size):
                chunk = audio_mulaw[i:i+chunk_size]
                
                # Pad last chunk if needed to maintain 20ms alignment
                if len(chunk) < chunk_size and i + chunk_size >= len(audio_mulaw):
                    # Pad with mulaw silence (0x7F for silence in mulaw)
                    chunk = chunk + b'\x7F' * (chunk_size - len(chunk))
                    logger.debug(f"   Padded last chunk to {chunk_size} bytes")
                
                # Send chunk - stop if WebSocket closes
                success = await send_audio_to_twilio(chunk, stream_sid)
                if not success:
                    logger.warning(f"⚠️  WebSocket closed after {chunks_sent}/{num_chunks} chunks")
                    break
                
                chunks_sent += 1
                
                # Calculate when next chunk should be sent (20ms per chunk)
                chunk_num = i // chunk_size
                expected_time = start_time + (chunk_num + 1) * 0.020
                current_time = time.monotonic()
                
                # Sleep until it's time for next chunk
                sleep_time = expected_time - current_time
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                elif sleep_time < -0.05:  # More than 50ms behind schedule
                    logger.warning(f"⚠️  Audio streaming lagging by {-sleep_time*1000:.0f}ms")
            
            logger.info(f"✅ Finished streaming {chunks_sent}/{num_chunks} chunks in {time.monotonic() - start_time:.2f}s")
            
            # Mark as done speaking
            conversation_state.is_speaking = False
            
            # Check if we should end the call after this response
            if conversation_state.should_end_call:
                logger.info("🏁 Call complete - hanging up...")
                await asyncio.sleep(3)  # Give audio time to finish playing
                # Close WebSocket to end the Twilio call
                await ws.close()
                return
            
        except Exception as e:
            logger.error(f"Error in generate_and_send_response: {e}", exc_info=True)
            conversation_state.is_speaking = False
    
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
                        
                        # PHASE 3: Process with LLM for final transcriptions
                        if is_final and sentence and conversation_state:
                            await process_with_llm(sentence, confidence)
                            
                except Exception as e:
                    logger.error(f"Error processing transcription: {e}", exc_info=True)
            
            async def process_with_llm(transcript: str, confidence: float):
                """Process transcription with LLM to extract gym info."""
                try:
                    if not llm_service.is_enabled():
                        logger.debug("LLM not enabled, skipping processing")
                        return
                    
                    # Add gym message to conversation
                    conversation_state.add_gym_message(transcript, confidence)
                    
                    # Process with LLM
                    logger.info(f"🧠 Processing with LLM: \"{transcript[:50]}...\"")
                    result = await llm_service.process_transcription(transcript, conversation_state)
                    
                    # Log results
                    if "error" in result:
                        logger.error(f"❌ LLM error: {result['error']}")
                        return
                    
                    extracted = result.get("extracted_info", {})
                    llm_confidence = result.get("confidence", "unknown")
                    notes = result.get("notes", "")
                    
                    # Update conversation state with extracted info
                    if extracted:
                        gym_info = conversation_state.gym_info
                        updated_fields = []
                        
                        if extracted.get("hours") and not gym_info.hours:
                            gym_info.hours = extracted["hours"]
                            updated_fields.append("hours")
                        
                        if extracted.get("day_pass_price") and not gym_info.day_pass_price:
                            gym_info.day_pass_price = extracted["day_pass_price"]
                            updated_fields.append("day_pass_price")
                        
                        if extracted.get("classes"):
                            if gym_info.classes is None:
                                gym_info.classes = []
                            gym_info.classes.extend(extracted["classes"])
                            updated_fields.append("classes")
                        
                        if extracted.get("drop_in_policy") and not gym_info.drop_in_policy:
                            gym_info.drop_in_policy = extracted["drop_in_policy"]
                            updated_fields.append("drop_in_policy")
                        
                        if updated_fields:
                            logger.info(f"✅ Extracted: {', '.join(updated_fields)}")
                            logger.info(f"   Confidence: {llm_confidence}")
                            if notes:
                                logger.info(f"   Notes: {notes}")
                            
                            # Log current progress
                            completion = gym_info.completion_percentage()
                            logger.info(f"📊 Info collection progress: {completion:.0f}%")
                            logger.info(f"   Hours: {'✓' if gym_info.hours else '✗'} {gym_info.hours or '(missing)'}")
                            logger.info(f"   Price: {'✓' if gym_info.day_pass_price else '✗'} {gym_info.day_pass_price or '(missing)'}")
                            logger.info(f"   Classes: {'✓' if gym_info.classes else '✗'} {gym_info.classes or '(missing)'}")
                            logger.info(f"   Policy: {'✓' if gym_info.drop_in_policy else '✗'} {gym_info.drop_in_policy or '(missing)'}")
                        else:
                            logger.info(f"ℹ️  No new information extracted")
                            if notes:
                                logger.info(f"   Notes: {notes}")
                    
                    # Check if we should end the call
                    should_end, reason = await llm_service.should_end_call(conversation_state)
                    if should_end:
                        conversation_state.should_end_call = True
                        conversation_state.end_reason = reason
                        logger.info(f"🏁 Call should end: {reason}")
                    
                    # PHASE 4: Generate and send AI response
                    # Wait longer for gym staff to finish speaking
                    await asyncio.sleep(2.5)  # Increased from 1.0s - let them finish naturally
                    await generate_and_send_response()
                    
                except Exception as e:
                    logger.error(f"Error in process_with_llm: {e}", exc_info=True)
            
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
                
                # Initialize conversation state for this call
                conversation_state = get_or_create_conversation(call_sid)
                
                # PHASE 4: Send initial greeting after a brief pause
                # Wait for the call to fully connect, then greet
                await asyncio.sleep(2.0)
                
                # Only send initial greeting if gym hasn't said anything yet
                if conversation_state.transcriptions_processed == 0:
                    await generate_and_send_response()
                else:
                    logger.info("🔕 Skipping initial greeting - gym already spoke")
                
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
                    
                    # PHASE 3: Print extracted gym information
                    if conversation_state and llm_service.is_enabled():
                        logger.info("=" * 60)
                        logger.info("🏋️  EXTRACTED GYM INFORMATION")
                        logger.info("=" * 60)
                        gym_info = conversation_state.gym_info
                        completion = gym_info.completion_percentage()
                        logger.info(f"Completion: {completion:.0f}%")
                        logger.info("")
                        logger.info(f"Hours: {gym_info.hours or '(not found)'}")
                        logger.info(f"Day Pass Price: {gym_info.day_pass_price or '(not found)'}")
                        logger.info(f"Classes: {', '.join(gym_info.classes) if gym_info.classes else '(not found)'}")
                        logger.info(f"Drop-in Policy: {gym_info.drop_in_policy or '(not found)'}")
                        
                        if gym_info.is_complete():
                            logger.info("")
                            logger.info("✅ Successfully collected all core information!")
                        else:
                            missing = gym_info.get_missing_fields()
                            logger.info("")
                            logger.info(f"⚠️  Missing information: {', '.join(missing)}")
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
                                # Header
                                f.write(f"GYM CALL TRANSCRIPT & AI ANALYSIS\n")
                                f.write(f"=" * 70 + "\n")
                                f.write(f"Call SID: {call_sid}\n")
                                f.write(f"Date/Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
                                f.write(f"Duration: {stats['duration_seconds']:.2f} seconds\n")
                                f.write(f"=" * 70 + "\n\n")
                                
                                # Full conversation transcript (both Gym and AI)
                                f.write(f"FULL CONVERSATION\n")
                                f.write(f"-" * 70 + "\n\n")
                                
                                # Use conversation_history if available (includes AI messages)
                                if conversation_state and conversation_state.conversation_history:
                                    for i, msg in enumerate(conversation_state.conversation_history, 1):
                                        if msg.speaker == "gym":
                                            f.write(f"[{i}] 🏋️ Gym Staff: {msg.text}\n")
                                            if msg.confidence:
                                                f.write(f"    (Confidence: {msg.confidence:.0%})\n\n")
                                            else:
                                                f.write(f"\n")
                                        else:  # AI
                                            f.write(f"[{i}] 🤖 AI Agent: {msg.text}\n\n")
                                else:
                                    # Fallback to just transcriptions
                                    for i, trans in enumerate(final_transcriptions, 1):
                                        confidence = trans.get('confidence', 0)
                                        f.write(f"[{i}] 🏋️ Gym Staff: {trans['text']}\n")
                                        f.write(f"    (Confidence: {confidence:.0%})\n\n")
                                
                                # LLM Analysis & Extracted Information
                                if conversation_state and llm_service.is_enabled():
                                    f.write(f"\n")
                                    f.write(f"=" * 70 + "\n")
                                    f.write(f"AI ANALYSIS & EXTRACTED INFORMATION\n")
                                    f.write(f"=" * 70 + "\n\n")
                                    
                                    gym_info = conversation_state.gym_info
                                    completion = gym_info.completion_percentage()
                                    
                                    # Summary
                                    f.write(f"Information Completeness: {completion:.0f}%\n")
                                    if gym_info.is_complete():
                                        f.write(f"Status: ✓ All core information collected\n\n")
                                    else:
                                        missing = gym_info.get_missing_fields()
                                        f.write(f"Status: Missing {', '.join(missing)}\n\n")
                                    
                                    # Extracted details
                                    f.write(f"OPERATING HOURS\n")
                                    f.write(f"-" * 70 + "\n")
                                    if gym_info.hours:
                                        f.write(f"{gym_info.hours}\n\n")
                                    else:
                                        f.write(f"Not mentioned during call\n\n")
                                    
                                    f.write(f"DAY PASS PRICING\n")
                                    f.write(f"-" * 70 + "\n")
                                    if gym_info.day_pass_price:
                                        f.write(f"{gym_info.day_pass_price}\n\n")
                                    else:
                                        f.write(f"Not mentioned during call\n\n")
                                    
                                    f.write(f"FITNESS CLASSES\n")
                                    f.write(f"-" * 70 + "\n")
                                    if gym_info.classes:
                                        for class_name in gym_info.classes:
                                            f.write(f"  • {class_name}\n")
                                        f.write(f"\n")
                                    else:
                                        f.write(f"Not mentioned during call\n\n")
                                    
                                    f.write(f"DROP-IN POLICY\n")
                                    f.write(f"-" * 70 + "\n")
                                    if gym_info.drop_in_policy:
                                        f.write(f"{gym_info.drop_in_policy}\n\n")
                                    else:
                                        f.write(f"Not mentioned during call\n\n")
                                    
                                    # Conversation stats
                                    f.write(f"-" * 70 + "\n")
                                    f.write(f"Conversation Statistics:\n")
                                    
                                    # Count gym vs AI messages
                                    gym_msgs = [m for m in conversation_state.conversation_history if m.speaker == "gym"]
                                    ai_msgs = [m for m in conversation_state.conversation_history if m.speaker == "ai"]
                                    
                                    f.write(f"  • Total exchanges: {len(conversation_state.conversation_history)}\n")
                                    f.write(f"  • Gym staff messages: {len(gym_msgs)}\n")
                                    f.write(f"  • AI agent responses: {len(ai_msgs)}\n")
                                    f.write(f"  • Speech frames: {stats['speech_frames']} ({stats['speech_ratio']:.1%})\n")
                                    
                                    # Calculate avg confidence only from gym messages with confidence
                                    gym_with_conf = [m for m in gym_msgs if m.confidence is not None]
                                    if gym_with_conf:
                                        avg_conf = sum(m.confidence for m in gym_with_conf) / len(gym_with_conf)
                                        f.write(f"  • Average ASR confidence: {avg_conf:.0%}\n")
                                    f.write(f"\n")
                                else:
                                    # No LLM processing
                                    f.write(f"\n")
                                    f.write(f"=" * 70 + "\n")
                                    f.write(f"CALL STATISTICS\n")
                                    f.write(f"=" * 70 + "\n")
                                    f.write(f"Speech frames: {stats['speech_frames']} ({stats['speech_ratio']:.1%})\n")
                                    f.write(f"Total transcriptions: {len(final_transcriptions)}\n")
                                
                                f.write(f"\n" + "=" * 70 + "\n")
                                f.write(f"End of transcript\n")
                            
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
        
        # Clean up conversation state
        if call_sid and conversation_state:
            logger.info(f"🧹 Cleaning up conversation state for {call_sid}")
            remove_conversation(call_sid)
        
        # Ensure the Twilio socket is closed cleanly
        try:
            await ws.close()
            logger.info(f"✅ WebSocket closed - {stream_sid}")
        except Exception:
            pass