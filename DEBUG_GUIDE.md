# 🛠️ Quick Reference - Debug & Monitoring Scripts

## 📋 All Available Scripts

### 🚀 Core Scripts
| Script | Purpose | When to Use |
|--------|---------|-------------|
| `./deploy.sh` | Deploy code to k8s | After code changes |
| `./create_k8s_secret.sh` | Load secrets to k8s | After updating .env |
| `./test_outbound_call.py` | Make a test call | Test the system |

### 🔍 Debug Scripts
| Script | Purpose | What It Shows |
|--------|---------|---------------|
| `./check_logs.sh` | Quick log overview | Recent activity, calls, errors |
| `./debug_llm.sh` | LLM-specific debug | Phase 3 LLM processing |
| `./debug_deepgram.sh` | Deepgram-specific | Phase 2 transcription |
| `./health_check.sh` | System health | Pod status, secrets, errors |
| `./live_monitor.sh` | Live log tail | Real-time monitoring |

### 📄 Transcript Scripts
| Script | Purpose | What It Shows |
|--------|---------|---------------|
| `./view_transcripts.sh` | View latest transcript | Most recent call results |
| `./download_transcripts.sh` | Download all transcripts | Archive all calls |

---

## 🎯 Common Workflows

### 1️⃣ Deploy & Test
```bash
# Deploy updated code
./deploy.sh

# Make test call
python test_outbound_call.py +16305121365 "Test Phase 3"

# Check logs
./check_logs.sh
```

### 2️⃣ Debug Issues
```bash
# Check overall health
./health_check.sh

# Check specific issue:
./debug_llm.sh        # LLM not extracting info?
./debug_deepgram.sh   # Transcription issues?
./check_logs.sh       # General errors?
```

### 3️⃣ Monitor Live Call
```bash
# Open terminal 1: Make call
python test_outbound_call.py +16305121365 "Live test"

# Open terminal 2: Watch live
./live_monitor.sh
```

### 4️⃣ Review Results
```bash
# View latest transcript
./view_transcripts.sh

# Download all for analysis
./download_transcripts.sh
```

---

## 📖 Detailed Script Usage

### `./check_logs.sh`
**Quick log overview with smart filtering**

Shows:
- ✅ Recent logs (last 30 lines)
- ✅ Call activity (started/stopped)
- ✅ Transcriptions (what was said)
- ✅ LLM processing (what was extracted)
- ✅ Errors (if any)

```bash
./check_logs.sh
```

**Output Example:**
```
📋 RECENT LOGS (Last 30 lines):
----------------------------------------------------------------------
[Recent activity...]

📞 CALL ACTIVITY:
----------------------------------------------------------------------
Stream started - Call SID: CA123...
Stream stopped - MZ456...

🎤 TRANSCRIPTIONS (Last 10):
----------------------------------------------------------------------
🎤 FINAL [0.99]: We're open 6am to 10pm
🎤 FINAL [1.00]: Day passes are $25

🧠 LLM PROCESSING (Last 10):
----------------------------------------------------------------------
🧠 Processing with LLM: "We're open 6am to 10pm"
✅ Extracted: hours
📊 Info collection progress: 25%

❌ ERRORS (if any):
----------------------------------------------------------------------
✓ No errors found
```

---

### `./debug_llm.sh`
**Phase 3 LLM diagnostics**

Checks:
- ✅ OpenAI API key configured?
- ✅ LLM initialized?
- ✅ Processing transcriptions?
- ✅ Extracting information?
- ✅ Progress tracking?
- ✅ Any LLM errors?

```bash
./debug_llm.sh
```

**Output Example:**
```
🔑 Checking OpenAI Configuration:
----------------------------------------------------------------------
✓ OPENAI_API_KEY is set

🚀 LLM Initialization:
----------------------------------------------------------------------
✅ OpenAI client initialized (model: gpt-4o-mini)

🧠 LLM Processing Activity:
----------------------------------------------------------------------
🧠 Processing with LLM: "We're open from 6am to 10pm"
🧠 Processing with LLM: "Day passes are twenty-five dollars"

✅ Information Extracted:
----------------------------------------------------------------------
✅ Extracted: hours
✅ Extracted: day_pass_price

📊 Collection Progress:
----------------------------------------------------------------------
📊 Info collection progress: 25%
   Hours: ✓ 6am-10pm
   Price: ✗ (missing)
📊 Info collection progress: 50%
   Hours: ✓ 6am-10pm
   Price: ✓ $25

🏋️  Extracted Information (Last call):
----------------------------------------------------------------------
EXTRACTED GYM INFORMATION
Completion: 50%
Hours: 6am-10pm
Day Pass Price: $25
Classes: (not found)
```

---

### `./live_monitor.sh`
**Real-time log monitoring**

Follows logs and shows only important events:
- 📞 Calls starting/stopping
- 🎤 Transcriptions
- 🧠 LLM processing
- ✅ Extracted info
- ❌ Errors

```bash
./live_monitor.sh
```

