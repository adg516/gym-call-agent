# Phase 2 - Deepgram ASR Integration: Deployment Guide

## ✅ What Was Implemented

Phase 2 adds real-time speech recognition to your call agent using Deepgram ASR.

### Changes Made:
1. ✅ Added `deepgram-sdk==3.8.3` to requirements.txt
2. ✅ Updated `config.py` with `deepgram_api_key` setting
3. ✅ Integrated Deepgram WebSocket in `twilio.py`:
   - Connects to Deepgram's live transcription API
   - Streams μ-law audio directly (no conversion needed!)
   - Receives real-time transcriptions with confidence scores
   - Logs transcripts as they arrive
   - Shows full conversation summary at call end
4. ✅ Updated k8s deployment to use secrets for API keys
5. ✅ Created helper script to create k8s secret from .env

---

## 🚀 Deployment Steps

### Step 1: Create Kubernetes Secret

This loads your API keys from `.env` into a k8s secret:

```bash
cd /home/adggda/gymgym
./create_k8s_secret.sh
```

**Expected output:**
```
🔐 Creating Kubernetes secret from .env file...
✅ Secret created/updated successfully!
```

### Step 2: Deploy Updated Code

Run the existing deploy script which will:
- Build new Docker image with deepgram-sdk
- Load into k3s
- Restart deployment (which will pick up the secrets)

```bash
cd /home/adggda/gymgym
./deploy.sh
```

**Expected output:**
```
🏗️  Building Docker image...
💾 Saving image to tar...
📦 Loading into k3s...
🔄 Restarting deployment...
⏳ Waiting for rollout...
✅ Deployment complete!
```

### Step 3: Verify Deployment

Check that the pod is running and has the secrets:

```bash
# Check pod status
kubectl get pods -l app=gym-call-agent

# Check logs for startup messages
kubectl logs deployment/gym-call-agent --tail=50

# Should see:
# INFO:     Started server process
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
```

---

## 🧪 Testing Phase 2

### Test 1: Make a Call to Your Own Phone

```bash
cd /home/adggda/gymgym
python test_outbound_call.py +1YOUR_PHONE "Deepgram Test"
```

### Test 2: Watch Logs in Real-Time

In another terminal:

```bash
kubectl logs deployment/gym-call-agent -f
```

### Test 3: Talk and Verify Transcriptions

1. Answer the call
2. Say something like: "Hello, this is a test call"
3. Watch the logs for transcription output

**Expected log output:**
```
📞 Stream started
✅ Deepgram live transcription started
🗣️  Speech segment detected! Level=0.156, Segment #1
🎤 Transcription [0.95]: Hello, this is a test call
🗣️  Speech segment detected! Level=0.142, Segment #2
🎤 Transcription [0.87]: How can I help you today?
...
🛑 Stream stopped
📊 CALL STATISTICS
...
📝 TRANSCRIPTION SUMMARY
Total transcriptions: 5
Full conversation:
  [1] ✓ Hello, this is a test call
  [2] ✓ How can I help you today?
  [3] ... Um, let me check
  [4] ✓ Yes, we're open
  [5] ✓ Thanks for calling
```

---

## 🎯 What to Look For

### Success Indicators:
- ✅ `✅ Deepgram live transcription started` in logs
- ✅ `🎤 Transcription [confidence]: text` messages appear
- ✅ Transcriptions match what was said on the call
- ✅ `📝 TRANSCRIPTION SUMMARY` shows full conversation

### Potential Issues:

**Issue 1: "DEEPGRAM_API_KEY not set"**
```
⚠️  DEEPGRAM_API_KEY not set - transcription disabled
```
**Fix:** Run `./create_k8s_secret.sh` and redeploy

**Issue 2: "Failed to initialize Deepgram"**
```
❌ Failed to initialize Deepgram: [error details]
```
**Fix:** Check Deepgram API key is valid, verify you have credits

**Issue 3: No transcriptions appear**
- Check that you're actually speaking (audio level should show > 0.02)
- Verify Deepgram connection started successfully
- Check for Deepgram errors in logs

---

## 📊 What Phase 2 Gives You

### Before Phase 2:
- ✅ Audio streaming works
- ✅ Can detect speech vs silence
- ❌ No idea what's being said

### After Phase 2:
- ✅ Audio streaming works
- ✅ Can detect speech vs silence
- ✅ **Real-time transcription of conversation**
- ✅ Full text of what gym employee says
- ✅ Confidence scores for each transcription
- ✅ Ready for LLM integration (Phase 3)

---

## 🔜 Next Phase

**Phase 3: LLM Integration**
- Take transcriptions from Deepgram
- Send to GPT-4o-mini
- Generate intelligent responses
- Extract structured data (pricing, hours, etc.)

Once Phase 2 is working and you can see transcriptions, say:
**"Let's implement Phase 3 - add LLM logic to respond intelligently"**

---

## 💡 Key Technical Details

### Why μ-law Direct Streaming Works:
- Deepgram natively supports μ-law encoding
- No need to convert to PCM first (saves CPU)
- Lower latency (no conversion overhead)
- Configured with: `encoding="mulaw"`, `sample_rate=8000`

### Interim Results:
- Set `interim_results=True` to get partial transcriptions
- Shows "..." for partial, "✓" for final
- Useful for real-time responsiveness in future phases

### Transcription Flow:
```
Twilio → μ-law audio → Your Server → Deepgram WebSocket
                                          ↓
                                    Transcription events
                                          ↓
                                    Logged & stored
                                          ↓
                                    Summary at call end
```

---

*Phase 2 Complete: Speech Recognition ✅*
*Next: Phase 3 - LLM Integration*

