#!/bin/bash
# 🔍 COMPREHENSIVE DEBUG - Everything you need to know about the last call

echo "════════════════════════════════════════════════════════════════"
echo "🔍 COMPREHENSIVE CALL DEBUG"
echo "════════════════════════════════════════════════════════════════"
date
echo ""

# Get pod name
POD=$(sudo kubectl get pod -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD" ]; then
    echo "❌ No pod running!"
    echo "   Deploy first: ./nuke_and_deploy.sh"
    exit 1
fi

echo "📦 Pod: $POD"
REPLICASET=$(echo $POD | cut -d'-' -f3)
echo "🔄 Replicaset: $REPLICASET"
echo ""

# ============================================================================
# 1. DEPLOYMENT VERIFICATION
# ============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "1️⃣  DEPLOYMENT VERIFICATION"
echo "═══════════════════════════════════════════════════════════════"

if sudo kubectl logs $POD --tail=2000 2>/dev/null | grep -q "\[v2.0-PCM\]"; then
    echo "✅ Code version: v2.0-PCM (LATEST)"
else
    echo "⚠️  Code version: Unknown (may be old)"
fi

if sudo kubectl logs $POD --tail=2000 2>/dev/null | grep -q "output_format=pcm_24000"; then
    echo "✅ API URL: Correct (pcm_24000 in query params)"
else
    echo "❌ API URL: Wrong format"
fi

echo ""

# ============================================================================
# 2. API SERVICES STATUS
# ============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "2️⃣  API SERVICES STATUS"
echo "═══════════════════════════════════════════════════════════════"

# Deepgram
if sudo kubectl logs $POD 2>/dev/null | grep -q "Deepgram live transcription started"; then
    echo "✅ Deepgram: Connected"
else
    echo "❌ Deepgram: Not initialized"
fi

# OpenAI LLM
if sudo kubectl logs $POD 2>/dev/null | grep -q "OpenAI client initialized"; then
    echo "✅ OpenAI LLM: Connected ($(sudo kubectl logs $POD 2>/dev/null | grep 'OpenAI client initialized' | tail -1 | grep -oP 'model: \K[^)]+')"
else
    echo "❌ OpenAI LLM: Not initialized"
fi

# ElevenLabs TTS
if sudo kubectl logs $POD 2>/dev/null | grep -q "ElevenLabs TTS initialized"; then
    VOICE_ID=$(sudo kubectl logs $POD 2>/dev/null | grep 'ElevenLabs TTS initialized' | tail -1 | grep -oP 'voice: \K[^)]+')
    echo "✅ ElevenLabs TTS: Connected (voice: $VOICE_ID)"
    
    # Check content type
    CONTENT_TYPE=$(sudo kubectl logs $POD --tail=1000 2>/dev/null | grep "🎵 Content-Type:" | tail -1)
    if echo "$CONTENT_TYPE" | grep -q "audio/mpeg"; then
        echo "   ⚠️  Format: audio/mpeg (WRONG - will cause static!)"
    elif echo "$CONTENT_TYPE" | grep -qE "octet-stream|not set"; then
        echo "   ✅ Format: PCM (correct)"
    else
        echo "   ? Format: Unknown (no calls yet?)"
    fi
else
    echo "❌ ElevenLabs TTS: Not initialized"
fi

echo ""

# ============================================================================
# 3. LAST CALL - FULL TRANSCRIPT
# ============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "3️⃣  LAST CALL - FULL CONVERSATION"
echo "═══════════════════════════════════════════════════════════════"

# Find the last call's Call SID
LAST_CALL_SID=$(sudo kubectl logs $POD --tail=2000 2>/dev/null | grep "Call SID:" | tail -1 | grep -oP 'CA[a-f0-9]+')

if [ -z "$LAST_CALL_SID" ]; then
    echo "⚠️  No calls found in logs"
else
    echo "📞 Call SID: $LAST_CALL_SID"
    echo ""
    
    # Extract conversation between Stream started and Stream stopped
    sudo kubectl logs $POD --tail=2000 2>/dev/null | \
        awk "/Call SID: $LAST_CALL_SID/,/Stream stopped/" | \
        grep -E "(🎤 FINAL|💬 AI will say|🤖 Generated)" | \
        sed 's/.*🎤 FINAL.* /🏋️  Gym: /' | \
        sed 's/.*💬 AI will say: "/🤖 AI: /' | \
        sed 's/.*🤖 Generated: "/🤖 AI: /' | \
        sed 's/"$//'
fi

echo ""

# ============================================================================
# 4. EXTRACTED INFORMATION
# ============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "4️⃣  EXTRACTED GYM INFORMATION"
echo "═══════════════════════════════════════════════════════════════"

if [ -n "$LAST_CALL_SID" ]; then
    # Look for extracted info
    HOURS=$(sudo kubectl logs $POD --tail=2000 2>/dev/null | \
        awk "/Call SID: $LAST_CALL_SID/,/Stream stopped/" | \
        grep "Hours:" | tail -1 | grep -oP 'Hours: \K.*' | sed 's/ (missing)//')
    
    PRICE=$(sudo kubectl logs $POD --tail=2000 2>/dev/null | \
        awk "/Call SID: $LAST_CALL_SID/,/Stream stopped/" | \
        grep "Price:" | tail -1 | grep -oP 'Price: \K.*' | sed 's/ (missing)//')
    
    CLASSES=$(sudo kubectl logs $POD --tail=2000 2>/dev/null | \
        awk "/Call SID: $LAST_CALL_SID/,/Stream stopped/" | \
        grep "Classes:" | tail -1 | grep -oP 'Classes: \K.*' | sed 's/ (missing)//')
    
    POLICY=$(sudo kubectl logs $POD --tail=2000 2>/dev/null | \
        awk "/Call SID: $LAST_CALL_SID/,/Stream stopped/" | \
        grep "Policy:" | tail -1 | grep -oP 'Policy: \K.*' | sed 's/ (missing)//')
    
    if [ -n "$HOURS" ]; then
        echo "✅ Hours: $HOURS"
    else
        echo "❌ Hours: Not extracted"
    fi
    
    if [ -n "$PRICE" ]; then
        echo "✅ Day Pass Price: $PRICE"
    else
        echo "❌ Day Pass Price: Not extracted"
    fi
    
    if [ -n "$CLASSES" ]; then
        echo "✅ Classes: $CLASSES"
    else
        echo "❌ Classes: Not extracted"
    fi
    
    if [ -n "$POLICY" ]; then
        echo "✅ Drop-in Policy: $POLICY"
    else
        echo "❌ Drop-in Policy: Not extracted"
    fi
    
    # Completion percentage
    COMPLETION=$(sudo kubectl logs $POD --tail=2000 2>/dev/null | \
        awk "/Call SID: $LAST_CALL_SID/,/Stream stopped/" | \
        grep "Completion:" | tail -1 | grep -oP '\d+%')
    
    if [ -n "$COMPLETION" ]; then
        echo ""
        echo "📊 Completion: $COMPLETION"
    fi
else
    echo "⚠️  No call data to analyze"
fi

echo ""

# ============================================================================
# 5. AUDIO QUALITY METRICS
# ============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "5️⃣  AUDIO QUALITY METRICS"
echo "═══════════════════════════════════════════════════════════════"

if [ -n "$LAST_CALL_SID" ]; then
    # TTS generations
    TTS_COUNT=$(sudo kubectl logs $POD --tail=2000 2>/dev/null | \
        awk "/Call SID: $LAST_CALL_SID/,/Stream stopped/" | \
        grep -c "ElevenLabs generated")
    
    echo "🔊 TTS Generations: $TTS_COUNT"
    
    if [ $TTS_COUNT -gt 0 ]; then
        echo ""
        echo "Last few audio generations:"
        sudo kubectl logs $POD --tail=2000 2>/dev/null | \
            awk "/Call SID: $LAST_CALL_SID/,/Stream stopped/" | \
            grep "ElevenLabs generated" | tail -3 | \
            sed 's/.*ElevenLabs generated /  /'
    fi
    
    # Check for streaming issues
    STREAM_ERRORS=$(sudo kubectl logs $POD --tail=2000 2>/dev/null | \
        awk "/Call SID: $LAST_CALL_SID/,/Stream stopped/" | \
        grep -c "WebSocket closed after")
    
    if [ $STREAM_ERRORS -gt 0 ]; then
        echo ""
        echo "⚠️  WebSocket Interruptions: $STREAM_ERRORS"
        echo "   (Audio may have been cut off)"
    fi
else
    echo "⚠️  No call to analyze"
fi

echo ""

# ============================================================================
# 6. ERRORS & WARNINGS
# ============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "6️⃣  ERRORS & WARNINGS"
echo "═══════════════════════════════════════════════════════════════"

if [ -n "$LAST_CALL_SID" ]; then
    ERRORS=$(sudo kubectl logs $POD --tail=2000 2>/dev/null | \
        awk "/Call SID: $LAST_CALL_SID/,/Stream stopped/" | \
        grep -iE "error|exception|failed|❌" | \
        grep -v "deepgram" | \
        grep -v "tasks cancelled" | \
        wc -l)
    
    if [ $ERRORS -eq 0 ]; then
        echo "✅ No errors detected"
    else
        echo "❌ Found $ERRORS error(s):"
        echo ""
        sudo kubectl logs $POD --tail=2000 2>/dev/null | \
            awk "/Call SID: $LAST_CALL_SID/,/Stream stopped/" | \
            grep -iE "error|exception|failed|❌" | \
            grep -v "deepgram" | \
            grep -v "tasks cancelled" | \
            tail -5 | \
            sed 's/^/   /'
    fi
else
    # Check for any recent errors
    RECENT_ERRORS=$(sudo kubectl logs $POD --tail=100 2>/dev/null | \
        grep -iE "error|exception|failed|❌" | \
        grep -v "deepgram" | \
        grep -v "tasks cancelled" | \
        wc -l)
    
    if [ $RECENT_ERRORS -eq 0 ]; then
        echo "✅ No recent errors"
    else
        echo "⚠️  Found $RECENT_ERRORS recent error(s)"
    fi
fi

echo ""

# ============================================================================
# 7. COST ESTIMATE
# ============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "7️⃣  COST ESTIMATE (Last Call)"
echo "═══════════════════════════════════════════════════════════════"

if [ -n "$LAST_CALL_SID" ] && [ $TTS_COUNT -gt 0 ]; then
    # Extract token counts
    TOTAL_TOKENS=$(sudo kubectl logs $POD --tail=2000 2>/dev/null | \
        awk "/Call SID: $LAST_CALL_SID/,/Stream stopped/" | \
        grep "tokens:" | tail -1 | grep -oP 'total_tokens}=\K\d+')
    
    # Extract character count
    CHAR_COUNT=$(sudo kubectl logs $POD --tail=2000 2>/dev/null | \
        awk "/Call SID: $LAST_CALL_SID/,/Stream stopped/" | \
        grep "character-cost" | tail -1 | grep -oP "'character-cost', b'\K\d+'")
    
    # Calculate duration (rough estimate from audio bytes)
    CALL_DURATION=$(sudo kubectl logs $POD --tail=2000 2>/dev/null | \
        awk "/Call SID: $LAST_CALL_SID/,/Stream stopped/" | \
        grep "Total audio duration:" | tail -1 | grep -oP '\d+\.\d+')
    
    echo "📊 Usage:"
    echo "   • Call duration: ${CALL_DURATION:-unknown} seconds"
    echo "   • GPT-4 tokens: ${TOTAL_TOKENS:-0}"
    echo "   • ElevenLabs chars: ${CHAR_COUNT:-0}"
    
    echo ""
    echo "💰 Estimated Costs:"
    
    # Deepgram: ~$0.0043/min for Nova-2
    if [ -n "$CALL_DURATION" ]; then
        DEEPGRAM_COST=$(echo "scale=4; $CALL_DURATION / 60 * 0.0043" | bc)
        echo "   • Deepgram: \$${DEEPGRAM_COST:-0.00} (Nova-2 @ \$0.0043/min)"
    fi
    
    # GPT-4o-mini: $0.150/1M input, $0.600/1M output (rough 50/50 split)
    if [ -n "$TOTAL_TOKENS" ]; then
        GPT_COST=$(echo "scale=4; $TOTAL_TOKENS / 1000000 * 0.375" | bc)
        echo "   • GPT-4o-mini: \$${GPT_COST:-0.00} (\$0.150/\$0.600 per 1M tokens)"
    fi
    
    # ElevenLabs: ~$0.18/1000 chars for Turbo v2.5
    if [ -n "$CHAR_COUNT" ]; then
        ELEVENLABS_COST=$(echo "scale=4; $CHAR_COUNT / 1000 * 0.18" | bc)
        echo "   • ElevenLabs: \$${ELEVENLABS_COST:-0.00} (Turbo @ \$0.18/1K chars)"
    fi
    
    # Twilio: ~$0.0085/min for voice
    if [ -n "$CALL_DURATION" ]; then
        TWILIO_COST=$(echo "scale=4; $CALL_DURATION / 60 * 0.0085" | bc)
        echo "   • Twilio Voice: \$${TWILIO_COST:-0.00} (\$0.0085/min)"
    fi
    
    # Total
    if [ -n "$DEEPGRAM_COST" ] && [ -n "$GPT_COST" ] && [ -n "$ELEVENLABS_COST" ] && [ -n "$TWILIO_COST" ]; then
        TOTAL_COST=$(echo "scale=4; $DEEPGRAM_COST + $GPT_COST + $ELEVENLABS_COST + $TWILIO_COST" | bc)
        echo ""
        echo "   💵 TOTAL: \$${TOTAL_COST} per call"
        
        # Extrapolate to volume
        echo ""
        echo "📈 Volume Estimates:"
        COST_100=$(echo "scale=2; $TOTAL_COST * 100" | bc)
        COST_1000=$(echo "scale=2; $TOTAL_COST * 1000" | bc)
        echo "   • 100 calls/day: \$${COST_100}/day (\$$(echo "scale=0; $COST_100 * 30" | bc)/month)"
        echo "   • 1000 calls/day: \$${COST_1000}/day (\$$(echo "scale=0; $COST_1000 * 30" | bc)/month)"
    fi
else
    echo "⚠️  No call data for cost estimation"
    echo ""
    echo "💰 Typical Cost per Call (estimated):"
    echo "   • Deepgram: ~\$0.001-0.002 (Nova-2, 1-2 min call)"
    echo "   • GPT-4o-mini: ~\$0.0002-0.0005 (600 tokens)"
    echo "   • ElevenLabs: ~\$0.005-0.010 (30-50 chars TTS)"
    echo "   • Twilio Voice: ~\$0.01-0.02 (1-2 min call)"
    echo ""
    echo "   💵 TOTAL: ~\$0.02-0.03 per call"
fi

echo ""

# ============================================================================
# 8. QUICK ACTIONS
# ============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo "8️⃣  QUICK ACTIONS"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Test a new call:"
echo "  python test_outbound_call.py +16305121365 \"Test Gym\""
echo ""
echo "Watch live logs:"
echo "  sudo kubectl logs -f $POD | grep -E '(v2.0-PCM|🎤 FINAL|🤖 AI|Content-Type)'"
echo ""
echo "Redeploy changes:"
echo "  ./nuke_and_deploy.sh"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "Debug complete! $(date)"
echo "════════════════════════════════════════════════════════════════"



