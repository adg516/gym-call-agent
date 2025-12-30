#!/bin/bash
# Script to copy transcripts from pod to local machine

set -e

POD=$(sudo kubectl get pod -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD" ]; then
    echo "❌ No pod found for gym-call-agent"
    exit 1
fi

# Create local transcripts directory
mkdir -p ./transcripts

echo "📥 Copying transcripts from pod to ./transcripts/"
sudo kubectl cp $POD:/app/transcripts ./transcripts

echo "✅ Done! Transcripts copied to: ./transcripts/"
echo ""
ls -lh ./transcripts/

echo ""
echo "💡 To view a transcript:"
echo "   cat ./transcripts/transcript_*.txt"

