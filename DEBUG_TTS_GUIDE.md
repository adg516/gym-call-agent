# 🛠️ Debug & Monitoring Guide - Phase 4

Quick reference for debugging and monitoring your AI call agent.

---

## 🚀 Quick Debug Commands

### Check Everything at Once
```bash
./test_phase4.sh              # Comprehensive Phase 4 test
```

### Phase-Specific Debugging
```bash
./debug_llm.sh                # Debug Phase 3 (LLM/extraction)
./debug_tts.sh                # Debug Phase 4 (TTS/responses)
./debug_deepgram.sh           # Debug Phase 2 (transcription)
```

### Live Monitoring
```bash
./live_tts_monitor.sh         # Watch conversation in real-time
./check_logs.sh               # Quick log check
```

---

## 📊 What Each Script Shows

### `debug_tts.sh` - TTS Diagnostics
- ✅ OpenAI API key status
- 🚀 TTS client initialization
- 🔊 Speech generation activity
- 💬 AI response generation
- 🔄 Audio format conversion
- 📤 Audio streaming to Twilio
- ❌ TTS errors
- ⚡ Performance metrics

**Run when:** AI doesn't speak or audio is garbled

### `debug_llm.sh` - LLM Diagnostics
- ✅ OpenAI configuration
- 🧠 LLM processing activity
- ✅ Information extraction
- 📊 Collection progress
- 🏋️ Final summaries
- ❌ LLM errors

**Run when:** AI doesn't understand or extract info incorrectly

### `debug_deepgram.sh` - ASR Diagnostics
- ✅ Deepgram API key status
- 🎤 Transcription activity
- 🔊 Audio quality
- ❌ Deepgram errors

**Run when:** Transcriptions are missing or inaccurate

### `live_tts_monitor.sh` - Real-time Watch
Shows conversation flow live:
```
📞 Stream started
🎤 FINAL: "We're open from 6am to 10pm"
🧠 Processing with LLM
✅ Extracted: hours
💬 AI will say: "Great! How much is a day pass?"
🔊 Generating speech
🔄 Converting audio format
📤 Sent 160 bytes of audio
✅ Finished sending AI response
```

**Run when:** You want to see everything happening in real-time

---

## 🎯 Common Issues & Solutions

### Issue: AI doesn't speak at all

**Debug:**
```bash
./debug_tts.sh
```

**Look for:**
- ❌ OPENAI_API_KEY not set
- ⚠️ No TTS generation found
- ❌ TTS errors

**Fix:**
```bash
# Check .env has OPENAI_API_KEY
cat .env | grep OPENAI

# Recreate k8s secret
./create_k8s_secret.sh

# Redeploy
./deploy.sh
```

---

### Issue: Audio is garbled or distorted

**Debug:**
```bash
./debug_tts.sh | grep -A 5 "Audio Format"
```

**Look for:**
- Audio conversion errors
- Wrong sample rates (should be 24000 → 8000)
- Mulaw encoding issues

**Fix:**
```bash
# Try different voice
echo "TTS_VOICE=nova" >> .env
./deploy.sh

# Check conversion logs
sudo kubectl logs -f deployment/gym-call-agent | grep "Converting audio"
```

---

### Issue: AI interrupts gym staff

**Debug:**
```bash
./debug_tts.sh | grep -A 5 "Speaking State"
```

**Look for:**
- `should_ai_speak` returning true too early
- Missing silence detection
- `last_gym_speech_time` not updating

**Fix:**
```bash
# Check conversation timing in code
# Default is 1.5s silence threshold
# May need to increase in conversation.py
```

---

### Issue: AI responses don't make sense

**Debug:**
```bash
./debug_llm.sh                # Check LLM processing
./debug_tts.sh | grep "AI will say"  # See what AI generated
```

**Look for:**
- Missing context in conversation history
- Incorrect information extraction
- LLM errors

**Fix:**
```bash
# Check LLM is working
./debug_llm.sh

# Verify extracted info
sudo kubectl logs deployment/gym-call-agent | grep "Extracted:"
```

