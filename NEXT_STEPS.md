# 🚀 Next Steps - Phase 3: LLM Integration

**Current Status:** Phase 2 Complete ✅ (ASR working perfectly)  
**Next Phase:** AI-Powered Conversation

## 🎯 Phase 3: Intelligent Conversation (LLM Integration)

### Goals
Build an AI agent that can:
1. Understand what the gym receptionist says
2. Ask intelligent follow-up questions
3. Extract structured information (hours, pricing, classes)
4. Handle natural conversation flow
5. Know when to end the call

### Implementation Plan

#### Step 1: Choose LLM Provider
**Options:**
- **OpenAI GPT-4** - Best for complex reasoning
- **Anthropic Claude** - Great for long context
- **OpenAI GPT-3.5-turbo** - Faster, cheaper

**Recommendation:** Start with GPT-4 Turbo for best results

#### Step 2: Design Conversation Flow

```
Call Start
    ↓
AI: "Hi, I'm calling to ask about day passes and hours. Are you open today?"
    ↓
Listen → Transcribe → Process with LLM
    ↓
Extract Info:
- Hours: "9am-10pm"
- Day Pass: "$25"
- Classes: "Yoga at 6pm"
    ↓
Need more info? → Ask follow-up → Loop
    ↓
Got everything? → Thank them → End call
```

#### Step 3: Implement LLM Integration

**Files to Modify:**
```
app/
├── services/
│   ├── llm.py           # NEW: LLM client wrapper
│   └── conversation.py  # NEW: Conversation manager
└── api/
    └── twilio.py        # MODIFY: Add LLM processing
```

**Example Code:**
```python
# app/services/llm.py
from openai import AsyncOpenAI

class LLMService:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        
    async def process_transcript(
        self, 
        conversation_history: list,
        latest_transcript: str
    ) -> dict:
        """
        Process transcription and decide next action.
        
        Returns:
        {
            "extracted_info": {...},
            "next_question": "...",
            "should_end_call": bool
        }
        """
        # Build prompt with conversation history
        # Send to GPT-4
        # Parse response
        # Return structured data
```

**Prompt Template Example:**
```python
SYSTEM_PROMPT = """
You are an AI assistant calling gyms to gather information.

Your goal: Get the following information:
- Operating hours
- Day pass pricing
- Available classes/schedules
- Drop-in policies

Guidelines:
- Be polite and brief
- Ask one question at a time
- Thank them and end call when you have all info
- If they can't answer, politely end the call

Current info collected:
{collected_info}

Latest from gym: "{latest_transcript}"

What should you ask next? Or should you end the call?
"""
```

#### Step 4: Add State Management

**Conversation State:**
```python
@dataclass
class ConversationState:
    call_sid: str
    gym_name: str
    collected_info: dict
    conversation_history: list
    questions_asked: list
    should_end: bool = False
```

**Store in Memory (Phase 3) or Redis (Phase 5)**

#### Step 5: Test with Simple Prompts

Start simple:
1. Transcribe: "Hello, we're open 9-5"
2. LLM Extract: `{"hours": "9am-5pm"}`
3. LLM Decide: "Ask about day pass pricing"
4. (Phase 4 will speak this response)

### Dependencies to Add

```txt
# requirements.txt
openai>=1.0.0        # For GPT integration
# OR
anthropic>=0.7.0     # For Claude integration

redis>=5.0.0         # For state storage (Phase 5)
pydantic>=2.0.0      # For data validation (already have)
```

### Environment Variables

```bash
# .env
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...

# For Phase 5
REDIS_URL=redis://localhost:6379
```

## 🎯 Phase 4: Text-to-Speech (TTS)

### Goals
- Convert LLM responses to speech
- Send audio back to caller
- Create natural conversation flow

### Implementation Plan

**Options:**
1. **Deepgram TTS** (since we already use them for ASR)
2. **OpenAI TTS** (natural-sounding voices)
3. **ElevenLabs** (most realistic, pricey)
4. **Google Cloud TTS** (good quality, cheap)

**Recommended:** Deepgram TTS (consistency) or OpenAI TTS (quality)

