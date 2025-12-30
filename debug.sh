#!/bin/bash
# 🔍 HOLISTIC DEBUGGER - One script to debug everything
# Usage: ./debug.sh [mode]
#   ./debug.sh         - Full snapshot (transcripts + errors + status)
#   ./debug.sh live    - Live stream of conversation flow
#   ./debug.sh call    - Watch a specific call in real-time
#   ./debug.sh errors  - Just errors
#   ./debug.sh health  - Quick health check

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

MODE="${1:-full}"

# Get the running pod
get_pod() {
    sudo kubectl get pods -l app=gym-call-agent -o jsonpath='{.items[0].metadata.name}' 2>/dev/null
}

POD=$(get_pod)

header() {
    echo -e "\n${BOLD}${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════${NC}"
}

section() {
    echo -e "\n${YELLOW}▶ $1${NC}"
    echo -e "${YELLOW}───────────────────────────────────────────────────────────────${NC}"
}

# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════
health_check() {
    header "🏥 HEALTH CHECK"
    
    section "Kubernetes Status"
    echo -e "${BOLD}Nodes:${NC}"
    sudo kubectl get nodes --no-headers 2>/dev/null | while read line; do
        if echo "$line" | grep -q "Ready"; then
            echo -e "  ${GREEN}✓${NC} $line"
        else
            echo -e "  ${RED}✗${NC} $line"
        fi
    done
    
    echo -e "\n${BOLD}Pod Status:${NC}"
    POD_STATUS=$(sudo kubectl get pods -l app=gym-call-agent -o wide --no-headers 2>/dev/null)
    if [ -z "$POD_STATUS" ]; then
        echo -e "  ${RED}✗ No gym-call-agent pods found!${NC}"
        return 1
    fi
    
    echo "$POD_STATUS" | while read line; do
        if echo "$line" | grep -q "Running"; then
            echo -e "  ${GREEN}✓${NC} $line"
        else
            echo -e "  ${RED}✗${NC} $line"
        fi
    done
    
    section "API Keys Configured"
    if [ -n "$POD" ]; then
        LOGS=$(sudo kubectl logs "$POD" --tail=100 2>/dev/null)
        
        # Check Deepgram
        if echo "$LOGS" | grep -q "Deepgram.*initialized\|✅.*Deepgram"; then
            echo -e "  ${GREEN}✓${NC} Deepgram ASR"
        elif echo "$LOGS" | grep -q "DEEPGRAM.*not set"; then
            echo -e "  ${RED}✗${NC} Deepgram ASR - API key not set!"
        else
            echo -e "  ${YELLOW}?${NC} Deepgram ASR - unknown status"
        fi
        
        # Check OpenAI LLM
        if echo "$LOGS" | grep -q "OpenAI LLM.*initialized\|LLM client initialized"; then
            echo -e "  ${GREEN}✓${NC} OpenAI LLM"
        elif echo "$LOGS" | grep -q "OPENAI.*not set"; then
            echo -e "  ${RED}✗${NC} OpenAI LLM - API key not set!"
        else
            echo -e "  ${YELLOW}?${NC} OpenAI LLM - unknown status"
        fi
        
        # Check OpenAI TTS
        if echo "$LOGS" | grep -q "TTS client initialized\|OpenAI TTS"; then
            echo -e "  ${GREEN}✓${NC} OpenAI TTS"
        elif echo "$LOGS" | grep -q "TTS.*disabled\|TTS.*not set"; then
            echo -e "  ${RED}✗${NC} OpenAI TTS - not configured!"
        else
            echo -e "  ${YELLOW}?${NC} OpenAI TTS - unknown status"
        fi
    fi
    
    section "Recent Errors (last 50 lines)"
    if [ -n "$POD" ]; then
        ERRORS=$(sudo kubectl logs "$POD" --tail=50 2>/dev/null | grep -iE "error|exception|failed|❌" | tail -5)
        if [ -z "$ERRORS" ]; then
            echo -e "  ${GREEN}✓ No recent errors${NC}"
        else
            echo "$ERRORS" | while read line; do
                echo -e "  ${RED}$line${NC}"
            done
        fi
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# TRANSCRIPTS
# ═══════════════════════════════════════════════════════════════════════════════
show_transcripts() {
    header "📝 TRANSCRIPTS"
    
    if [ -z "$POD" ]; then
        echo -e "${RED}No pod running!${NC}"
        return 1
    fi
    
    section "Available Transcripts"
    TRANSCRIPTS=$(sudo kubectl exec "$POD" -- ls -lt /app/transcripts/ 2>/dev/null | head -10)
    if [ -z "$TRANSCRIPTS" ] || echo "$TRANSCRIPTS" | grep -q "No such file"; then
        echo -e "  ${YELLOW}No transcripts yet. Make a call first!${NC}"
        return
    fi
    echo "$TRANSCRIPTS"
    
    section "Latest Transcript"
    LATEST=$(sudo kubectl exec "$POD" -- ls -t /app/transcripts/ 2>/dev/null | head -1)
    if [ -n "$LATEST" ]; then
        sudo kubectl exec "$POD" -- cat "/app/transcripts/$LATEST" 2>/dev/null
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# ERRORS ONLY
# ═══════════════════════════════════════════════════════════════════════════════
show_errors() {
    header "❌ ERROR LOG"
    
    if [ -z "$POD" ]; then
        echo -e "${RED}No pod running!${NC}"
        return 1
    fi
    
    section "All Errors (last 200 lines)"
    ERRORS=$(sudo kubectl logs "$POD" --tail=200 2>/dev/null | grep -iE "error|exception|failed|traceback|❌" )
    if [ -z "$ERRORS" ]; then
        echo -e "${GREEN}✓ No errors found!${NC}"
    else
        echo "$ERRORS" | tail -30
        
        TOTAL=$(echo "$ERRORS" | wc -l)
        if [ "$TOTAL" -gt 30 ]; then
            echo -e "\n${YELLOW}... ($TOTAL total errors, showing last 30)${NC}"
        fi
    fi
    
    section "Python Tracebacks"
    sudo kubectl logs "$POD" --tail=500 2>/dev/null | grep -A5 "Traceback" | tail -20
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONVERSATION FLOW (for a single call)
# ═══════════════════════════════════════════════════════════════════════════════
show_call_flow() {
    header "📞 LAST CALL FLOW"
    
    if [ -z "$POD" ]; then
        echo -e "${RED}No pod running!${NC}"
        return 1
    fi
    
    # Get logs and find the last call
    LOGS=$(sudo kubectl logs "$POD" --tail=500 2>/dev/null)
    
    # Find the last call SID
    LAST_CALL=$(echo "$LOGS" | grep -oE "CA[a-f0-9]{32}" | tail -1)
    
    if [ -z "$LAST_CALL" ]; then
        echo -e "${YELLOW}No calls found in recent logs${NC}"
        return
    fi
    
    echo -e "${BOLD}Call SID:${NC} $LAST_CALL"
    
    section "1️⃣  Call Connection"
    echo "$LOGS" | grep -E "webhook called|WebSocket connected|stream.*started" | tail -5
    
    section "2️⃣  Speech Recognition (ASR)"
    echo "$LOGS" | grep -E "🎤.*FINAL|Transcription:" | tail -10 | while read line; do
        echo -e "${CYAN}$line${NC}"
    done
    
    section "3️⃣  LLM Processing"
    echo "$LOGS" | grep -E "🧠|Processing with LLM|Extracted info|generate_response" | tail -10 | while read line; do
        echo -e "${MAGENTA}$line${NC}"
    done
    
    section "4️⃣  AI Responses Generated"
    echo "$LOGS" | grep -E "💬|AI response:|Generated response" | tail -10 | while read line; do
        echo -e "${GREEN}$line${NC}"
    done
    
    section "5️⃣  Text-to-Speech (TTS)"
    echo "$LOGS" | grep -E "🔊|Generating speech|Generated.*bytes.*audio" | tail -10 | while read line; do
        echo -e "${BLUE}$line${NC}"
    done
    
    section "6️⃣  Audio Streaming to Twilio"
    AUDIO_SENT=$(echo "$LOGS" | grep -c "Sent.*bytes.*audio.*Twilio" || echo "0")
    AUDIO_BYTES=$(echo "$LOGS" | grep "Audio ready:" | tail -1)
    echo -e "  Chunks sent to Twilio: ${BOLD}$AUDIO_SENT${NC}"
    echo -e "  Last audio: $AUDIO_BYTES"
    
    section "7️⃣  Call End"
    echo "$LOGS" | grep -E "Call ended|disconnected|stop|Saving transcript" | tail -5
}

# ═══════════════════════════════════════════════════════════════════════════════
# LIVE MONITOR
# ═══════════════════════════════════════════════════════════════════════════════
live_monitor() {
    header "🔴 LIVE MONITOR (Ctrl+C to stop)"
    
    if [ -z "$POD" ]; then
        echo -e "${RED}No pod running!${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}Streaming conversation flow...${NC}\n"
    echo -e "Legend: ${CYAN}🎤 ASR${NC} | ${MAGENTA}🧠 LLM${NC} | ${GREEN}💬 Response${NC} | ${BLUE}🔊 TTS${NC} | ${RED}❌ Error${NC}\n"
    
    sudo kubectl logs -f "$POD" 2>/dev/null | while read line; do
        # Colorize based on content
        if echo "$line" | grep -qE "🎤|FINAL.*:"; then
            echo -e "${CYAN}$line${NC}"
        elif echo "$line" | grep -qE "🧠|LLM|Extracted"; then
            echo -e "${MAGENTA}$line${NC}"
        elif echo "$line" | grep -qE "💬|AI response|Generated response"; then
            echo -e "${GREEN}$line${NC}"
        elif echo "$line" | grep -qE "🔊|TTS|speech"; then
            echo -e "${BLUE}$line${NC}"
        elif echo "$line" | grep -qE "❌|error|Error|failed|Failed"; then
            echo -e "${RED}$line${NC}"
        elif echo "$line" | grep -qE "📞|Call|webhook|WebSocket"; then
            echo -e "${YELLOW}$line${NC}"
        elif echo "$line" | grep -qE "✅|success|complete"; then
            echo -e "${GREEN}$line${NC}"
        else
            # Skip noisy debug logs in live mode
            if ! echo "$line" | grep -qE "DEBUG.*Sent.*bytes"; then
                echo "$line"
            fi
        fi
    done
}

# ═══════════════════════════════════════════════════════════════════════════════
# FULL SNAPSHOT
# ═══════════════════════════════════════════════════════════════════════════════
full_snapshot() {
    echo -e "${BOLD}${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║           🔍 GYM CALL AGENT - HOLISTIC DEBUGGER               ║"
    echo "║                     $(date '+%Y-%m-%d %H:%M:%S')                        ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    health_check
    show_call_flow
    show_transcripts
    show_errors
    
    header "💡 QUICK COMMANDS"
    echo -e "  ${BOLD}./debug.sh live${NC}    - Watch calls in real-time"
    echo -e "  ${BOLD}./debug.sh errors${NC}  - Show only errors"
    echo -e "  ${BOLD}./debug.sh health${NC}  - Quick health check"
    echo -e "  ${BOLD}./nuke_and_deploy.sh${NC} - Redeploy from scratch"
    echo -e "  ${BOLD}python test_outbound_call.py +1XXX \"Gym\"${NC} - Make a test call"
}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
case "$MODE" in
    live|watch|stream)
        live_monitor
        ;;
    call|flow)
        show_call_flow
        ;;
    errors|error)
        show_errors
        ;;
    health|status)
        health_check
        ;;
    transcripts|transcript)
        show_transcripts
        ;;
    full|*)
        full_snapshot
        ;;
esac

