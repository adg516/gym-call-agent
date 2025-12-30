#!/bin/bash
# Full diagnostic - run DURING a call to see what's happening

POD="gym-call-agent-7cdbf4db75-p5fg5"  # From your debug.txt

echo "=== CHECKING POD: $POD ==="
echo ""

echo "1. TTS INITIALIZATION (should happen at startup):"
echo "---"
sudo kubectl logs $POD 2>/dev/null | grep -i "tts" | head -10
echo ""

echo "2. LLM SERVICE STATUS:"
echo "---"
sudo kubectl logs $POD 2>/dev/null | grep -i "llm" | head -10
echo ""

echo "3. CHECKING FOR NEW CODE MARKERS:"
echo "---"
if sudo kubectl logs $POD --tail=2000 2>/dev/null | grep -q "length:.*chars"; then
    echo "✅ NEW code detected (improved logging)"
else
    echo "❌ OLD code (or no TTS calls yet)"
fi
echo ""

echo "4. LAST CALL - AI RESPONSES:"
echo "---"
sudo kubectl logs $POD --tail=500 2>/dev/null | grep -E "(Generating AI|💬 AI will say|🔊)" | tail -10
echo ""

echo "5. LAST CALL - ERRORS:"
echo "---"
sudo kubectl logs $POD --tail=500 2>/dev/null | grep -iE "error|exception|failed" | grep -v "deepgram" | tail -10
echo ""

echo "6. ENVIRONMENT CHECK:"
echo "---"
sudo kubectl exec $POD -- env 2>/dev/null | grep -E "(ELEVENLABS|OPENAI)_API_KEY" | head -5
echo ""

echo "🎯 DIAGNOSIS:"
echo "---"
if sudo kubectl logs $POD 2>/dev/null | grep -q "✅.*TTS initialized"; then
    echo "✅ TTS is initialized"
else
    echo "❌ TTS NOT initialized - this is the problem!"
fi

if sudo kubectl logs $POD --tail=500 2>/dev/null | grep -q "Generating AI"; then
    echo "✅ LLM is generating responses"
else
    echo "❌ LLM NOT generating - check conversation logic"
fi