---

### Issue: No transcriptions coming through

**Debug:**
```bash
./debug_deepgram.sh
```

**Look for:**
- ❌ DEEPGRAM_API_KEY not set
- Deepgram connection errors
- Audio not reaching Deepgram

**Fix:**
```bash
# Check Deepgram setup
./debug_deepgram.sh

# Verify audio pipeline
./check_logs.sh
```

---

## 📱 Live Monitoring Commands

### Watch entire conversation flow
```bash
./live_tts_monitor.sh
```

### Watch specific components
```bash
# Just TTS activity
sudo kubectl logs -f deployment/gym-call-agent | grep -E "🔊|💬|📤"

# Just transcriptions and responses
sudo kubectl logs -f deployment/gym-call-agent | grep -E "🎤|💬"

# Just LLM processing
sudo kubectl logs -f deployment/gym-call-agent | grep -E "🧠|✅ Extracted"

# Just errors
sudo kubectl logs -f deployment/gym-call-agent | grep -E "❌|Error"
```

---

## 🔍 Detailed Investigation

### Get full logs for specific call
```bash
# Find the call SID first
sudo kubectl logs deployment/gym-call-agent | grep "Call SID:"

# Then filter by that SID
sudo kubectl logs deployment/gym-call-agent | grep "CA1234567890abcdef"
```

### Check pod status
```bash
sudo kubectl get pods -l app=gym-call-agent
sudo kubectl describe pod <pod-name>
```

### Check secrets
```bash
sudo kubectl get secret gym-call-agent-secrets -o yaml
```

### Check environment variables in pod
```bash
POD=$(sudo kubectl get pods -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}')
sudo kubectl exec $POD -- env | grep -E "OPENAI|DEEPGRAM|TWILIO|TTS"
```

---

## 📊 Performance Monitoring

### Check TTS generation times
```bash
sudo kubectl logs deployment/gym-call-agent | grep "Generated.*bytes of audio"
```

### Check LLM response times
```bash
sudo kubectl logs deployment/gym-call-agent | grep "LLM processed transcription"
```

### Check audio conversion times
```bash
sudo kubectl logs deployment/gym-call-agent | grep "Audio ready.*mulaw"
```

---

## 🎬 Testing Workflow

### 1. Pre-flight checks
```bash
./test_phase4.sh
```

### 2. Make test call
```bash
python test_outbound_call.py +YOUR_NUMBER "Phase 4 Test"
```

### 3. Watch live
```bash
./live_tts_monitor.sh
```

### 4. Post-call analysis
```bash
./debug_tts.sh          # Check TTS activity
./debug_llm.sh          # Check extraction results
./view_transcripts.sh   # See final transcript
```

---

## 🆘 Emergency Debugging

### Nothing works
```bash
# Check everything
./test_phase4.sh

# Restart from scratch
./deploy.sh

# Check pod is running
sudo kubectl get pods

# Check pod logs for startup errors
sudo kubectl logs deployment/gym-call-agent | head -50
```

### Find recent errors
```bash
sudo kubectl logs deployment/gym-call-agent | grep -E "❌|Error|Exception" | tail -20
```

### Get last 100 log lines
```bash
sudo kubectl logs deployment/gym-call-agent --tail=100
```

---

## 📚 Log Emoji Guide

- 📞 = Call/Stream events
- 🎤 = Transcriptions (what gym says)
- 🧠 = LLM processing
- ✅ = Extracted information
- 💬 = AI responses (text)
- 🔊 = TTS generation (text→audio)
- 🔄 = Audio conversion
- 📤 = Streaming to Twilio
- 🏁 = Call ending
- ❌ = Errors
- ⚠️  = Warnings
- 📊 = Progress/stats
- 🏋️ = Final summaries

---

**Quick Reference:**
- Debug TTS: `./debug_tts.sh`
- Debug LLM: `./debug_llm.sh`
- Live watch: `./live_tts_monitor.sh`
- Full test: `./test_phase4.sh`