**Press Ctrl+C to stop**

Great for watching calls in real-time!

---

### `./health_check.sh`
**Complete system health check**

Shows:
- ✅ Deployment status
- ✅ Pod status (running/ready/restarts)
- ✅ Secrets configured (Twilio/Deepgram/OpenAI)
- ✅ Recent errors
- ✅ Transcript count

```bash
./health_check.sh
```

**Output Example:**
```
📦 Deployment Status:
----------------------------------------------------------------------
NAME              READY   UP-TO-DATE   AVAILABLE   AGE
gym-call-agent    1/1     1            1           2h

📱 Pod Status:
----------------------------------------------------------------------
NAME                              READY   STATUS    RESTARTS   AGE
gym-call-agent-abc123-xyz         1/1     Running   0          2h

🔑 Secrets Status:
----------------------------------------------------------------------
✓ gym-call-agent-secrets exists
  ✓ TWILIO_ACCOUNT_SID
  ✓ DEEPGRAM_API_KEY
  ✓ OPENAI_API_KEY

⚠️  Recent Errors (if any):
----------------------------------------------------------------------
✓ No recent errors

📄 Transcript Files:
----------------------------------------------------------------------
Total transcripts: 5
```

---

### `./view_transcripts.sh`
**View call transcripts**

Shows:
- ✅ List of all transcript files
- ✅ Most recent transcript (full content)
- ✅ File locations

```bash
./view_transcripts.sh
```

**Output Example:**
```
📋 Fetching transcripts from pod: gym-call-agent-abc123

Available transcripts (3 found):

-rw-r--r--  1.2K  transcript_20251230_143045_CA123.txt
-rw-r--r--  1.5K  transcript_20251230_144512_CA456.txt
-rw-r--r--  2.1K  transcript_20251230_150023_CA789.txt

============================================================

📝 Most Recent Transcript:

GYM CALL TRANSCRIPT & AI ANALYSIS
======================================================================
Call SID: CA789...
Date/Time: 2025-12-30 15:00:23 UTC
Duration: 45.23 seconds
[... full transcript ...]
```

---

### `./download_transcripts.sh`
**Download all transcripts locally**

Downloads transcripts to your machine for offline analysis.

```bash
./download_transcripts.sh
```

Creates: `transcripts_YYYYMMDD_HHMMSS.tar.gz`

---

## 🆘 Troubleshooting Guide

### Problem: No logs showing
```bash
./health_check.sh
# Check if pod is running
# If not running, redeploy:
./deploy.sh
```

### Problem: LLM not working
```bash
./debug_llm.sh
# Check if OPENAI_API_KEY is set
# If not:
./create_k8s_secret.sh
./deploy.sh
```

### Problem: No transcriptions
```bash
./debug_deepgram.sh
# Check Deepgram connection
# Verify DEEPGRAM_API_KEY
```

### Problem: Errors in logs
```bash
./check_logs.sh
# See recent errors
# Check specific logs:
sudo kubectl logs deployment/gym-call-agent --tail=100
```

### Problem: Pod keeps restarting
```bash
./health_check.sh
# Check restart count
# View pod events:
sudo kubectl describe pod $(sudo kubectl get pod -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}')
```

---

## 💡 Pro Tips

### Combine scripts for debugging
```bash
# Terminal 1: Monitor live
./live_monitor.sh

# Terminal 2: Make test calls
python test_outbound_call.py +16305121365 "Test 1"
sleep 10
python test_outbound_call.py +16305121365 "Test 2"

# Terminal 3: Check health
watch -n 5 ./health_check.sh
```

### Search logs for specific info
```bash
# Find all calls
sudo kubectl logs deployment/gym-call-agent | grep "Stream started"

# Find specific call by SID
sudo kubectl logs deployment/gym-call-agent | grep "CA1234567890"

# Find extraction of hours
sudo kubectl logs deployment/gym-call-agent | grep "hours"
```

### Quick pod restart
```bash
sudo kubectl rollout restart deployment/gym-call-agent
# Wait 30 seconds for new pod
./health_check.sh
```

---

## 📊 Script Comparison

| Need | Script | Speed |
|------|--------|-------|
| Quick overview | `./check_logs.sh` | ⚡ Fast |
| Deep dive LLM | `./debug_llm.sh` | ⚡⚡ Medium |
| Live monitoring | `./live_monitor.sh` | 🔴 Continuous |
| Full health check | `./health_check.sh` | ⚡⚡ Medium |
| View results | `./view_transcripts.sh` | ⚡ Fast |

---

## 🎯 Quick Commands Summary

```bash
# Deploy & Test
./deploy.sh && python test_outbound_call.py +16305121365 "Test"

# Quick debug
./check_logs.sh

# Deep LLM debug  
./debug_llm.sh

# Watch live
./live_monitor.sh

# System health
./health_check.sh

# View results
./view_transcripts.sh

# Download all
./download_transcripts.sh
```

---

**All scripts are now ready! Debug with confidence! 🛠️✨**

