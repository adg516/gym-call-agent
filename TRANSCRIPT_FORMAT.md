# 📄 Transcript Output Format

## Overview

After each call, the system automatically generates a comprehensive text file containing:
1. **Full conversation transcript** - Everything the gym staff said
2. **AI analysis** - What the LLM understood and extracted
3. **Structured information** - Organized gym details
4. **Call statistics** - Quality metrics

## File Location

Transcripts are saved to: `/app/transcripts/transcript_YYYYMMDD_HHMMSS_<call_sid>.txt`

To view from your local machine:
```bash
./view_transcripts.sh
# or
./download_transcripts.sh
```

## File Format

### Section 1: Header
```
GYM CALL TRANSCRIPT & AI ANALYSIS
======================================================================
Call SID: CA1234567890abcdef
Date/Time: 2025-12-30 14:30:45 UTC
Duration: 45.23 seconds
======================================================================
```

### Section 2: Full Conversation
```
FULL CONVERSATION
----------------------------------------------------------------------

[1] Gym Staff: Hello, thanks for calling Fitness Plus.
    (Confidence: 99%)

[2] Gym Staff: We're open from 6am to 10pm Monday through Friday.
    (Confidence: 98%)

[3] Gym Staff: Day passes are twenty-five dollars.
    (Confidence: 100%)
```

Each line includes:
- **Number**: Order in conversation
- **Speaker**: "Gym Staff" (AI responses in Phase 4)
- **Text**: What was said
- **Confidence**: Speech recognition accuracy (0-100%)

### Section 3: AI Analysis & Extracted Information

```
======================================================================
AI ANALYSIS & EXTRACTED INFORMATION
======================================================================

Information Completeness: 75%
Status: Missing drop_in_policy

OPERATING HOURS
----------------------------------------------------------------------
6am-10pm Mon-Fri, 8am-8pm weekends

DAY PASS PRICING
----------------------------------------------------------------------
$25

FITNESS CLASSES
----------------------------------------------------------------------
  • yoga
  • spin
  • pilates

DROP-IN POLICY
----------------------------------------------------------------------
Not mentioned during call
```

This section shows:
- **Completeness**: Percentage of info collected (0-100%)
- **Status**: Whether all core info was gathered
- **Hours**: Operating hours (if mentioned)
- **Pricing**: Day pass cost (if mentioned)
- **Classes**: List of available classes (if mentioned)
- **Policy**: Drop-in/walk-in policy (if mentioned)

### Section 4: Statistics
```
----------------------------------------------------------------------
Conversation Statistics:
  • Total exchanges: 7
  • Speech frames: 234 (52%)
  • Average confidence: 99%
```

## Example: Complete Successful Call

See [`SAMPLE_TRANSCRIPT.txt`](SAMPLE_TRANSCRIPT.txt) for a full example of what a successful call looks like.

## Example: Partial Information

If some information wasn't mentioned:

```
OPERATING HOURS
----------------------------------------------------------------------
Not mentioned during call

DAY PASS PRICING
----------------------------------------------------------------------
$25

FITNESS CLASSES
----------------------------------------------------------------------
  • yoga

DROP-IN POLICY
----------------------------------------------------------------------
Not mentioned during call
```

## Reading Transcripts

### View Most Recent
```bash
./view_transcripts.sh
```

### Download All Transcripts
```bash
./download_transcripts.sh
# Creates: transcripts_YYYYMMDD_HHMMSS.tar.gz
```

### View Specific Transcript
```bash
POD=$(sudo kubectl get pod -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}')
sudo kubectl exec $POD -- cat /app/transcripts/transcript_20251230_143045_CA123.txt
```

## What Gets Saved

✅ **Saved**:
- Final transcriptions (complete sentences)
- High confidence speech
- All extracted information
- Call metadata and stats

❌ **Not Saved**:
- Interim/partial transcriptions
- Background noise
- Silence periods
- Low confidence fragments

## File Size

Typical file size: **1-3 KB** per call

Example:
- 5-minute call
- 10 exchanges
- All info collected
- File size: ~2 KB

## Integration

These text files are:
- ✅ Human readable (open in any text editor)
- ✅ Machine parsable (structured format)
- ✅ Version controlled (can track changes)
- ✅ Searchable (grep for specific info)
- ✅ Archivable (compress and store long-term)

## Future Enhancements (Phase 5)

Planned improvements:
- Export to JSON format
- Export to CSV for spreadsheets
- Automatic email delivery
- Database storage
- Web dashboard view
- Search across all transcripts

## Troubleshooting

### No transcript file created
**Cause**: No final transcriptions received
**Check**: Look for "No final transcriptions to save" in logs

### Missing AI analysis section
**Cause**: LLM not configured or disabled
**Fix**: Ensure OPENAI_API_KEY is set in secrets

### Empty extracted information
**Cause**: Gym staff didn't mention the information
**Expected**: This is normal if they don't provide details

### Low confidence scores
**Cause**: Poor audio quality or background noise
**Improve**: 
- Speak clearly and loudly
- Reduce background noise
- Check phone connection quality

---

**Your transcript files now provide a complete, readable record of each call with intelligent AI analysis! 📄✨**

