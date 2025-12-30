# Transcript Storage Guide

## What Was Added

Transcripts are now automatically saved to files after each call!

### Files Created:
1. **Updated `app/api/twilio.py`** - Saves transcripts to `/app/transcripts/` in the pod
2. **`view_transcripts.sh`** - View transcripts directly from the pod
3. **`download_transcripts.sh`** - Copy transcripts to your local machine

---

## Usage

### Option 1: View Transcripts in Pod

```bash
cd /home/adggda/gymgym
./view_transcripts.sh
```

This will show:
- List of all transcript files
- Contents of the most recent transcript

### Option 2: Download Transcripts Locally

```bash
cd /home/adggda/gymgym
./download_transcripts.sh
```

This will:
- Copy all transcripts to `./transcripts/` directory
- List all downloaded files

Then view them:
```bash
cat ./transcripts/transcript_*.txt
# Or open in editor
code ./transcripts/
```

---

## Transcript Format

Each transcript file is named:
```
transcript_YYYYMMDD_HHMMSS_CallSID.txt
```

Example content:
```
Call Transcript
============================================================
Call SID: CA1a827607894307d386ecc189d1c6fd97
Stream SID: MZ3890f1b17a81805767d18b4f942074eb
Timestamp: 20251230_070404
Duration: 9.18 seconds
Speech frames: 123 (26.8%)

Transcription:
------------------------------------------------------------
[1] ✓ [0.95] Hello?
[2] ... [0.82] Testing one two three
[3] ✓ [0.91] Can you hear me?
============================================================
```

Where:
- `✓` = Final transcription
- `...` = Interim/partial transcription
- `[0.95]` = Confidence score (0.0-1.0)

---

## Deploy Updated Code

To enable transcript saving:

```bash
cd /home/adggda/gymgym
./deploy.sh
```

After deployment, make a test call and the transcript will be automatically saved!

---

## Notes

- **Storage:** Transcripts are stored in the pod at `/app/transcripts/`
- **Persistence:** Currently ephemeral (lost on pod restart). See below for persistent storage.
- **Format:** Plain text files, easy to parse for analytics

---

## Making Transcripts Persistent (Optional)

If you want transcripts to survive pod restarts, you can mount a persistent volume. Let me know if you want this!

Current setup is fine for development/testing since you can always download them with `./download_transcripts.sh`.

---

## Quick Commands

```bash
# After making a call, view the transcript
./view_transcripts.sh

# Download all transcripts
./download_transcripts.sh

# View a specific transcript
cat ./transcripts/transcript_20251230_070404_CA*.txt

# Count total calls
ls -1 ./transcripts/*.txt | wc -l

# Search transcripts for a word
grep -r "drop-in" ./transcripts/
```

---

*Transcripts will be generated automatically after each call once you redeploy!*

