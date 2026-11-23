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
# SECURITY: anyone who can be heard by the microphone can steer the brain. How much power it
# has is chosen by ONE setting, the profile (read README "Security" first):
#   safe         (default) plan mode, isolation on, tools Read,Grep,Glob only, no shell/edit/web.
#   own-settings isolation off: the brain inherits YOUR Claude Code settings, MCP servers and
#                allow rules, but runs in the normal "default" permission mode, so in headless
#                mode anything your own settings do not pre-approve is denied.
#   full         permission mode "auto", all tools, isolation off: it can run commands, edit
#                files and start background helpers. Anyone who can be heard can do the same.
# The profile comes from VOICE_HUB_PROFILE, else from the one-word file PROFILE_FILE, else
# "safe". The explicit variables VOICE_HUB_PERMISSION_MODE, VOICE_HUB_ISOLATE and
# VOICE_HUB_TOOLS (comma list) still work and win over the profile.
PROFILES = {
    "safe":         {"mode": "plan",    "isolate": True,  "tools": "Read,Grep,Glob"},
    "own-settings": {"mode": "default", "isolate": False, "tools": "Read,Grep,Glob"},
    "full":         {"mode": "auto",    "isolate": False, "tools": "Read,Grep,Glob"},
}
PROFILE_FILE = os.path.join(HOME_DIR, "profile")


def _read_profile_file():
    try:
        with open(PROFILE_FILE) as f:
            return f.read().strip().lower()
    except OSError:
        return ""


def resolve_profile(env=None, file_value=None):
    """Return (name, note, source). Unknown values fall back to safe, with a note."""
    env = os.environ if env is None else env
    raw, source = env.get("VOICE_HUB_PROFILE", "").strip().lower(), "VOICE_HUB_PROFILE"
    if not raw:
        raw = _read_profile_file() if file_value is None else file_value
        source = PROFILE_FILE
    if not raw:
        return "safe", "", "default"
    if raw in PROFILES:
        return raw, "", source
    return "safe", f"unknown profile '{raw}' (from {source}); using safe", source


def write_profile(name):
    """Write ONLY the profile word to PROFILE_FILE, created/fixed to 0600."""
    if name not in PROFILES:
        raise ValueError(f"profile must be one of {', '.join(PROFILES)}")
    os.makedirs(HOME_DIR, mode=0o700, exist_ok=True)
    fd = os.open(PROFILE_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, (name + "\n").encode())
    finally:
        os.close(fd)


def effective_settings(profile, env=None):
    """Profile defaults with the explicit variables applied on top. Returns (mode, isolate, tools)."""
    env = os.environ if env is None else env
    p = PROFILES[profile]
    mode = env.get("VOICE_HUB_PERMISSION_MODE") or p["mode"]
    iso_env = env.get("VOICE_HUB_ISOLATE")
    isolate = p["isolate"] if iso_env is None else iso_env != "0"
    tools = env.get("VOICE_HUB_TOOLS") or p["tools"]
    return mode, isolate, tools


PROFILE, PROFILE_NOTE, PROFILE_SOURCE = resolve_profile()
PERMISSION_MODE, ISOLATE_BRAIN, BRAIN_TOOLS = effective_settings(PROFILE)
PERMISSIVE_MODES = {"auto", "bypassPermissions", "acceptEdits"}
# Isolation (safe profile): the brain is started with --strict-mcp-config (none of your global
# MCP servers), --setting-sources project (your user-level settings, allow rules, hooks and
# CLAUDE.md are not loaded; only the scratch workspace's own .claude/ is), --disable-slash-
# commands, and --tools limited to BRAIN_TOOLS. In "plan" mode shell, edit, write and web tools
# are also explicitly denied. With isolation off the brain gets your normal Claude Code setup
# and all tools (BRAIN_TOOLS is then not passed).
PLAN_DENY_TOOLS = "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch"


def profile_summary():
    """One plain-language line on what the agent can and cannot do (for --check and the log)."""
    mode, iso = PERMISSION_MODE, ISOLATE_BRAIN
    custom = (mode, iso, BRAIN_TOOLS) != effective_settings(PROFILE, {})
    if mode == "plan" and iso:
        s = (f"It can only read and search files in its empty scratch folder ({BRAIN_TOOLS}); it cannot "
             "run commands, edit or write files, use the web, or use your MCP servers or settings.")
    elif mode in PERMISSIVE_MODES:
        s = ("It can run commands, edit files, start background helpers and use your settings"
             + (" and MCP servers" if not iso else "") + " without asking.")
    elif not iso:
        s = ("It uses your own Claude Code settings and MCP servers, but anything your settings do not "
             "pre-approve is denied because nobody can click Allow in headless mode.")
    else:
        s = f"Permission mode '{mode}' with tools {BRAIN_TOOLS}; unapproved actions are denied."
    return s + (" (Customised by explicit VOICE_HUB_* variables.)" if custom else "")


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
