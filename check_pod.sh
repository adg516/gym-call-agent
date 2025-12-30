#!/bin/bash
# Quick check for new deployment

POD=$(sudo kubectl get pod -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD" ]; then
    echo "❌ No pod found!"
    exit 1
fi

echo "📦 Current pod: $POD"
echo ""

# Extract replicaset ID
RS=$(echo $POD | cut -d'-' -f3)
echo "🔄 Replicaset: $RS"

if [ "$RS" = "7cdbf4db75" ]; then
    echo "❌ OLD CODE - Same replicaset! Need to deploy."
    echo ""
    echo "Run: ./nuke_and_deploy.sh"
else
    echo "✅ NEW CODE - Different replicaset!"
    echo ""
    echo "Testing content-type in logs..."
    sudo kubectl logs $POD --tail=500 | grep "content-type" | tail -1
    echo ""
    echo "Make a test call and monitor:"
    echo "  sudo kubectl logs -f $POD | grep content-type"
fi

