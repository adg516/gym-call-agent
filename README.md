# 🤖 Gym Call Agent - AI Phone Assistant

An AI-powered phone agent that calls gyms to gather information about day passes, hours, pricing, and classes, then provides a clean summary.

## 🎉 Current Status: Phase 2 Complete!

✅ **Working Features:**
- Outbound calling via Twilio
- Real-time speech transcription (99-100% accuracy!)
- Automatic transcript generation
- Kubernetes deployment

## 🚀 Quick Start

```bash
# Make a test call
python test_outbound_call.py +16305121365 "Test call"

# View the transcript
./view_transcripts.sh
```

**Example output:**
```
Call Transcript
============================================================
Duration: 8.90 seconds
Speech frames: 157 (35.3%)

[1] [0.99] Please, is this working?
[2] [1.00] I'd really like this to work. That'd be awesome. Thank you.
```

## 📋 Project Phases

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Complete | Audio pipeline (Twilio, WebSocket streaming) |
| Phase 2 | ✅ Complete | Speech recognition (Deepgram ASR) |
| Phase 3 | ⏳ Next | LLM integration (GPT-4/Claude) |
| Phase 4 | 📅 Planned | Text-to-speech (AI responses) |
| Phase 5 | 📅 Planned | Production features (Redis, admin UI) |

**Progress:** 40% Complete

## 🏗️ Architecture

```
Phone Call
    ↓
Twilio Voice API
    ↓
FastAPI Server (K8s)
    ↓
Deepgram ASR
    ↓
Transcript Files
    ↓
[Phase 3: LLM Processing]
    ↓
[Phase 4: AI Response via TTS]
```

## 🛠️ Tech Stack

- **Backend:** FastAPI (Python)
- **Telephony:** Twilio Voice + Media Streams
- **Speech-to-Text:** Deepgram
- **Infrastructure:** K3s (Kubernetes) on Raspberry Pi
- **Coming:** OpenAI GPT-4, Redis, React admin UI

## 📚 Documentation

**Start Here:**
- [`SESSION_HANDOFF.md`](SESSION_HANDOFF.md) - Complete handoff for new developers
- [`QUICK_START.md`](QUICK_START.md) - Quick reference & commands
- [`PROJECT_STATUS.md`](PROJECT_STATUS.md) - Detailed project status

**Technical:**
- [`PHASE2_TRANSCRIPTION_COMPLETE.md`](PHASE2_TRANSCRIPTION_COMPLETE.md) - Phase 2 summary & bugs fixed
- [`NEXT_STEPS.md`](NEXT_STEPS.md) - Detailed Phase 3-5 plans
- [`IMPLEMENTATION_NOTES.md`](IMPLEMENTATION_NOTES.md) - Architecture & technical details

**Guides:**
- [`TRANSCRIPT_GUIDE.md`](TRANSCRIPT_GUIDE.md) - How to access transcripts
- [`TRANSCRIPTION_TIPS.md`](TRANSCRIPTION_TIPS.md) - Improve transcription accuracy
- [`DEPLOY_CHECKLIST.md`](DEPLOY_CHECKLIST.md) - Deployment procedures

## 🔑 Environment Setup

Create `.env` file:
```bash
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+1...
DEEPGRAM_API_KEY=...
```

Deploy secrets to Kubernetes:
```bash
./create_k8s_secret.sh
```

## 🚢 Deployment

```bash
# Build and deploy to k3s
./deploy.sh

# Check status
sudo kubectl get pods -l app=gym-call-agent

# View logs
sudo kubectl logs -f deployment/gym-call-agent
```

## 🧪 Testing

```bash
# Make a test call
python test_outbound_call.py +YOUR_NUMBER "Testing transcription"

# View transcripts
./view_transcripts.sh

# Check logs
./check_logs.sh

# Debug Deepgram
./debug_deepgram.sh
```

## 💰 Cost (Current)

- **Per 10-minute call:** ~$0.15
  - Twilio: $0.01/min
  - Deepgram: $0.0043/min

**Future with LLM + TTS:** ~$0.35/call

## 🎯 Next Steps

**Phase 3: LLM Integration**
1. Add OpenAI SDK
2. Create LLM service (`app/services/llm.py`)
3. Design conversation prompts
4. Extract structured data (hours, pricing, classes)
5. Implement decision logic

See [`NEXT_STEPS.md`](NEXT_STEPS.md) for detailed plans.

## 🐛 Known Issues

- Minor: "Error closing Deepgram: a coroutine was expected, got None"
  - Cosmetic only, doesn't affect functionality

## 📊 Performance

- **Transcription Accuracy:** 99-100%
- **Latency:** <1 second
- **Uptime:** Stable on Raspberry Pi k3s

## 🤝 Contributing

This is a personal learning project, but the documentation should help you:
1. Read [`SESSION_HANDOFF.md`](SESSION_HANDOFF.md)
2. Test current system
3. Start with Phase 3 tasks in [`NEXT_STEPS.md`](NEXT_STEPS.md)

## 📝 License

Personal project - Use as reference/learning material

## 🙏 Acknowledgments

- Built with Twilio, Deepgram, and FastAPI
- Deployed on Raspberry Pi k3s cluster
- Debugged with lots of coffee ☕

---

**Status:** Phase 2 Complete ✅ - Ready for LLM Integration!

**Last Updated:** December 30, 2025
