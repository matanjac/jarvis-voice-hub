#!/bin/sh
# Restart the hub gracefully: it finishes any sentence it is speaking, then restarts itself
# (SIGUSR1). Works the same whether the hub runs as the background service
# (hub.py --install-service) or in a terminal. The floating panel is closed so the restarted hub
# relaunches it with fresh code. The hub records its pid in $VOICE_HUB_HOME/state/hub.pid.
STATE="${VOICE_HUB_HOME:-$HOME/.config/jarvis-voice-hub}/state"
LABEL="com.jarvis-voice-hub"
PID=$(cat "$STATE/hub.pid" 2>/dev/null)
if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
  kill -USR1 "$PID" && echo "restart requested (pid $PID)"
elif [ -f "$HOME/Library/LaunchAgents/$LABEL.plist" ]; then
  # service installed but the hub is not running (for example after a crash, or booted out)
  if launchctl kickstart "gui/$(id -u)/$LABEL" 2>/dev/null; then
    echo "hub was not running; started the background service"
  else
    echo "hub not running; the service is installed but not loaded: run .venv/bin/python hub.py --install-service"
  fi
else
  echo "hub not running"
fi
pkill -f "python.* ui\.py [0-9]" 2>/dev/null
true
