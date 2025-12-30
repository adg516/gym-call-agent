# Gym Call Agent - Complete Project Status

**Last Updated:** December 30, 2025

## 🎯 Project Overview

An AI-powered phone call agent that handles inbound calls for gyms, collects information about operating hours, pricing, and fitness classes, then saves transcripts to a database.

### Core Technology Stack
- **Backend:** Python 3.12, FastAPI
- **Telephony:** Twilio Voice API + Media Streams (WebSocket)
- **Speech Recognition:** Deepgram (real-time streaming ASR)
- **LLM:** OpenAI GPT-4
- **Text-to-Speech:** ElevenLabs (preferred) or OpenAI TTS (fallback)
- **Infrastructure:** k3s (Kubernetes), Traefik Ingress, LetsEncrypt SSL
- **Deployment:** Docker containers on Raspberry Pi

### Key Features
- Real-time bidirectional audio streaming over WebSocket
- Natural conversation flow with interruption handling
- Voice Activity Detection (VAD) to prevent AI interruptions
- Automatic call termination after information collection
- Transcript generation with speaker labels
- PostgreSQL database for storing gym info and transcripts

---

## 📋 Project Phases

### Phase 1: Initial Setup ✅
**Status:** Complete

**Goals:**
- Set up FastAPI application structure
- Integrate Twilio Voice API for inbound calls
- Implement WebSocket handler for Media Streams
- Basic audio processing (μ-law encoding/decoding)

**Key Files:**
- `app/main.py` - FastAPI application entry point
- `app/api/twilio.py` - Twilio webhooks and WebSocket handler
- `app/services/audio_utils.py` - Audio conversion utilities
- `Dockerfile` - Container definition
- `requirements.txt` - Python dependencies

### Phase 2: Speech & Intelligence ✅
**Status:** Complete

**Goals:**
- Integrate Deepgram for real-time speech recognition
- Connect to OpenAI GPT-4 for response generation
- Implement conversation state management
- Add text-to-speech for AI responses

**Key Files:**
- `app/services/transcription.py` - Deepgram integration
- `app/services/llm.py` - OpenAI LLM integration
- `app/services/tts.py` - TTS service (ElevenLabs/OpenAI)
- `app/services/conversation.py` - Conversation state management
- `app/core/config.py` - Configuration and settings

### Phase 3: Kubernetes Deployment ✅
**Status:** Complete

**Goals:**
- Deploy to k3s on Raspberry Pi
- Configure Traefik ingress with SSL/TLS
- Set up LetsEncrypt certificates
- Manage secrets for API keys

**Key Files:**
- `k8s/deployment.yaml` - Kubernetes deployment manifest
- `k8s/service.yaml` - Kubernetes service definition
- `k8s/ingress.yaml` - Traefik ingress with SSL/TLS
- `k8s/letsencrypt-issuer.yaml` - cert-manager ClusterIssuer
- `deploy.sh` - Quick deployment script
- `nuke_and_deploy.sh` - Full rebuild and deployment script

### Phase 4: Audio Quality & Conversation Flow 🔄
**Status:** In Progress - TTS Issues

**Goals:**
- Fix static/garbled audio issues
- Improve conversation naturalness
- Prevent AI interruptions and question repetition
- Optimize TTS voice quality

**Changes Made:**
1. **Audio Processing Improvements:**
   - Switched from basic decimation to `scipy.signal.decimate` with anti-aliasing filter
   - Added `scipy.signal.resample_poly` for non-integer ratios
   - Replaced custom μ-law encoding with Python's `audioop.lin2ulaw()`
   - Added padding for odd-length audio buffers (for 16-bit alignment)
   - **CRITICAL:** TTS must output 24kHz PCM for clean 3:1 resampling to 8kHz Twilio

2. **Conversation Flow Improvements:**
   - Increased silence detection from 1.5s to 3.0s (`min_silence_seconds`)
   - Added tracking for AI's previous messages to prevent repetition
   - Modified greeting logic to prevent duplicate greetings
   - Added explicit "NEVER repeat questions" rules to LLM prompt
   - Increased pause after LLM processing from 1.0s to 2.5s
   - Implemented call termination with graceful hangup

