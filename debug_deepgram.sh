#!/bin/bash

echo "🔍 Checking for ALL Deepgram-related logs..."
POD=$(sudo kubectl get pods -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}')
echo "Pod: $POD"
echo ""

echo "📋 All Deepgram logs (last 100 lines):"
sudo kubectl logs $POD --tail=200 | grep -i "deepgram\|transcript\|🎤" || echo "No Deepgram transcript logs found"

echo ""
echo "📋 Looking for websocket messages from Deepgram:"
sudo kubectl logs $POD --tail=200 | grep -E "(< TEXT|> BINARY|Transcript|channel|alternatives)" || echo "No websocket messages found"

