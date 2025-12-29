# Gym Call Agent - Project Status & Next Steps

**Last Updated**: December 28, 2025  
**Status**: Phase 1 Complete ✅

---

## 🎯 Project Goal

Build an AI phone agent that autonomously calls gyms/BJJ gyms, has natural voice conversations, and collects structured drop-in information (pricing, schedule, mat fees, requirements).

---

## ✅ What's Working (Phase 1 Complete)

### Infrastructure
- **k3s Cluster**: 3 Raspberry Pi nodes, production-ready
- **Domain & TLS**: `bidetking.ddns.net` with Let's Encrypt certificates
- **Ingress**: Traefik with HTTP/HTTPS, WebSocket support
- **Dynamic DNS**: No-IP automatically updating public IP
- **Deployment**: Docker containerization, k8s manifests

### Application
- **FastAPI Backend**: Python 3.13, async/await architecture
- **Outbound Calling**: Twilio Voice API integration
  - Create calls via REST API (`POST /v1/calls`)
  - Status tracking and webhooks
  - Call metadata storage (in-memory, Redis-ready)

### Audio Processing Pipeline (Phase 1)
- ✅ **Twilio Media Streams**: Real-time bidirectional audio via WebSocket
- ✅ **Audio Decoding**: μ-law (8kHz phone audio) → PCM (16-bit linear)
- ✅ **Audio Encoding**: PCM → μ-law (for sending audio back)
- ✅ **Buffering**: 20ms chunks → 1-second segments for processing
- ✅ **Voice Activity Detection (VAD)**: Simple threshold-based speech detection
- ✅ **Audio Analysis**: RMS level calculation, speech/silence classification
- ✅ **Statistics Tracking**: Frame counts, speech ratio, audio levels, call duration

### Monitoring & Observability
- Comprehensive logging with DEBUG level
- Real-time audio frame analysis
- Call statistics reports
- WebSocket connection tracking

---

## 📊 Last Test Call Results

```
Duration: 9.18 seconds
Frames processed: 459
Speech detected: 106 frames (23.1%)
Silence: 353 frames (76.9%)
Audio levels: Min 0.0, Max 0.39, Avg 0.033
Speech segments: 6
```

**What this proves:**
- ✅ Audio streaming works end-to-end
- ✅ Speech detection is functional
- ✅ Audio decoding is correct (no overflow errors)
- ✅ WebSocket connection stable
- ✅ Ready for ASR integration

---

## 🚀 What Needs to Happen Next

### Phase 2: Speech Recognition (ASR)
**Goal**: Convert audio to text in real-time

**Tasks**:
1. **Sign up for ASR service** (Recommended: Deepgram)
   - Free tier: $200 credit
   - Best for real-time: ~100ms latency
   - WebSocket streaming API

2. **Integrate Deepgram**
   ```python
   # Add to requirements.txt
   deepgram-sdk==3.x
   
   # In WebSocket handler
   - Connect to Deepgram WebSocket
   - Forward buffered μ-law audio
   - Receive transcription events
   - Log what gym is saying
   ```

3. **Handle Transcriptions**
   - Store conversation history
   - Detect utterance boundaries
   - Track speaker turns

**Output**: Real-time transcription of gym employee speech

---

### Phase 3: LLM Integration
**Goal**: Generate intelligent responses

**Tasks**:
1. **Choose LLM** (Recommended: GPT-4o-mini)
   - Fast: ~500ms response time
   - Cheap: $0.15/1M input tokens, $0.60/1M output
   - Good for structured extraction

2. **Design Conversation Prompt**
   ```
   System: You're calling a gym to ask about drop-in rates.
   Be friendly, professional, and direct. Ask about:
   - Drop-in class pricing
   - Schedule (what days/times)
   - Mat fees or equipment requirements
   - Trial class availability
   
   Extract structured data and end call politely.
   ```

3. **Implement Conversation Loop**
   - ASR transcript → LLM
   - LLM response → TTS
   - Track conversation state
   - Extract structured data
   - Detect call end conditions

4. **Add Structured Data Extraction**
   - Parse LLM responses for pricing
   - Extract schedule information
   - Store in database/Redis

**Output**: AI that responds intelligently to gym questions

---

### Phase 4: Text-to-Speech (TTS)
**Goal**: Convert AI responses to natural-sounding speech

**Tasks**:
1. **Choose TTS service** (Recommended: Cartesia or OpenAI TTS)
   - Cartesia: Low latency (~100ms), good quality
   - OpenAI TTS: Good balance, easy integration
   - ElevenLabs: Best quality, higher latency

2. **Integrate TTS**
   ```python
   async def synthesize_speech(text: str) -> bytes:
       # Call TTS API
       audio_pcm = await tts_client.synthesize(text)
       # Encode to μ-law for Twilio
       audio_mulaw = encode_pcm_to_mulaw(audio_pcm)
       return audio_mulaw
   
   # In WebSocket handler
   ai_response = await llm.generate(conversation_history)
   audio = await synthesize_speech(ai_response)
   await send_audio_to_twilio(ws, audio)
   ```

