#!/bin/bash
# Definitive deployment verification

echo "🔍 DEPLOYMENT VERIFICATION"
echo "=========================="
echo ""

POD=$(sudo kubectl get pod -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD" ]; then
    echo "❌ No pod running!"
    echo "   Run: ./nuke_and_deploy.sh"
    exit 1
fi

echo "📦 Pod: $POD"
echo ""

# Check for version marker
echo "🔍 Checking for v2.0-PCM marker..."
if sudo kubectl logs $POD --tail=1000 2>/dev/null | grep -q "\[v2.0-PCM\]"; then
    echo "✅ NEW CODE CONFIRMED - Found [v2.0-PCM] marker"
    NEW_CODE=true
else
    echo "❌ OLD CODE - Missing [v2.0-PCM] marker"
    NEW_CODE=false
fi
echo ""

# Check URL format
echo "🔍 Checking API URL format..."
if sudo kubectl logs $POD --tail=1000 2>/dev/null | grep -q "output_format=pcm_24000"; then
    echo "✅ Correct URL - output_format in query params"
else
    echo "❌ Wrong URL - output_format not in query params"
fi
echo ""

# Check content-type
echo "🔍 Checking Content-Type from ElevenLabs..."
CONTENT_TYPE=$(sudo kubectl logs $POD --tail=1000 2>/dev/null | grep "🎵 Content-Type:" | tail -1)
if [ -n "$CONTENT_TYPE" ]; then
    echo "$CONTENT_TYPE"
    if echo "$CONTENT_TYPE" | grep -q "audio/mpeg"; then
        echo "❌ WRONG - Still getting MPEG!"
    elif echo "$CONTENT_TYPE" | grep -q "octet-stream\|not set"; then
        echo "✅ CORRECT - Getting raw PCM data!"
    fi
else
    echo "⚠️  No TTS calls logged yet (make a test call)"
fi
echo ""

# Summary
echo "=========================="
if [ "$NEW_CODE" = true ]; then
    echo "✅ v2.0-PCM CODE IS DEPLOYED"
    echo ""
    echo "Make a test call to verify audio quality:"
    echo "  python test_outbound_call.py +16305121365 \"Test\""
    echo ""
    echo "Monitor during call:"
    echo "  sudo kubectl logs -f $POD | grep -E '(v2.0-PCM|Content-Type)'"
else
    echo "❌ OLD CODE STILL RUNNING"
    echo ""
    echo "Deploy new code:"
    echo "  ./nuke_and_deploy.sh"
fi




