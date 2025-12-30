#!/bin/bash
# 🔥 Nuclear deploy script - handles all the k3s bullshit
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🔥 NUKE AND DEPLOY - Starting...${NC}"

cd /home/adggda/gymgym

# Step 1: Make sure k3s is running
echo -e "\n${YELLOW}[1/7] Checking k3s status...${NC}"
if ! sudo systemctl is-active --quiet k3s; then
    echo -e "${RED}k3s is down! Starting...${NC}"
    sudo systemctl start k3s
    echo "Waiting 30s for k3s to initialize..."
    sleep 30
else
    echo -e "${GREEN}✓ k3s is running${NC}"
fi

# Step 2: Wait for k3s API to be ready
echo -e "\n${YELLOW}[2/7] Waiting for k3s API...${NC}"
for i in {1..30}; do
    if sudo kubectl get nodes &>/dev/null; then
        echo -e "${GREEN}✓ k3s API is ready${NC}"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 2
done

# Show nodes
sudo kubectl get nodes

# Step 2.5: Cleanup to free disk space
echo -e "\n${YELLOW}[2.5/7] Cleaning up disk space...${NC}"

# Remove old tar files
echo "Removing old tar files..."
rm -f /tmp/gym-agent*.tar /tmp/*gym*.tar 2>/dev/null || true

# Prune Docker images and build cache
echo "Pruning Docker..."
docker system prune -f --volumes 2>/dev/null || true
docker image prune -a -f 2>/dev/null || true

# Prune old k3s/containerd images (keep only gym-call-agent:dev)
echo "Pruning old containerd images..."
sudo k3s ctr images ls -q 2>/dev/null | grep -v "gym-call-agent:dev" | grep -v "rancher\|traefik\|pause\|coredns\|metrics\|cert-manager" | head -10 | while read img; do
    sudo k3s ctr images rm "$img" 2>/dev/null || true
done

echo -e "${GREEN}✓ Cleanup complete${NC}"
df -h /tmp | tail -1

# Step 3: Build Docker image
echo -e "\n${YELLOW}[3/7] Building Docker image...${NC}"
docker build -t gym-call-agent:dev . 2>&1 | tail -20

# Step 4: Save image
echo -e "\n${YELLOW}[4/7] Saving image to tar...${NC}"
docker save gym-call-agent:dev -o /tmp/gym-agent-nuke.tar
echo -e "${GREEN}✓ Saved to /tmp/gym-agent-nuke.tar${NC}"

# Step 5: Load into k3s containerd (with retry)
echo -e "\n${YELLOW}[5/7] Loading into k3s containerd...${NC}"
for attempt in {1..3}; do
    echo "Attempt $attempt/3..."
    if sudo k3s ctr images import /tmp/gym-agent-nuke.tar 2>&1; then
        echo -e "${GREEN}✓ Image loaded successfully${NC}"
        break
    else
        echo -e "${RED}Failed, waiting 10s...${NC}"
        sleep 10
    fi
done

# Verify image is loaded
echo "Verifying image..."
sudo k3s ctr images list | grep gym-call-agent || echo "Warning: Image not found in list"

# Step 6: Nuclear cleanup - delete everything
echo -e "\n${YELLOW}[6/7] Nuclear cleanup...${NC}"
echo "Deleting deployment..."
sudo kubectl delete deployment gym-call-agent --ignore-not-found --grace-period=0 --force 2>/dev/null || true
echo "Deleting all pods..."
sudo kubectl delete pods -l app=gym-call-agent --force --grace-period=0 2>/dev/null || true
echo "Deleting any replicasets..."
sudo kubectl delete replicasets -l app=gym-call-agent --force --grace-period=0 2>/dev/null || true

echo "Waiting for cleanup..."
sleep 10

# Double check nothing is left
remaining=$(sudo kubectl get pods -l app=gym-call-agent --no-headers 2>/dev/null | wc -l)
if [ "$remaining" -gt 0 ]; then
    echo -e "${RED}Still $remaining pods remaining, force killing...${NC}"
    sudo kubectl delete pods -l app=gym-call-agent --force --grace-period=0 2>/dev/null || true
    sleep 5
fi

# Step 7: Fresh deploy
echo -e "\n${YELLOW}[7/7] Fresh deployment...${NC}"

# Apply manifests first
for attempt in {1..5}; do
    echo "Apply attempt $attempt/5..."
    if sudo kubectl apply -f k8s/deployment.yaml 2>&1 && \
       sudo kubectl apply -f k8s/service.yaml 2>&1 && \
       sudo kubectl apply -f k8s/ingress.yaml 2>&1; then
        echo -e "${GREEN}✓ All resources applied${NC}"
        break
    else
        echo -e "${RED}Failed (etcd issue?), waiting 5s...${NC}"
        sleep 5
    fi
done

# FORCE pod restart to use new image (even with same tag)
echo -e "\n${YELLOW}Forcing pod restart with new image...${NC}"
sudo kubectl rollout restart deployment gym-call-agent
echo "Waiting for rollout to complete..."
sudo kubectl rollout status deployment gym-call-agent --timeout=120s

# Check if cert-manager and letsencrypt are configured
echo -e "\n${YELLOW}Checking SSL certificates...${NC}"
if sudo kubectl get clusterissuer letsencrypt-prod &>/dev/null; then
    echo -e "${GREEN}✓ LetsEncrypt issuer configured${NC}"
else
    echo -e "${YELLOW}⚠ LetsEncrypt issuer not found - HTTPS may use self-signed cert${NC}"
    echo "  To fix: sudo kubectl apply -f k8s/letsencrypt-issuer.yaml"
fi

# Wait for pod to be ready
echo -e "\n${YELLOW}Waiting for pod to be ready...${NC}"
if sudo kubectl wait --for=condition=ready pod -l app=gym-call-agent --timeout=180s; then
    echo -e "${GREEN}✓ Pod is ready!${NC}"
else
    echo -e "${RED}Timeout waiting for pod${NC}"
fi

# Final status
echo -e "\n${GREEN}========== FINAL STATUS ==========${NC}"
sudo kubectl get pods -l app=gym-call-agent -o wide
echo ""
sudo kubectl get deployment gym-call-agent

# Show recent logs
echo -e "\n${YELLOW}Recent pod logs:${NC}"
POD=$(sudo kubectl get pods -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$POD" ]; then
    sudo kubectl logs "$POD" --tail=10 2>/dev/null || echo "No logs yet"
fi

echo -e "\n${GREEN}🚀 Done! Test with: python test_outbound_call.py +1XXXXXXXXXX \"Test\"${NC}"

