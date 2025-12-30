#!/bin/bash
# Script to create Kubernetes secret from .env file
set -e

echo "🔐 Creating Kubernetes secret from .env file..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please create a .env file with your credentials first"
    exit 1
fi

# Load environment variables from .env (using source for better compatibility)
set -a  # automatically export all variables
source .env
set +a

# Debug: Show if keys are loaded (first 10 chars only)
echo "Loaded keys:"
echo "  TWILIO_ACCOUNT_SID: ${TWILIO_ACCOUNT_SID:0:10}..."
echo "  DEEPGRAM_API_KEY: ${DEEPGRAM_API_KEY:0:10}..."
echo "  OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}..."
echo ""

# Create the secret (k3s requires sudo for kubectl)
sudo kubectl create secret generic gym-call-agent-secrets \
    --from-literal=TWILIO_ACCOUNT_SID="${TWILIO_ACCOUNT_SID:-}" \
    --from-literal=TWILIO_AUTH_TOKEN="${TWILIO_AUTH_TOKEN:-}" \
    --from-literal=TWILIO_FROM_NUMBER="${TWILIO_FROM_NUMBER:-}" \
    --from-literal=DEEPGRAM_API_KEY="${DEEPGRAM_API_KEY:-}" \
    --from-literal=OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
    --dry-run=client -o yaml | sudo kubectl apply -f -

echo "✅ Secret created/updated successfully!"
echo ""
echo "To verify:"
echo "  sudo kubectl get secret gym-call-agent-secrets"
echo ""
echo "To delete (if needed):"
echo "  sudo kubectl delete secret gym-call-agent-secrets"