3. **TTS Configuration:**
   - **ElevenLabs (PREFERRED):**
     - Model: `eleven_turbo_v2_5`
     - Voice: Rachel (or custom voice ID)
     - Output format: `pcm_24000` (24kHz 16-bit PCM) ⚠️ CRITICAL for quality
     - Settings: stability=0.5, similarity_boost=0.75, use_speaker_boost=True
   - **OpenAI TTS (Fallback):**
     - Model: `tts-1-hd`
     - Voice: `alloy`
     - Output: 24kHz PCM

**Current Issues:**
- Deployment blocked by "no space left on device" error on Raspberry Pi
- Need to verify ElevenLabs API key is correctly configured
- Audio quality testing pending successful deployment

---

## 🛠️ Scripts & Tools

### Deployment Scripts

#### `deploy.sh`
Quick deployment for minor changes. Does NOT restart k3s or clean up images.

```bash
#!/bin/bash
set -e

echo "🏗️  Building Docker image..."
docker build -t gym-call-agent:dev .

echo "💾 Saving image to tar..."
docker save gym-call-agent:dev -o /tmp/gym-agent.tar

echo "📦 Loading into k3s..."
sudo k3s ctr images import /tmp/gym-agent.tar

echo "🚀 Deploying to k3s..."
kubectl delete pod -l app=gym-call-agent --ignore-not-found
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

echo "✅ Deployment complete!"
```

#### `nuke_and_deploy.sh`
Full nuclear deployment with cleanup, k3s restart, and retry logic. Use when things are broken.

```bash
#!/bin/bash
set -e

echo "☢️  NUCLEAR DEPLOYMENT INITIATED ☢️"
echo "This will:"
echo "  - Clean up Docker images and k3s cache"
echo "  - Restart k3s"
echo "  - Build fresh image"
echo "  - Force reload everything"
echo ""

# Step 1: Disk cleanup (addresses "no space left on device")
echo "[1/7] Cleaning up disk space..."
echo "Removing old tar files..."
sudo rm -f /tmp/*.tar

echo "Pruning Docker images..."
sudo docker system prune -af
sudo docker image prune -af

echo "Pruning old containerd images..."
sudo k3s ctr images prune -a

echo "✓ Cleanup complete"
df -h /

# Step 2: Restart k3s
echo "[2/7] Restarting k3s..."
sudo systemctl restart k3s
echo "Waiting for k3s to be ready..."
sleep 10

# Wait for k3s to be truly ready
max_wait=60
elapsed=0
while ! kubectl get nodes &>/dev/null; do
    if [ $elapsed -ge $max_wait ]; then
        echo "❌ k3s failed to start"
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done
echo "✓ k3s is ready"

# Step 3: Build Docker image
echo "[3/7] Building Docker image..."
docker build -t gym-call-agent:dev .

# Step 4: Save to tar
echo "[4/7] Saving image to tar..."
docker save gym-call-agent:dev -o /tmp/gym-agent-nuke.tar
echo "✓ Saved to /tmp/gym-agent-nuke.tar"

# Step 5: Load into k3s with retries
echo "[5/7] Loading into k3s containerd..."
max_attempts=3
attempt=1
while [ $attempt -le $max_attempts ]; do
    echo "Attempt $attempt/$max_attempts..."
    if sudo k3s ctr images import /tmp/gym-agent-nuke.tar; then
        echo "✓ Image loaded successfully"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ Failed to load image after $max_attempts attempts"
        exit 1
    fi
    
    echo "⚠️  Load failed, restarting k3s and retrying..."
    sudo systemctl restart k3s
    sleep 15
    attempt=$((attempt + 1))
done

echo "Verifying image..."
sudo k3s ctr images ls | grep gym-call-agent

# Step 6: Nuclear cleanup of k8s resources
echo "[6/7] Nuclear cleanup..."
echo "Deleting deployment..."
kubectl delete deployment gym-call-agent --ignore-not-found

echo "Deleting all pods..."
kubectl delete pods -l app=gym-call-agent --ignore-not-found

echo "Deleting any replicasets..."
kubectl delete replicasets -l app=gym-call-agent --ignore-not-found

echo "Waiting for cleanup..."
sleep 5

# Step 7: Fresh deployment with retries
echo "[7/7] Fresh deployment..."
max_attempts=5
attempt=1
while [ $attempt -le $max_attempts ]; do
    echo "Apply attempt $attempt/$max_attempts..."
    if kubectl apply -f k8s/deployment.yaml && \
       kubectl apply -f k8s/service.yaml && \
       kubectl apply -f k8s/ingress.yaml; then
        echo "✓ All resources applied"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ Failed to apply resources"
        exit 1
    fi
    
    sleep 5
    attempt=$((attempt + 1))
done

# Check for LetsEncrypt issuer
echo "Checking SSL certificates..."
if kubectl get clusterissuer letsencrypt-prod &>/dev/null; then
    echo "✓ LetsEncrypt issuer configured"
else
    echo "⚠️  LetsEncrypt issuer not found, applying..."
    kubectl apply -f k8s/letsencrypt-issuer.yaml
fi

# Wait for pod to be ready
echo "Waiting for pod to be ready..."
max_wait=120
elapsed=0
while ! kubectl get pod -l app=gym-call-agent &>/dev/null; do
    if [ $elapsed -ge $max_wait ]; then
        echo "Timeout waiting for pod"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

# Final status
echo "========== FINAL STATUS =========="
kubectl get pods -l app=gym-call-agent -o wide
kubectl get deployments gym-call-agent
echo "Recent pod logs:"
kubectl logs -l app=gym-call-agent --tail=20 2>/dev/null || echo "No logs yet"

echo "🚀 Done! Test with: python test_outbound_call.py +1XXXXXXXXXX \"Test\""
```

