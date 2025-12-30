#!/bin/bash
# Deep dive into what's happening
echo "=== Pod Logs (last 100 lines) ==="
sudo kubectl logs gym-call-agent-76d68d98cf-zr4xz --tail=100

echo ""
echo "=== Checking if app is running ==="
sudo kubectl exec gym-call-agent-76d68d98cf-zr4xz -- curl -s http://localhost:8000/health

echo ""
echo "=== Checking environment ==="
sudo kubectl exec gym-call-agent-76d68d98cf-zr4xz -- env | grep -E "DEEPGRAM|OPENAI|TWILIO|PUBLIC"

echo ""
echo "=== Recent call attempts ==="
sudo kubectl logs gym-call-agent-76d68d98cf-zr4xz --tail=200 | grep -i "call\|webhook\|websocket" | tail -20