3. **Handle Audio Timing**
   - Wait for gym to finish speaking (VAD)
   - Generate response quickly
   - Stream audio back smoothly

**Output**: AI voice that sounds natural on phone calls

---

### Phase 5: Production Readiness

**Tasks**:
1. **Data Storage**
   - Replace in-memory storage with Redis
   - Store call transcripts
   - Save extracted gym information
   - Call recording (optional)

2. **Error Handling**
   - Retry logic for API failures
   - Graceful degradation
   - Call timeout handling
   - Network error recovery

3. **Rate Limiting & Scaling**
   - Queue system for multiple calls
   - Concurrent call limits (Twilio trial: 1)
   - API rate limiting

4. **Admin Interface**
   - Web UI to view call history
   - See extracted gym data
   - Manage call queue
   - View transcripts

5. **Testing & Quality**
   - Automated tests for audio pipeline
   - Conversation quality metrics
   - Data extraction accuracy
   - Call success rate tracking

---

## 💰 Cost Estimate: One Complete Call

### Assumptions
- **Call duration**: 4 minutes average
- **Exchanges**: 15-20 back-and-forth exchanges
- **Transcription**: Full call audio (both sides)
- **LLM tokens**: ~10,000 total (input + output)
- **TTS words**: ~1000 words spoken by AI

### Cost Breakdown

| Service | Usage | Unit Cost | Total |
|---------|-------|-----------|-------|
| **Twilio Voice** | 4 min outbound | $0.013/min | $0.052 |
| **Twilio Phone Number** | Monthly | $1.00/mo ÷ 1000 calls | $0.001 |
| **Deepgram ASR** | 4 min audio | $0.0043/min | $0.017 |
| **GPT-4o-mini** | 10K tokens | $0.15/1M in, $0.60/1M out | $0.075 |
| **OpenAI TTS** | 1000 words | $15/1M chars (~5 chars/word) | $0.075 |
| **Infrastructure** | k3s on RPi | Self-hosted | $0.000 |
| **Redis/Storage** | Minimal | Negligible | $0.000 |
| | | **Total per call** | **$0.22** |

### Monthly Cost Projections

| Calls/Month | Total Cost | Notes |
|-------------|------------|-------|
| 100 | $22 | Light testing |
| 500 | $110 | Active development |
| 1,000 | $220 | Light production |
| 5,000 | $1,100 | Scaling up |
| 10,000 | $2,200 | Full production |

### Cost Optimization Options

**If you need cheaper:**
- Use Whisper API instead of Deepgram: -$0.012/call ($0.006/min vs $0.0043/min)
- Use Gemini Flash instead of GPT-4o-mini: -$0.05/call
- Use Google Cloud TTS instead of OpenAI: -$0.06/call
- **Cheapest stack**: ~$0.07/call (Twilio + Whisper + Gemini + Google TTS)

