#!/bin/sh
# Restart the hub gracefully: it finishes any sentence it is speaking, then restarts itself
# (SIGUSR1). The floating panel is closed so the restarted hub relaunches it with fresh code.
# The hub records its pid in $VOICE_HUB_HOME/state/hub.pid; nothing else is touched.
STATE="${VOICE_HUB_HOME:-$HOME/.config/jarvis-voice-hub}/state"
PID=$(cat "$STATE/hub.pid" 2>/dev/null)
if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
  kill -USR1 "$PID" && echo "restart requested (pid $PID)"
else
  echo "hub not running"
fi
pkill -f "python.* ui\.py [0-9]" 2>/dev/null
true