### Key Challenges
1. Convert TTS output to μ-law format for Twilio
2. Stream audio back through Twilio Media Stream
3. Handle timing (don't interrupt the person)
4. Detect when person is done speaking

### Files to Create
```
app/
├── services/
│   └── tts.py           # NEW: TTS client
└── api/
    └── twilio.py        # MODIFY: Send audio back
```

## 🎯 Phase 5: Production Features

### Must-Haves for Production

**1. Persistent Storage (Redis)**
- Store conversation state
- Cache gym information
- Track call history

**2. Admin Interface**
- View call logs
- See transcripts
- Manage gym list
- Monitor system health

**3. Error Handling**
- Retry failed calls
- Handle API rate limits
- Graceful degradation
- Alert on failures

**4. Security**
- API authentication
- Rate limiting
- Input validation
- Secure secrets management

**5. Monitoring**
- Prometheus metrics
- Grafana dashboards
- Log aggregation (ELK stack?)
- Cost tracking

**6. Call Features**
- Call recording
- Voicemail detection
- Business hours detection
- Multi-language support

### Infrastructure Improvements

**Current: Raspberry Pi k3s**
- Good for development
- Limited resources
- Single point of failure

**Production Options:**
1. **AWS EKS** - Managed Kubernetes
2. **Google GKE** - Good for ML workloads
3. **DigitalOcean** - Simple, cheap
4. **Keep Raspberry Pi** - For learning/personal use

### Cost Estimates (Monthly)

**Current MVP:**
- Twilio: ~$1/1000 min
- Deepgram: ~$0.0043/min
- **Total per 10-min call:** ~$0.05

**Phase 3 (+ LLM):**
- OpenAI GPT-4: ~$0.01-0.03/1000 tokens
- **Total per call:** ~$0.10-0.20

**Phase 4 (+ TTS):**
- OpenAI TTS: ~$15/1M chars
- **Total per call:** ~$0.15-0.30

**Phase 5 (Production):**
- Infrastructure: $50-200/month
- Monitoring: $20-50/month
- **Total:** ~$100-300/month + per-call costs

## 📝 Immediate Next Steps

### For New Chat/Session:

1. **Read These Files First:**
   - `QUICK_START.md` - Current status
   - `PHASE2_TRANSCRIPTION_COMPLETE.md` - What's working
   - `IMPLEMENTATION_NOTES.md` - Technical details
   - `app/api/twilio.py` - Main code (lines 140-210 for Deepgram)

2. **Test Current System:**
   ```bash
   python test_outbound_call.py +YOUR_NUMBER "Test"
   ./view_transcripts.sh
   ```

3. **Start Phase 3:**
   - Add OpenAI SDK to requirements
   - Create `app/services/llm.py`
   - Build simple prompt template
   - Test with mock conversations

4. **Keep It Simple:**
   - Start with pre-written questions (not full AI)
   - Extract basic info first (hours only)
   - Add complexity gradually

## 🎓 Learning Resources

**Twilio:**
- Media Streams: https://www.twilio.com/docs/voice/media-streams
- TwiML: https://www.twilio.com/docs/voice/twiml

**Deepgram:**
- Live Streaming: https://developers.deepgram.com/docs/live-streaming
- TTS: https://developers.deepgram.com/docs/tts

**OpenAI:**
- GPT-4: https://platform.openai.com/docs/guides/gpt
- TTS: https://platform.openai.com/docs/guides/text-to-speech

**Conversational AI:**
- State machines for dialogs
- Intent recognition
- Entity extraction
- Context management

## 🏆 Success Criteria

### Phase 3 Complete When:
- [ ] LLM can process transcriptions
- [ ] AI extracts hours, pricing, classes
- [ ] System knows what to ask next
- [ ] Call ends gracefully when done

### Phase 4 Complete When:
- [ ] AI responses are spoken back
- [ ] Natural conversation flow works
- [ ] Timing is correct (no interruptions)

### Phase 5 Complete When:
- [ ] System handles 100+ calls/day
- [ ] Admin can view all data
- [ ] Errors are handled gracefully
- [ ] Monitoring shows system health

---

**You're 40% Done!** 🎉

✅ Phase 1: Audio Pipeline  
✅ Phase 2: ASR Integration  
⏳ Phase 3: LLM (Next)  
⏳ Phase 4: TTS  
⏳ Phase 5: Production Polish

