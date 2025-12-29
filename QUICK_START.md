# Quick Reference: Start New Chat

## Current Status
✅ **Phase 1 Complete** - Audio processing pipeline working end-to-end

## What Works
- Outbound calling via Twilio
- Real-time audio streaming (WebSocket)
- Audio decoding (μ-law → PCM)
- Voice activity detection
- Call statistics tracking

## What's Next
**Phase 2**: Add Deepgram ASR to transcribe speech → "Let's implement Phase 2 - integrate Deepgram ASR"

## Cost Per Call
~$0.22 per 4-minute call breakdown:
- Twilio: $0.052
- ASR: $0.017  
- LLM: $0.075
- TTS: $0.075
- Infrastructure: $0 (self-hosted)

Optimized: ~$0.07/call with Whisper+Gemini+Google TTS

## Key Files
- `PROJECT_STATUS.md` - Full documentation (read this first)
- `deploy.sh` - Build and deploy to k3s
- `test_outbound_call.py` - Test making calls
- `app/api/twilio.py` - Main audio processing logic
- `app/services/audio_utils.py` - Audio utilities

## Test Command
```bash
python test_outbound_call.py +1YOUR_PHONE "Test"
kubectl logs deployment/gym-call-agent -f
```

## Environment
- Domain: https://bidetking.ddns.net
- Cluster: 3x Raspberry Pi k3s nodes
- Twilio: +1 630 937 3197

## Progress
- [x] Phase 1: Audio Pipeline (DONE)
- [ ] Phase 2: ASR Integration (NEXT)
- [ ] Phase 3: LLM Logic
- [ ] Phase 4: TTS Output  
- [ ] Phase 5: Production Polish

25% complete | ~$0.22/call | 2-3 sessions to MVP

