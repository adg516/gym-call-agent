# Gym Call Agent

An AI phone agent that calls gyms/BJJ gyms, has natural voice conversations, and collects structured drop-in information (schedule, pricing, mat fees, requirements).

## Stack

- **Twilio Voice** for phone calls with real-time Media Streams
- **Python + FastAPI** backend
- **k3s** on 3 Raspberry Pis, Traefik ingress, cert-manager for TLS
- Streaming audio (real-time) for LLM voice + transcription

## Infrastructure Status

✅ k3s cluster running (3 nodes)  
✅ App deployed and reachable at `https://bidetking.ddns.net`  
✅ Let's Encrypt TLS certificate issued and renewing automatically  
✅ No-IP dynamic DNS updating correctly  
✅ Traefik Ingress configured for HTTP/HTTPS

## Features

### ✅ Implemented
- **Outbound Calls**: Initiate calls to gyms via REST API
- **Media Streaming**: Bidirectional audio streaming via WebSocket
- **Call Status Tracking**: Real-time updates on call lifecycle
- **TwiML Integration**: Automatic call flow management

### 🚧 Coming Soon
- ASR (Speech-to-Text) integration
- LLM conversation logic
- TTS (Text-to-Speech) for responses
- Structured data extraction
- Redis for persistent storage

## Quick Start: Making Your First Call

### 1. **Set Environment Variables**

Make sure your `.env` file has:

```bash
PUBLIC_BASE_URL=https://bidetking.ddns.net
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_FROM_NUMBER=+1234567890
```

### 2. **Start the Server**

```bash
cd /home/adggda/gymgym
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

### 3. **Make a Test Call**

Using the test script:

```bash
python test_outbound_call.py +14155551234 "Test Gym"
```

Or using curl:

```bash
curl -X POST http://localhost:8000/v1/calls \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+14155551234",
    "gym_name": "Example BJJ Gym"
  }'
```

### 4. **Watch the Logs**

You'll see:
1. Call initiated via Twilio API
2. Twilio calls the gym
3. When answered: webhook hit at `/v1/twilio/voice`
4. WebSocket connection at `/v1/twilio/stream`
5. Audio frames streaming in real-time

## Environment Variables

Create a `.env` file in the project root:

```bash
# App Configuration
APP_NAME=gym-call-agent
ENV=dev  # or prod
LOG_LEVEL=INFO

# Network (IMPORTANT: Update this for production!)
PUBLIC_BASE_URL=https://bidetking.ddns.net

# Twilio Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_FROM_NUMBER=+1234567890
TWILIO_VALIDATE_SIGNATURE=false  # Set to true in production for security

# Redis (optional, for future use)
# REDIS_URL=redis://localhost:6379
```

### Getting Twilio Credentials

1. Sign up at [twilio.com](https://www.twilio.com)
2. Go to Console Dashboard to find your **Account SID** and **Auth Token**
3. Buy a phone number in Console → Phone Numbers → Buy a Number
4. Copy the phone number (in E.164 format, e.g., `+14155551234`)

## Twilio Console Configuration

### 1. Configure Voice Webhook

1. Go to [Twilio Console → Phone Numbers → Manage → Active numbers](https://console.twilio.com/us1/develop/phone-numbers/manage/incoming)
2. Click on your phone number
3. Scroll to "Voice Configuration"
4. Under **"A CALL COMES IN"**:
   - Select: `Webhook`
   - HTTP Method: `POST`
   - URL: `https://bidetking.ddns.net/v1/twilio/voice`
5. Click **Save**

### 2. Test the Integration

Call your Twilio phone number and check the logs:

```bash
# If running locally
uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info

# If running in k3s
kubectl logs -f deployment/gym-call-agent -n default
```

You should see:
- Webhook hit at `/v1/twilio/voice`
- WebSocket connection at `/v1/twilio/stream`
- Stream start event with `streamSid` and `callSid`
- Media frames being received
- Stream stop event when call ends

## API Endpoints

### Make an Outbound Call (Primary Feature)
```bash
POST /v1/calls
Content-Type: application/json

{
  "phone_number": "+14155552671",
  "gym_name": "Example BJJ Gym",
  "country": "US",
  "timezone": "America/Los_Angeles",
  "preferred_language": "en"
}

# Response:
{
  "call_id": "uuid-here",
  "status": "queued",  # or "initiated", "ringing", etc.
  "twilio_call_sid": "CAxxxx",
  "created_at": "2025-12-28T..."
}
```

