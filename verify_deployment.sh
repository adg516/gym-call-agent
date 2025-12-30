#!/bin/bash
# Verify if new code is deployed

POD=$(sudo kubectl get pod -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD" ]; then
    echo "❌ No pod found!"
    exit 1
fi

echo "📦 Pod: $POD"
echo ""

# Check if new code has the improved logging
echo "🔍 Checking for NEW code markers..."
echo ""

# Look for the new normalization logging
if sudo kubectl logs $POD --tail=500 2>/dev/null | grep -q "Normalizing audio"; then
    echo "✅ NEW CODE DEPLOYED - Found 'Normalizing audio' log"
else
    echo "❌ OLD CODE STILL RUNNING - Missing 'Normalizing audio' log"
fi

# Look for new ElevenLabs logging format
if sudo kubectl logs $POD --tail=500 2>/dev/null | grep -q "length:.*chars"; then
    echo "✅ NEW CODE DEPLOYED - Found improved ElevenLabs logging"
else
    echo "❌ OLD CODE STILL RUNNING - Missing improved logging"
fi

# Check pod age
AGE=$(sudo kubectl get pod $POD -o jsonpath='{.status.startTime}')
echo ""
echo "📅 Pod started: $AGE"
echo ""

# Show image ID
IMAGE=$(sudo kubectl get pod $POD -o jsonpath='{.spec.containers[0].image}')
echo "🐳 Image: $IMAGE"

echo ""
echo "To force new deployment, run:"
echo "  sudo kubectl delete pod $POD"
echo "  (New pod will auto-create with fresh image)"