### Debugging Scripts

#### `debug_tts.sh`
Checks TTS configuration and recent audio generation logs.

```bash
#!/bin/bash
POD=$(kubectl get pod -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}')

echo "=== TTS Configuration Check ==="
kubectl exec -it $POD -- env | grep -E "(ELEVENLABS|OPENAI|TTS)"

echo -e "\n=== Recent TTS Initialization ==="
kubectl logs $POD | grep -i "tts initialized" | tail -5

echo -e "\n=== Recent Speech Generation ==="
kubectl logs $POD | grep -E "(generate_speech|ElevenLabs|OpenAI TTS)" | tail -20

echo -e "\n=== Recent Audio Processing ==="
kubectl logs $POD | grep -E "(resample|convert_pcm|mulaw)" | tail -20

echo -e "\n=== Any TTS Errors ==="
kubectl logs $POD | grep -iE "(tts|speech|audio).*error" | tail -10
```

#### `deep_debug.sh`
Comprehensive debugging info from running pod.

```bash
#!/bin/bash
POD=$(kubectl get pod -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}')

echo "=== POD INFO ==="
kubectl get pod $POD -o wide

echo -e "\n=== ENVIRONMENT VARIABLES ==="
kubectl exec -it $POD -- env | sort

echo -e "\n=== FULL LOGS (last 100 lines) ==="
kubectl logs $POD --tail=100

echo -e "\n=== SERVICE ENDPOINTS ==="
kubectl get endpoints gym-call-agent

echo -e "\n=== INGRESS STATUS ==="
kubectl get ingress gym-call-agent -o yaml
```

### Testing Scripts

#### `test_outbound_call.py`
Initiates test calls to verify the system.

```python
import sys
import requests
import time

if len(sys.argv) < 3:
    print("Usage: python test_outbound_call.py +1234567890 'Gym Name'")
    sys.exit(1)

phone = sys.argv[1]
gym_name = sys.argv[2]

print(f"📞 Initiating call to {phone} ({gym_name})")

response = requests.post(
    "https://bidetking.ddns.net/v1/calls",
    json={"phone_number": phone, "gym_name": gym_name},
    verify=False  # Self-signed cert during dev
)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Call initiated successfully!")
    print(f"   Call ID: {data['call_id']}")
    print(f"   Twilio SID: {data['twilio_call_sid']}")
    print(f"   Status: {data['status']}")
    
    # Check status after 3 seconds
    time.sleep(3)
    status_response = requests.get(
        f"https://bidetking.ddns.net/v1/calls/{data['call_id']}",
        verify=False
    )
    if status_response.status_code == 200:
        status = status_response.json()
        print(f"📊 Call Status:")
        print(f"   Status: {status['status']}")
        print(f"   Phone: {status['phone_number']}")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
```

