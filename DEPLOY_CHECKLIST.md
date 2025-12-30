# ✅ Phase 2 Deployment Checklist

## Pre-Deployment Verification

- [ ] Deepgram account created
- [ ] Deepgram API key obtained
- [ ] API key added to `/home/adggda/gymgym/.env`
- [ ] `.env` file has: `DEEPGRAM_API_KEY=your_key_here`

---

## Deployment Steps (Run These)

```bash
cd /home/adggda/gymgym
```

### Step 1: Create Kubernetes Secret
```bash
./create_k8s_secret.sh
```
**Expected:** `✅ Secret created/updated successfully!`

### Step 2: Deploy Updated Code
```bash
./deploy.sh
```
**Expected:** 
- `🏗️  Building Docker image...`
- `📦 Loading into k3s...`
- `✅ Deployment complete!`

### Step 3: Test Call
```bash
python test_outbound_call.py +1YOUR_PHONE "Deepgram Test"
```
**Expected:** Call initiated with SID

### Step 4: Watch Logs (new terminal)
```bash
sudo kubectl logs deployment/gym-call-agent -f
```

### Step 5: Answer Call & Talk
Say things like:
- "Hello, this is a test"
- "Testing one two three"
- "Can you hear me?"

---

## Success Indicators

Look for these in the logs:

- [ ] `📞 Stream started`
- [ ] `✅ Deepgram live transcription started`
- [ ] `🎤 Transcription [confidence]: text` messages appear
- [ ] Transcriptions match what you said
- [ ] `📝 TRANSCRIPTION SUMMARY` at end of call
- [ ] Full conversation text displayed

---

## Example Success Log

```
INFO:     Twilio Media Stream WebSocket connected
INFO:     📞 Stream started
INFO:        Stream SID: MZxxxxxxxx
INFO:        Call SID: CAxxxxxxxx
INFO:     🔌 WebSocket connected to Twilio
INFO:     ✅ Deepgram live transcription started
INFO:     🗣️  Speech segment detected! Level=0.156, Segment #1
INFO:     🎤 Transcription [0.95]: Hello, this is a test
INFO:     🗣️  Speech segment detected! Level=0.142, Segment #2
INFO:     🎤 Transcription [0.89]: Testing one two three
INFO:     🛑 Stream stopped - MZxxxxxxxx
INFO:     ============================================================
INFO:     📊 CALL STATISTICS
INFO:     ============================================================
INFO:     Total frames received: 234
INFO:     Speech segments detected: 2
INFO:     ============================================================
INFO:     📝 TRANSCRIPTION SUMMARY
INFO:     ============================================================
INFO:     Total transcriptions: 2
INFO:     
INFO:     Full conversation:
INFO:       [1] ✓ Hello, this is a test
INFO:       [2] ✓ Testing one two three
INFO:     ============================================================
```

---

## Troubleshooting

### ❌ "DEEPGRAM_API_KEY not set"
**Cause:** Secret not created or not loaded
**Fix:**
```bash
./create_k8s_secret.sh
./deploy.sh  # Redeploy to pick up secret
```

### ❌ "Failed to initialize Deepgram"
**Cause:** Invalid API key or Deepgram service issue
**Fix:**
1. Verify API key: Login to Deepgram console
2. Check credits remaining
3. Regenerate API key if needed
4. Update `.env` and run `./create_k8s_secret.sh`

### ❌ No transcriptions appearing
**Check:**
1. Is Deepgram connected? Look for: `✅ Deepgram live transcription started`
2. Is audio loud enough? Audio level should be > 0.02
3. Are you actually speaking during the call?

### ❌ Pod not starting
```bash
sudo kubectl get pods -l app=gym-call-agent
sudo kubectl describe pod <pod-name>
sudo kubectl logs deployment/gym-call-agent
```

---

## Verification Commands

### Check secret exists:
```bash
sudo kubectl get secret gym-call-agent-secrets
```

### Check deployment status:
```bash
sudo kubectl get deployment gym-call-agent
sudo kubectl get pods -l app=gym-call-agent
```

### Check logs:
```bash
sudo kubectl logs deployment/gym-call-agent --tail=100
```

### Check environment variables in pod:
```bash
POD=$(sudo kubectl get pod -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}')
sudo kubectl exec $POD -- env | grep -E "(DEEPGRAM|TWILIO)"
```

---

## After Successful Test

Once you see transcriptions working:

✅ Phase 2 Complete!

**Next:** Tell me "Phase 2 works! Let's implement Phase 3"

Phase 3 will add:
- GPT-4o-mini LLM integration
- Intelligent conversation logic
- Structured data extraction
- Response generation

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `./create_k8s_secret.sh` | Create/update k8s secret |
| `./deploy.sh` | Build & deploy new code |
| `python test_outbound_call.py +1PHONE "Name"` | Make test call |
| `sudo kubectl logs deployment/gym-call-agent -f` | Watch logs live |
| `sudo kubectl get pods` | Check pod status |
| `sudo kubectl rollout restart deployment/gym-call-agent` | Restart app |

---

## Files to Read

1. **First:** `PHASE2_SUMMARY.md` - High-level overview
2. **Deploy:** `PHASE2_COMPLETE.md` - Deployment guide
3. **Details:** `PHASE2_DEPLOYMENT.md` - Technical details
4. **Always:** `QUICK_START.md` - Quick reference

---

*Phase 2: Speech Recognition Complete ✅*

