#!/bin/bash
# Quick TTS debug script

POD=$(sudo kubectl get pods -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

echo "=========================================="
echo "TTS DEBUG - $(date)"
echo "=========================================="
echo ""

echo "📦 Pod: $POD"
echo ""

echo "🔑 API KEYS CONFIGURED:"
echo "-------------------------------------------"
sudo kubectl exec $POD -- env 2>/dev/null | grep -E "ELEVENLABS|OPENAI" | sed 's/=.*/=***/'
echo ""

echo "🔊 TTS INITIALIZATION:"
echo "-------------------------------------------"
sudo kubectl logs $POD --tail=200 2>/dev/null | grep -E "TTS|ElevenLabs|OpenAI TTS" | head -10
echo ""

echo "🎤 LAST CALL - SPEECH FLOW:"
echo "-------------------------------------------"
sudo kubectl logs $POD --tail=500 2>/dev/null | grep -E "Generating|Generated|🔊|📤|audio|Audio|mulaw|Converting" | tail -30
echo ""

echo "❌ ERRORS:"
echo "-------------------------------------------"
sudo kubectl logs $POD --tail=500 2>/dev/null | grep -iE "error|exception|failed|❌" | tail -20
echo ""

echo "📝 FULL RECENT LOGS (last 50 lines):"
echo "-------------------------------------------"
sudo kubectl logs $POD --tail=50 2>/dev/null

