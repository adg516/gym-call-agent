#!/bin/bash
set -e

echo "🏗️  Building Docker image..."
sudo docker build -t gym-call-agent:dev .

echo "💾 Saving image to tar..."
sudo docker save gym-call-agent:dev -o /tmp/gym-call-agent-new.tar

echo "📦 Loading into k3s..."
sudo k3s ctr images import /tmp/gym-call-agent-new.tar

echo "🔄 Restarting deployment..."
sudo kubectl rollout restart deployment/gym-call-agent

echo "⏳ Waiting for rollout..."
sudo kubectl rollout status deployment/gym-call-agent

echo "✅ Deployment complete!"
echo ""
echo "📋 Checking logs..."
sudo kubectl logs deployment/gym-call-agent --tail=20

echo ""
echo "🎉 Done! Now test your call again."