---

## 🔑 Configuration & Secrets

### Environment Variables (Kubernetes Secrets)

Create/update secrets with:
```bash
kubectl create secret generic gym-call-agent-secrets \
  --from-literal=TWILIO_ACCOUNT_SID='your_sid' \
  --from-literal=TWILIO_AUTH_TOKEN='your_token' \
  --from-literal=TWILIO_PHONE_NUMBER='+1234567890' \
  --from-literal=DEEPGRAM_API_KEY='your_key' \
  --from-literal=OPENAI_API_KEY='your_key' \
  --from-literal=ELEVENLABS_API_KEY='your_key' \
  --from-literal=DATABASE_URL='postgresql://...' \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Required API Keys
1. **Twilio** (https://console.twilio.com)
   - Account SID
   - Auth Token
   - Phone Number (with Voice capabilities)

2. **Deepgram** (https://console.deepgram.com)
   - API Key for speech recognition

3. **OpenAI** (https://platform.openai.com)
   - API Key for GPT-4 LLM

4. **ElevenLabs** (https://elevenlabs.io/app/speech-synthesis)
   - API Key for TTS
   - Voice ID (default: "Rachel" or custom)
   - Get API key from: https://elevenlabs.io/app/settings/api-keys

5. **PostgreSQL Database**
   - Connection string for storing transcripts

---

## 🏗️ Architecture

### Call Flow
1. **Inbound Call** → Twilio receives call → POSTs to `/twilio/voice` webhook
2. **TwiML Response** → Returns `<Connect><Stream>` to establish WebSocket
3. **WebSocket Connection** → Twilio connects to `/twilio/media-stream`
4. **Audio Streaming** → Bidirectional audio over WebSocket:
   - Twilio → Server: μ-law 8kHz audio chunks
   - Server → Twilio: Base64-encoded μ-law 8kHz audio
5. **Speech Recognition** → Deepgram transcribes audio in real-time
6. **LLM Processing** → OpenAI GPT-4 generates contextual responses
7. **Text-to-Speech** → ElevenLabs converts text to natural speech
8. **Audio Resampling** → 24kHz PCM → 8kHz μ-law for Twilio
9. **Call Termination** → After collecting info, AI says goodbye and hangs up
10. **Transcript Storage** → Save conversation to PostgreSQL

### Audio Processing Pipeline

```
Twilio μ-law 8kHz → Decode to PCM → Deepgram (transcription)
                                          ↓
                                      LLM Response
                                          ↓
                        ElevenLabs 24kHz PCM (pcm_24000)
                                          ↓
                    Resample 24kHz → 8kHz (scipy.signal.decimate)
                                          ↓
                            Encode to μ-law (audioop)
                                          ↓
                         Base64 encode → Twilio
