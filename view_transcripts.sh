#!/bin/bash
# Script to view call transcripts from the pod

set -e

POD=$(sudo kubectl get pod -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD" ]; then
    echo "❌ No pod found for gym-call-agent"
    exit 1
fi

echo "📋 Fetching transcripts from pod: $POD"
echo ""

# Check if any transcripts exist
TRANSCRIPT_COUNT=$(sudo kubectl exec $POD -- sh -c 'ls -1 /app/transcripts/*.txt 2>/dev/null | wc -l' || echo "0")

if [ "$TRANSCRIPT_COUNT" = "0" ]; then
    echo "No transcripts found yet."
    echo "Make a call first, then transcripts will be saved to /app/transcripts/"
    exit 0
fi

# List available transcripts
echo "Available transcripts ($TRANSCRIPT_COUNT found):"
echo ""
sudo kubectl exec $POD -- ls -lh /app/transcripts/

echo ""
echo "=" * 60
echo ""

# Show the most recent transcript
echo "📝 Most Recent Transcript:"
echo ""
LATEST=$(sudo kubectl exec $POD -- sh -c 'ls -t /app/transcripts/*.txt | head -1')
sudo kubectl exec $POD -- cat "$LATEST"

echo ""
echo ""
echo "💡 To copy all transcripts to your local machine:"
echo "   sudo kubectl cp $POD:/app/transcripts ./transcripts"

