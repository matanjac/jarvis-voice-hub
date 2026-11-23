#!/bin/sh
# jarvis-voice-hub setup: venv + Python deps, Kokoro model files, and the small C mic helpers.
#   ./setup.sh               full setup
#   ./setup.sh --no-venv     skip creating the venv / pip install (use your own environment)
#   ./setup.sh --launchd     only prints the service command: hub.py --install-service
# Override the install location with VOICE_HUB_HOME (default ~/.config/jarvis-voice-hub).
set -eu
DIR=$(cd "$(dirname "$0")" && pwd)
HOME_DIR="${VOICE_HUB_HOME:-$HOME/.config/jarvis-voice-hub}"
VENV="${VOICE_HUB_VENV:-$DIR/.venv}"
KOKORO_BASE="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
NO_VENV=0; LAUNCHD=0
for a in "$@"; do
  case "$a" in --no-venv) NO_VENV=1 ;; --launchd) LAUNCHD=1 ;; *) echo "unknown option $a" >&2; exit 2 ;; esac
done

[ "$(uname -s)" = "Darwin" ] || { echo "macOS only" >&2; exit 1; }
[ "$(uname -m)" = "arm64" ] || { echo "Apple Silicon (M1 or newer) required: transcription uses MLX, which does not run on Intel Macs. Found: $(uname -m)" >&2; exit 1; }
MACOS_MAJOR="$(sw_vers -productVersion | cut -d. -f1)"
[ "${MACOS_MAJOR:-0}" -ge 14 ] || echo "warning: macOS 14 or newer is expected (found $(sw_vers -productVersion)); continuing anyway" >&2
umask 077   # state files hold transcripts: owner only
mkdir -p "$HOME_DIR/models" "$HOME_DIR/bin" "$HOME_DIR/state" "$HOME_DIR/workspace"
chmod 700 "$HOME_DIR" "$HOME_DIR/state"

echo "== compiling mic helpers into $HOME_DIR/bin"
for t in defaultmic micusers; do
  clang -O2 -framework CoreAudio -framework CoreFoundation \
    -o "$HOME_DIR/bin/$t" "$DIR/native/$t.c"
done

echo "== Kokoro model files into $HOME_DIR/models (SHA-256 verified)"
# Source: $KOKORO_BASE (kokoro-onnx GitHub release "model-files-v1.0"). Upstream publishes no
# checksums; these were computed from the files downloaded from that release and their sizes
# match the release's Content-Length (kokoro-v1.0.onnx 325532387 bytes, voices-v1.0.bin
# 28214398 bytes). Confirm them against upstream before you trust this script.
sha_of() { shasum -a 256 "$1" | cut -d' ' -f1; }
want_sha() {
  case "$1" in
    kokoro-v1.0.onnx) echo 7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5 ;;
    voices-v1.0.bin)  echo bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d ;;
  esac
}
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  want=$(want_sha "$f")
  if [ -s "$HOME_DIR/models/$f" ] && [ "$(sha_of "$HOME_DIR/models/$f")" = "$want" ]; then
    echo "   $f present, checksum ok"
  else
    [ -s "$HOME_DIR/models/$f" ] && echo "   $f present but checksum differs; downloading again"
    curl -L --fail --proto '=https' --tlsv1.2 --progress-bar -o "$HOME_DIR/models/$f.part" "$KOKORO_BASE/$f"
    got=$(sha_of "$HOME_DIR/models/$f.part")
    if [ "$got" != "$want" ]; then
      rm -f "$HOME_DIR/models/$f.part"
      echo "checksum mismatch for $f (expected $want, got $got); file discarded" >&2
      exit 1
    fi
    mv "$HOME_DIR/models/$f.part" "$HOME_DIR/models/$f"
    echo "   $f downloaded, checksum ok"
  fi
done

PY=python3
if [ "$NO_VENV" = 0 ]; then
  echo "== Python venv at $VENV"
  command -v python3.12 >/dev/null 2>&1 || { echo "python3.12 not found (brew install python@3.12)" >&2; exit 1; }
  [ -d "$VENV" ] || python3.12 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install -r "$DIR/requirements.txt"   # versions pinned; see requirements.lock
  PY="$VENV/bin/python"
fi

echo "== downloading openWakeWord base models"
"$PY" -c "import openwakeword; openwakeword.utils.download_models()" || \
  echo "   (skipped; the wheel normally bundles them)"

if [ "$LAUNCHD" = 1 ]; then
  echo "== --launchd is now: $PY $DIR/hub.py --install-service (run it after --check passes; add --dry-run to preview)"
fi

echo "== downloading the Whisper speech model (a large one-time download, over 1 GB; can take several minutes)"
"$PY" - <<'PYEOF'
import os
from huggingface_hub import snapshot_download
repo = os.environ.get("VOICE_HUB_WHISPER", "mlx-community/whisper-large-v3-turbo")
print("   model repo:", repo)
print("   cached at:", snapshot_download(repo))
PYEOF

echo "== done. Next: $PY $DIR/hub.py --check"