```

**CRITICAL:** TTS must output 24kHz for clean 3:1 ratio resampling to 8kHz.
- ✅ ElevenLabs `pcm_24000` format
- ✅ OpenAI TTS outputs 24kHz
- ❌ ElevenLabs `pcm_22050` causes audio artifacts (avoid!)

### Key Components

#### `app/api/twilio.py`
- `/twilio/voice` - Webhook for inbound calls, returns TwiML
- `/twilio/media-stream` - WebSocket endpoint for audio streaming
- `generate_and_send_response()` - Orchestrates LLM → TTS → Audio pipeline

#### `app/services/audio_utils.py`
- `convert_mulaw_to_pcm()` - Decode μ-law to 16-bit PCM
- `convert_pcm16_to_mulaw_8khz()` - Resample PCM to 8kHz and encode μ-law
- `resample_audio()` - High-quality resampling with anti-aliasing
- `detect_voice_activity()` - VAD to prevent AI interruptions

#### `app/services/conversation.py`
- `ConversationState` - Tracks call state, transcriptions, gym info
- `should_ai_speak()` - Determines if enough silence for AI to speak
- `should_end_call()` - Checks if all required info is collected

#### `app/services/llm.py`
- `generate_response()` - OpenAI GPT-4 with conversation history
- Prevents duplicate greetings and repeated questions
- Tracks conversation flow to maintain naturalness

#### `app/services/tts.py`
- `generate_speech()` - ElevenLabs (preferred) or OpenAI TTS (fallback)
- Returns 24kHz PCM audio for clean resampling
- ElevenLabs uses `pcm_24000` format (NOT `pcm_22050`)

---

## 🚨 Common Issues & Solutions

### Issue: "no space left on device"
**Cause:** Docker/k3s image cache fills up Raspberry Pi storage

**Solution:** Run `nuke_and_deploy.sh` which includes cleanup:
```bash
sudo rm -f /tmp/*.tar
sudo docker system prune -af
sudo docker image prune -af
sudo k3s ctr images prune -a
```

### Issue: "ImagePullBackOff"
**Cause:** k3s can't find the image in containerd

**Solution:** Force delete pods and use `nuke_and_deploy.sh`:
```bash
kubectl delete pods -l app=gym-call-agent --force --grace-period=0
./nuke_and_deploy.sh
```

### Issue: "ctr: rpc error: code = Unavailable"
**Cause:** k3s containerd is unstable or restarting

**Solution:** `nuke_and_deploy.sh` handles this with retry logic

### Issue: Static/garbled audio
**Causes:**
1. TTS outputting wrong sample rate (e.g., 22050Hz)
2. Poor resampling algorithm (no anti-aliasing)
3. Custom μ-law encoding bugs

**Solutions:**
1. ✅ Use ElevenLabs `pcm_24000` or OpenAI TTS (both 24kHz)
2. ✅ Use `scipy.signal.decimate` for 3:1 ratio with anti-aliasing
3. ✅ Use Python's `audioop.lin2ulaw()` for reliable μ-law encoding

### Issue: AI interrupts or repeats questions
**Causes:**
1. Insufficient silence detection threshold
2. LLM not aware of previous questions
3. Too little pause after LLM processing

**Solutions:**
1. ✅ Increased `min_silence_seconds` to 3.0s
2. ✅ Added "NEVER repeat questions" to LLM prompt
3. ✅ Added safety check to skip duplicate messages
4. ✅ Increased pause after LLM from 1.0s to 2.5s

### Issue: Call doesn't terminate
**Cause:** WebSocket not closing after final AI message

**Solution:** ✅ Added explicit WebSocket close after `should_end_call` is true

### Issue: 401 Unauthorized from ElevenLabs
**Cause:** Missing or invalid API key

**Solution:** Update Kubernetes secret:
```bash
kubectl patch secret gym-call-agent-secrets -p '{"data":{"ELEVENLABS_API_KEY":"'$(echo -n 'your_actual_key' | base64)'"}}'
kubectl delete pod -l app=gym-call-agent  # Force restart
```

### Issue: SSL certificate verification failed
**Cause:** Using self-signed certificate during development

**Solutions:**
1. For testing: Add `verify=False` to requests
2. For production: Ensure LetsEncrypt cert is provisioned:
   ```bash
   kubectl get certificate gym-call-agent-tls
   kubectl describe certificate gym-call-agent-tls
   ```

---

## 📁 Project Structure

```
gymgym/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── twilio.py              # Twilio webhooks & WebSocket
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py              # Configuration & settings
│   ├── models/
│   │   ├── __init__.py
│   │   └── database.py            # Database models
│   └── services/
│       ├── __init__.py
│       ├── audio_utils.py         # Audio processing utilities
│       ├── conversation.py        # Conversation state management
│       ├── llm.py                 # OpenAI LLM integration
│       ├── transcription.py       # Deepgram speech recognition
│       └── tts.py                 # ElevenLabs/OpenAI TTS
├── k8s/
│   ├── deployment.yaml            # Kubernetes deployment
│   ├── service.yaml               # Kubernetes service
│   ├── ingress.yaml               # Traefik ingress with SSL
│   └── letsencrypt-issuer.yaml    # cert-manager issuer
├── Dockerfile                     # Container definition
├── requirements.txt               # Python dependencies
├── deploy.sh                      # Quick deployment script
├── nuke_and_deploy.sh            # Full rebuild script
├── debug_tts.sh                   # TTS debugging
├── deep_debug.sh                  # Comprehensive debugging
├── test_outbound_call.py         # Test call initiation
└── .env                          # Local environment variables (gitignored)
```

---

## 🎯 Next Steps & Future Phases

### Phase 5: Production Readiness (Planned)
- [ ] Fix ElevenLabs TTS with `pcm_24000` format
- [ ] Comprehensive audio quality testing
- [ ] Monitor disk space and implement auto-cleanup
- [ ] Add health checks and monitoring
- [ ] Implement rate limiting
- [ ] Add comprehensive error handling
- [ ] Set up structured logging with log aggregation
- [ ] Performance testing and optimization

### Phase 6: Database & Analytics (Planned)
- [ ] Complete PostgreSQL schema for gyms and transcripts
- [ ] Add database migration system (Alembic)
- [ ] Build admin dashboard for transcript review
- [ ] Generate analytics and reports
- [ ] Export transcripts to CSV/JSON

### Phase 7: Advanced Features (Future)
- [ ] Multi-language support
- [ ] Custom voice cloning for gym brands
- [ ] Integration with CRM systems
- [ ] Automated follow-up calls
- [ ] A/B testing different conversation flows
- [ ] Real-time call monitoring dashboard

---

## 📝 Important Notes

### TTS Configuration - READ THIS!

**You MUST use ElevenLabs with `pcm_24000` format or OpenAI TTS:**

```python
# ✅ CORRECT - ElevenLabs
"output_format": "pcm_24000"  # 24kHz = clean 3:1 to 8kHz

# ❌ WRONG - Causes static/artifacts
"output_format": "pcm_22050"  # 22050Hz = problematic 2.75625:1 ratio
```

This is **critical** for audio quality. The 24kHz → 8kHz resampling is a clean 3:1 integer ratio that `scipy.signal.decimate` handles perfectly with anti-aliasing. Any other sample rate will cause audio artifacts.

### Kubernetes on Raspberry Pi

k3s on Raspberry Pi can be unstable. Always use `nuke_and_deploy.sh` when:
- Getting `ImagePullBackOff` errors
- Seeing "no space left on device"
- Experiencing mysterious deployment failures
- After making config changes

The script handles k3s restarts, cleanup, and retry logic.

### API Rate Limits

Monitor usage for:
- **Deepgram:** Real-time streaming (concurrent connections)
- **OpenAI:** GPT-4 tokens per minute
- **ElevenLabs:** Characters per month, concurrent requests

### Security Considerations

1. **Never commit secrets** - Use Kubernetes secrets or environment variables
2. **Rotate API keys** regularly
3. **Use LetsEncrypt** for production SSL certificates
4. **Implement webhook signature verification** (Twilio)
5. **Add rate limiting** to prevent abuse
6. **Sanitize all database inputs** to prevent SQL injection

---

## 🐛 Debugging Checklist

When things break, run these in order:

1. **Check pod status:**
   ```bash
   kubectl get pods -l app=gym-call-agent
   ```

2. **Check logs:**
   ```bash
   kubectl logs -l app=gym-call-agent --tail=50 -f
   ```

3. **Run TTS debug:**
   ```bash
   ./debug_tts.sh > debug.txt
   ```

4. **Check disk space:**
   ```bash
   df -h /
   ```

5. **If stuck, nuke it:**
   ```bash
   ./nuke_and_deploy.sh
   ```

6. **Test call:**
   ```bash
   python test_outbound_call.py +16305121365 "Test Gym"
   ```

---

## 📞 Contact & Support

- **Twilio Console:** https://console.twilio.com
- **Deepgram Docs:** https://developers.deepgram.com
- **OpenAI Docs:** https://platform.openai.com/docs
- **ElevenLabs Docs:** https://elevenlabs.io/docs
- **k3s Docs:** https://docs.k3s.io

---

**End of Document**
