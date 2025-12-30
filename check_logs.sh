#!/bin/bash

echo "🔍 Checking current pod..."
POD=$(sudo kubectl get pods -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}')
echo "Pod: $POD"
echo ""

echo "📋 Last 50 lines of logs:"
echo "=" 
sudo kubectl logs $POD --tail=50

echo ""
echo "🔍 Checking for Deepgram messages:"
sudo kubectl logs $POD | grep -E "(Deepgram|🎤|FINAL|interim)" | tail -20