### Check Call Status
```bash
GET /v1/calls/{call_id}

# Response:
{
  "call_id": "uuid-here",
  "twilio_call_sid": "CAxxxx",
  "status": "in-progress",
  "created_at": "2025-12-28T...",
  "last_updated": "2025-12-28T...",
  "request": { "phone_number": "+1...", ... },
  "result": null
}
```

### Health Check
```bash
GET /healthz
```

### Twilio Webhooks (Internal - Called by Twilio)
- `POST /v1/twilio/voice` - Voice webhook (returns TwiML)
- `WS /v1/twilio/stream` - Media Streams WebSocket

## Development

### Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Twilio Signature Validation

For security in production, enable signature validation:

1. Set `TWILIO_VALIDATE_SIGNATURE=true` in your `.env`
2. Ensure `TWILIO_AUTH_TOKEN` is set correctly
3. Twilio will sign all webhook requests with `X-Twilio-Signature` header
4. Invalid signatures will be rejected with HTTP 403

**Note:** Keep validation disabled (`false`) during local development if using ngrok/tunnels.

### Docker Build

```bash
# Build image
docker build -t gym-call-agent:latest .

# Run container
docker run -p 8000:8000 --env-file .env gym-call-agent:latest
```

### Deploy to k3s

```bash
# Build and save image
docker build -t gym-call-agent:latest .
docker save gym-call-agent:latest > gym-call-agent.tar

# Transfer to Pi and load
scp gym-call-agent.tar pi@raspberrypi.local:/tmp/
ssh pi@raspberrypi.local "sudo k3s ctr images import /tmp/gym-call-agent.tar"

# Apply manifests
kubectl apply -f k8s/
```

## Architecture

### Current Flow (MVP)

1. **Incoming Call**: User calls Twilio number
2. **Webhook**: Twilio POSTs to `/v1/twilio/voice`
3. **TwiML Response**: App returns XML with `<Connect><Stream url="wss://..."/>`
4. **WebSocket**: Twilio connects to `/v1/twilio/stream`
5. **Audio Stream**: 
   - Twilio sends μ-law encoded audio (8kHz, 20ms chunks)
   - Base64 encoded in JSON `media` events
   - App logs and buffers (no processing yet)

### Future Flow (Full AI Agent)

1. Incoming call → Twilio webhook
2. WebSocket established
3. **Audio Pipeline**:
   - Decode μ-law → PCM audio
   - Stream to ASR (Whisper / Deepgram)
   - Transcription → LLM (GPT-4, Claude)
   - LLM response → TTS (ElevenLabs / Cartesia)
   - Encode PCM → μ-law
   - Send back to Twilio WebSocket
4. Collect structured data during conversation
5. Store results (schedule, pricing, etc.) in Redis/DB

## Troubleshooting

### Webhook Not Receiving Calls

- Verify domain is publicly accessible: `curl https://bidetking.ddns.net/healthz`
- Check Twilio Console → Monitor → Logs → Errors
- Ensure No-IP DNS is updating: `dig bidetking.ddns.net`
- Check firewall/router port forwarding for 80/443

### WebSocket Connection Fails

- Ensure `PUBLIC_BASE_URL` starts with `https://` (will be converted to `wss://`)
- Check ingress supports WebSocket upgrades (Traefik does by default)
- Look for `Upgrade: websocket` in request headers

### Media Frames Not Arriving

- Confirm TwiML includes `<Connect><Stream>` (not `<Start><Stream>`)
- Check that WebSocket stays open (don't close on first message)
- Review Twilio Console → Voice → Streams for stream status

## Next Steps

- [ ] Implement audio decoding (μ-law → PCM)
- [ ] Integrate ASR (Whisper/Deepgram)
- [ ] Connect LLM for conversation logic
- [ ] Add TTS and audio encoding (PCM → μ-law)
- [ ] Store conversation results in Redis
- [ ] Build admin UI for call management
- [ ] Add rate limiting and authentication

## License

MIT

