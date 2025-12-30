#!/bin/bash
# Force rebuild without Docker cache

set -e
echo "🔨 FORCE REBUILD (no cache)"

echo "[1/5] Building with --no-cache..."
sudo docker build --no-cache -t gym-call-agent:dev .

echo "[2/5] Saving to tar..."
sudo docker save gym-call-agent:dev -o /tmp/gym-agent-fresh.tar

echo "[3/5] Loading into k3s..."
for i in 1 2 3; do
    if sudo k3s ctr images import /tmp/gym-agent-fresh.tar; then
        echo "✓ Image loaded"
        break
    fi
    echo "Retry $i..."
    sleep 10
done

echo "[4/5] Deleting old pods..."
sudo kubectl delete pods -l app=gym-call-agent --force --grace-period=0 2>/dev/null || true
sleep 3

echo "[5/5] Restart deployment..."
sudo kubectl rollout restart deployment gym-call-agent
sudo kubectl rollout status deployment gym-call-agent --timeout=120s

echo ""
echo "✅ Done! Checking TTS initialization..."
sleep 5
POD=$(sudo kubectl get pods -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}')
sudo kubectl logs $POD | grep -E "TTS|ElevenLabs" | head -5

echo ""
echo "🚀 Test: python test_outbound_call.py +16305121365 \"Test\""

