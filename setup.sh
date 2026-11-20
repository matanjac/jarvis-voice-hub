#!/bin/sh
# voice-hub setup: venv + Python deps, Kokoro model files, and the small C mic helpers.
#   ./setup.sh               full setup
#   ./setup.sh --no-venv     skip creating the venv / pip install (use your own environment)
#   ./setup.sh --launchd     also write ~/Library/LaunchAgents/com.example.voice-hub.plist (not loaded)
# Override the install location with VOICE_HUB_HOME (default ~/.config/voice-hub).
set -eu
DIR=$(cd "$(dirname "$0")" && pwd)
HOME_DIR="${VOICE_HUB_HOME:-$HOME/.config/voice-hub}"
VENV="${VOICE_HUB_VENV:-$DIR/.venv}"
KOKORO_BASE="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
NO_VENV=0; LAUNCHD=0
for a in "$@"; do
  case "$a" in --no-venv) NO_VENV=1 ;; --launchd) LAUNCHD=1 ;; *) echo "unknown option $a" >&2; exit 2 ;; esac
done

[ "$(uname -s)" = "Darwin" ] || { echo "macOS only" >&2; exit 1; }
mkdir -p "$HOME_DIR/models" "$HOME_DIR/bin" "$HOME_DIR/state" "$HOME_DIR/workspace"

echo "== compiling mic helpers into $HOME_DIR/bin"
for t in defaultmic micusers; do
  clang -O2 -framework CoreAudio -framework CoreFoundation \
    -o "$HOME_DIR/bin/$t" "$DIR/native/$t.c"
done

echo "== Kokoro model files into $HOME_DIR/models"
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  if [ -s "$HOME_DIR/models/$f" ]; then echo "   $f already present"; else
    curl -L --fail --progress-bar -o "$HOME_DIR/models/$f.part" "$KOKORO_BASE/$f"
    mv "$HOME_DIR/models/$f.part" "$HOME_DIR/models/$f"
  fi
done

PY=python3
if [ "$NO_VENV" = 0 ]; then
  echo "== Python venv at $VENV"
  command -v python3.12 >/dev/null 2>&1 || { echo "python3.12 not found (brew install python@3.12)" >&2; exit 1; }
  [ -d "$VENV" ] || python3.12 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install -r "$DIR/requirements.txt"
  PY="$VENV/bin/python"
fi

echo "== downloading openWakeWord base models"
"$PY" -c "import openwakeword; openwakeword.utils.download_models()" || \
  echo "   (skipped; the wheel normally bundles them)"

if [ "$LAUNCHD" = 1 ]; then
  CLAUDE=$(command -v claude || true); [ -n "$CLAUDE" ] || { echo "claude CLI not on PATH" >&2; exit 1; }
  OUT="$HOME/Library/LaunchAgents/com.example.voice-hub.plist"
  sed -e "s|__PYTHON__|$PY|g" -e "s|__REPO_DIR__|$DIR|g" -e "s|__HOME__|$HOME|g" \
      -e "s|__CLAUDE_BIN_DIR__|$(dirname "$CLAUDE")|g" "$DIR/launchd/com.example.voice-hub.plist.template" > "$OUT"
  echo "wrote $OUT (load with: launchctl load $OUT)"
fi

echo "== done. Next: $PY $DIR/hub.py --check"
