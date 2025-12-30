#!/bin/bash
# Quick deploy of PCM fix
set -e

echo "🔊 Deploying PCM Format Fix..."
echo ""

# Load into k3s
echo "📦 Loading image..."
sudo k3s ctr images import /tmp/gym-agent-pcm-fix.tar

# Delete pod to force restart
echo "🔄 Restarting pod..."
sudo kubectl delete pod -l app=gym-call-agent

# Wait for new pod
echo "⏳ Waiting for new pod..."
sleep 5
sudo kubectl wait --for=condition=ready pod -l app=gym-call-agent --timeout=60s

# Get new pod name
POD=$(sudo kubectl get pod -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}')
echo "✅ New pod: $POD"
echo ""

echo "🔍 Verification:"
echo "Make a test call and check logs with:"
echo "  sudo kubectl logs -f $POD | grep -E '(content-type|ElevenLabs generated)'"
echo ""
echo "You should see: 'content-type': 'application/octet-stream' (NOT audio/mpeg)"