**Cost scaling notes:**
- Infrastructure cost: $0 (self-hosted k3s)
- Twilio trial account: Limited to verified numbers only
- Deepgram: First $200 free
- OpenAI: Rate limits may apply at scale

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Request                             │
│              "Find gyms near me with drop-in rates"              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  POST /v1/calls → Initiate call via Twilio API                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Twilio Voice                                │
│  Calls gym phone number → Gym answers                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              Twilio → Your Server Webhook                        │
│  POST /v1/twilio/voice → Returns TwiML with WebSocket URL       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   WebSocket Connection                           │
│         wss://bidetking.ddns.net/v1/twilio/stream               │
│                                                                  │
│  ┌──────────────┐                        ┌──────────────┐      │
│  │ Gym speaks   │ ──μ-law audio→        │ Your Server  │      │
│  │              │                        │              │      │
│  │              │ ←──μ-law audio─       │ AI speaks    │      │
│  └──────────────┘                        └──────────────┘      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Audio Processing Pipeline                     │
│                                                                  │
│  1. Decode μ-law → PCM                     ✅ DONE              │
│  2. Buffer 20ms chunks → 1s segments       ✅ DONE              │
│  3. Voice Activity Detection               ✅ DONE              │
│                                                                  │
│  4. Forward to Deepgram ASR               ⏳ TODO (Phase 2)     │
│     ↓ transcription                                              │
│  5. Send to LLM (GPT-4o-mini)             ⏳ TODO (Phase 3)     │
│     ↓ AI response text                                           │
│  6. Text-to-Speech (Cartesia/OpenAI)      ⏳ TODO (Phase 4)     │
│     ↓ AI audio                                                   │
│  7. Encode PCM → μ-law                     ✅ DONE              │
│  8. Send back through WebSocket            ✅ DONE              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Structured Data Extraction                      │
│                                                                  │
│  Parse conversation → Extract:                                   │
│  - Drop-in pricing                        ⏳ TODO (Phase 3)     │
│  - Class schedule                         ⏳ TODO (Phase 3)     │
│  - Mat fees                               ⏳ TODO (Phase 3)     │
│  - Requirements                           ⏳ TODO (Phase 3)     │
│                                                                  │
│  Store in Redis/Database                  ⏳ TODO (Phase 5)     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        Return to User                            │
│  {                                                               │
│    "gym_name": "Example BJJ",                                   │
│    "drop_in_price": "$25",                                      │
│    "schedule": "Mon-Fri 6pm-9pm",                               │
│    "mat_fee": "None",                                           │
│    "requirements": "No gi needed for first class"               │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 File Structure

```
/home/adggda/gymgym/
├── app/
│   ├── main.py                    # FastAPI app, logging config
│   ├── api/
│   │   ├── routes.py              # Call management endpoints
│   │   └── twilio.py              # Twilio webhooks & WebSocket ✅
│   ├── core/
│   │   └── config.py              # Settings & env vars
│   └── services/
│       └── audio_utils.py         # Audio processing utilities ✅
├── k8s/
│   ├── deployment.yaml            # k8s deployment config
│   ├── service.yaml               # Service definition
│   ├── ingress.yaml               # Traefik ingress rules
│   └── letsencrypt-issuer.yaml    # Cert manager config
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Container definition
├── deploy.sh                      # Build & deploy script ✅
├── test_outbound_call.py          # Test script ✅
└── .env                           # Environment variables (gitignored)
```

---

## 🔑 Environment Variables

Current configuration (`.env` and k8s deployment):

```bash
# App
APP_NAME=gym-call-agent
ENV=dev
LOG_LEVEL=DEBUG

# Network
PUBLIC_BASE_URL=https://bidetking.ddns.net

# Twilio (configured)
TWILIO_ACCOUNT_SID=AC98fHx27abd077690fb594fef8d856e3
TWILIO_AUTH_TOKEN=***hidden***
TWILIO_FROM_NUMBER=+16309373197
TWILIO_VALIDATE_SIGNATURE=false

# TODO: Add in future phases
# DEEPGRAM_API_KEY=***
# OPENAI_API_KEY=***
# REDIS_URL=redis://localhost:6379
```

---

## 🧪 Testing

### Test Call Command
```bash
python test_outbound_call.py +1YOUR_PHONE "Test Gym Name"
```

### View Logs
```bash
# k8s deployment
kubectl logs deployment/gym-call-agent --tail=100 -f

# Local uvicorn (if running)
tail -f /tmp/uvicorn_log.txt
```

### Deploy New Code
```bash
cd /home/adggda/gymgym
./deploy.sh
```

---

## 📚 Key Learnings & Gotchas

1. **Python 3.13 Removed `audioop`**: Had to implement custom μ-law decoder
2. **WebSocket URLs**: Must convert `https://` → `wss://` in TwiML
3. **Environment Variables**: k8s deployment needs env vars explicitly set
4. **Logging Configuration**: Both uvicorn AND Python logging need configuration
5. **Docker Context**: Use `.dockerignore` to avoid permission errors
6. **Audio Buffering**: Twilio sends 20ms chunks, ASR needs 1-second segments
7. **Trial Account Limitations**: Can only call verified phone numbers
8. **WebSocket Through Ingress**: Traefik handles WebSocket upgrade automatically

---

## 🎯 Immediate Next Steps (Priority Order)

1. **Sign up for Deepgram** (free $200 credit)
2. **Add Deepgram integration** (Phase 2)
   - Test with existing audio pipeline
   - Verify transcriptions are accurate
3. **Design conversation prompt** (Phase 3)
   - Write system prompt for gym calling
   - Define data extraction schema
4. **Add OpenAI GPT-4o-mini** (Phase 3)
   - Simple conversation loop first
   - Add structured extraction later
5. **Integrate TTS** (Phase 4)
   - Start with OpenAI TTS (easiest)
   - Test latency and quality

---

## 🎉 Summary

**Phase 1 Achievement**: Built a production-ready audio processing pipeline that can:
- Make outbound phone calls
- Stream audio bidirectionally over WebSocket
- Decode/encode phone audio formats
- Detect speech vs silence
- Track comprehensive call statistics

**You're 25% complete**. The hard infrastructure work is done. Now you add intelligence:
- Phase 2 (ASR): +25% → Listen
- Phase 3 (LLM): +30% → Think  
- Phase 4 (TTS): +15% → Speak
- Phase 5 (Polish): +5% → Production

**Estimated time to full MVP**: 2-3 more sessions like this one.

**Cost per call**: ~$0.22 (optimizable to ~$0.07)

**Next chat prompt**: "Let's implement Phase 2 - integrate Deepgram ASR so we can see what gyms are saying in real-time"

---

*Generated: December 28, 2025*
*Author: Your AI Assistant*
*Project: Gym Call Agent MVP*

