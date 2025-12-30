#!/bin/bash
# Quick fix - apply service and ingress
echo "🔧 Applying missing service and ingress..."
sudo kubectl apply -f k8s/service.yaml
sudo kubectl apply -f k8s/ingress.yaml

echo ""
echo "Checking status..."
sudo kubectl get svc | grep gym
sudo kubectl get ingress | grep gym

echo ""
echo "✅ Done! Try making a call now."

