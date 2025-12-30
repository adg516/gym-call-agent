# Conversation Flow Improvements

## Issues Fixed
1. **Duplicate greetings/questions** - AI was asking about hours twice
2. **Interrupting gym staff** - Not waiting long enough for them to finish
3. **Robotic voice** - Voice quality improvements

## Changes Made

### 1. Voice Quality (`app/core/config.py`)
- **Model**: `tts-1` → `tts-1-hd` (higher quality)
- **Voice**: `alloy` → `nova` (most natural/conversational)
- **Speed**: `1.0` → `0.95` (slightly slower for more natural speech)

### 2. Silence Detection (`app/services/conversation.py`)
- **Increased minimum silence**: `1.5s` → `2.5s` before AI speaks
- Gives gym staff more time to continue their thought

### 3. Initial Greeting Logic (`app/api/twilio.py`)
- **Longer initial wait**: `1.5s` → `2.0s` for call to fully connect
- **Smart greeting**: Only send initial greeting if gym hasn't spoken yet
- Prevents duplicate "What are your operating hours?" questions

### 4. Response Timing (`app/api/twilio.py`)
- **Post-transcription wait**: `1.0s` → `2.5s` after gym staff speaks
- Allows them to finish multi-part responses naturally

### 5. Question Logic (`app/services/llm.py`)
- **First message handling**: Better detection of when to greet vs ask
- **Context awareness**: Checks if hours were already provided in greeting
- **LLM prompt improvement**: Added "NEVER repeat a question" rule
- **Conversation tracking**: Better check of what was already asked

## Expected Behavior

### Before:
```
[Start]
AI: "What are your operating hours? Thank you!"
Gym: "Hey. This is 24 Hour Fitness."
AI: "Hi! I'm calling to ask about your gym. What are your operating hours?"
❌ Duplicate question, interrupts
```

### After:
```
[Start - 2s pause]
[If gym speaks first:]
  Gym: "Hey. This is 24 Hour Fitness."
  [2.5s pause]
  AI: "Hi! I'm calling to ask about your gym. What are your operating hours?"

[If gym silent:]
  AI: "Hi! I'm calling to ask about your gym. What are your operating hours?"
  [2.5s pause for response]
  Gym: "We're open 24 hours."
  [2.5s pause]
  AI: "Thanks! And what's your day pass price?"
```

✅ No duplicates, natural flow, proper wait times

## Deploy
```bash
./nuke_and_deploy.sh
```

## Test
Make a test call and check the flow with:
```bash
python test_outbound_call.py +1XXXXXXXXXX "Test Gym"
./debug.sh
```

The conversation should now feel more natural with:
- Better voice quality (nova, HD, slower)
- No interruptions (2.5s pauses)
- No duplicate questions
- Smarter initial greeting

