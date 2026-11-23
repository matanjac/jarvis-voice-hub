"""Central configuration for jarvis-voice-hub. Everything is overridable with environment variables.

State lives under VOICE_HUB_HOME (default ~/.config/jarvis-voice-hub):

    models/      Kokoro model files (downloaded by setup.sh)
    bin/         small compiled C helpers (built by setup.sh)
    workspace/   scratch folder the Claude "brain" runs in (its working directory)
    state/       logs, session id, UI event file, lock files
"""
import os

HOME_DIR = os.path.expanduser(os.environ.get("VOICE_HUB_HOME", "~/.config/jarvis-voice-hub"))
MODELS_DIR = os.path.join(HOME_DIR, "models")
BIN_DIR = os.path.join(HOME_DIR, "bin")
STATE_DIR = os.path.join(HOME_DIR, "state")
WORKSPACE = os.path.expanduser(os.environ.get("VOICE_HUB_WORKSPACE",
                                              os.path.join(HOME_DIR, "workspace")))

LOG = os.path.join(STATE_DIR, "hub.log")
UI_EVENTS = os.path.join(STATE_DIR, "ui_events.jsonl")
UI_COMMANDS = os.path.join(STATE_DIR, "ui_commands.jsonl")   # HUD buttons -> hub
UI_ERR = os.path.join(STATE_DIR, "ui.err")
BRAIN_SESSION = os.path.join(STATE_DIR, "brain_session.txt")
HUB_PID = os.path.join(STATE_DIR, "hub.pid")
HUB_LOCK = os.path.join(STATE_DIR, "hub.lock")
UI_LOCK = os.path.join(STATE_DIR, "ui.lock")

KOKORO_MODEL = os.path.join(MODELS_DIR, "kokoro-v1.0.onnx")
KOKORO_VOICES = os.path.join(MODELS_DIR, "voices-v1.0.bin")
DEFAULTMIC = os.path.join(BIN_DIR, "defaultmic")
MICUSERS = os.path.join(BIN_DIR, "micusers")

# ---- identity -------------------------------------------------------------------------
# The name the assistant uses for itself (spoken greeting, HUD title, system prompt, and the
# "thank you <name>" goodbye). It is NOT the wake phrase; see WAKE_WORD_MODEL below.
ASSISTANT_NAME = os.environ.get("VOICE_HUB_NAME", "Jarvis")

# ---- wake word ------------------------------------------------------------------------
# An openWakeWord model name (downloaded by openWakeWord) or a path to your own .onnx file.
# The default is the pretrained "hey_jarvis" model that ships with openWakeWord. The pretrained
# models are CC BY-NC-SA 4.0 (non-commercial use only). Swap it for one of the other pretrained
# models ("alexa", "hey_mycroft", "hey_rhasspy") or train your own (needed for commercial use).
WAKE_WORD_MODEL = os.environ.get("VOICE_HUB_WAKE_MODEL", "hey_jarvis")
WAKE_THRESHOLD = float(os.environ.get("VOICE_HUB_WAKE_THRESHOLD", "0.5"))

# ---- speech models --------------------------------------------------------------------
WHISPER_MODEL = os.environ.get("VOICE_HUB_WHISPER", "mlx-community/whisper-large-v3-turbo")
KOKORO_VOICE = os.environ.get("KOKORO_VOICE", "af_heart")
KOKORO_SPEED = float(os.environ.get("KOKORO_SPEED", "1.15"))

# ---- brain (headless Claude Code) -----------------------------------------------------
BRAIN_MODEL = os.environ.get("VOICE_HUB_MODEL", "sonnet")
# SECURITY: anyone who can be heard by the microphone can steer the brain. The default is the
# restrictive "plan" mode (read-only analysis, no edits, no shell commands). Other choices:
# manual, dontAsk, acceptEdits, auto, bypassPermissions. Read README "Security" first.
PERMISSION_MODE = os.environ.get("VOICE_HUB_PERMISSION_MODE", "plan")
PERMISSIVE_MODES = {"auto", "bypassPermissions", "acceptEdits"}
# Brain isolation (on by default). The brain is started with --strict-mcp-config (none of your
# global MCP servers), --setting-sources project (your user-level settings, allow rules, hooks
# and CLAUDE.md are not loaded; only the scratch workspace's own .claude/ is), --disable-slash-
# commands, and --tools limited to the allowlist below. In "plan" mode shell, edit, write and
# web tools are also explicitly denied. Set VOICE_HUB_ISOLATE=0 to give the brain your normal
# Claude Code setup (not recommended). Override the allowlist with VOICE_HUB_TOOLS (comma list).
ISOLATE_BRAIN = os.environ.get("VOICE_HUB_ISOLATE", "1") != "0"
BRAIN_TOOLS = os.environ.get("VOICE_HUB_TOOLS", "Read,Grep,Glob")
PLAN_DENY_TOOLS = "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch"

# ---- conversation timing --------------------------------------------------------------
FOLLOWUP_WAIT = 7.0     # s of silence before the conversation ends
ONSET_WAIT = 8.0        # s to start talking after the wake word
END_SILENCE = 2.5       # s of quiet that ends an utterance
MAX_UTTERANCE = 60.0
MIN_LOGPROB = -1.0      # reject clips whose Whisper avg_logprob is below this (it is guessing)


def ensure_dirs():
    for d in (HOME_DIR, MODELS_DIR, BIN_DIR, STATE_DIR, WORKSPACE):
        os.makedirs(d, mode=0o700, exist_ok=True)
    os.chmod(STATE_DIR, 0o700)      # logs hold transcripts: owner only


def private_open(path, mode="a"):
    """open() that creates the file with 0600 (owner read/write only) and fixes older files."""
    flags = os.O_WRONLY | os.O_CREAT | (os.O_TRUNC if "w" in mode else os.O_APPEND)
    fd = os.open(path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
    except OSError:
        pass
    return os.fdopen(fd, "w" if "w" in mode else "a")
