#!/bin/bash
echo "=== Checking deployment status ==="
echo ""
echo "Pods:"
sudo kubectl get pods -l app=gym-call-agent
echo ""
echo "Services:"
sudo kubectl get svc | grep gym || echo "No gym-call-agent service found"
echo ""
echo "Ingress:"
sudo kubectl get ingress | grep gym || echo "No gym-call-agent ingress found"
echo ""
echo "Testing local pod connectivity:"
POD=$(sudo kubectl get pods -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$POD" ]; then
    echo "Pod: $POD"
    echo "Testing health endpoint..."
    sudo kubectl exec "$POD" -- curl -s http://localhost:8000/health 2>/dev/null || echo "Health check failed"
    echo ""
    echo "Recent logs:"
    sudo kubectl logs "$POD" --tail=20 2>/dev/null
fi
