# jarvis-voice-hub

A hands-free, always-on voice layer for [Claude Code](https://claude.com/claude-code) on a Mac.
Say a wake word, talk, and a headless Claude Code session (the "brain") answers out loud. A small
floating panel (the HUD) shows what it heard and what it is doing.

An independent hobby project, not affiliated with, endorsed by, or sponsored by Marvel, Disney, or any company named Jarvis.

*"jarvis-voice-hub" is a working name. The assistant's own name is configurable (default `Jarvis`).*

## Security: read this first

**This program connects a microphone to an AI agent that can be given tools. Anyone or anything
that the microphone can hear can talk to that agent.**

- **There is no speaker verification (voice ID).** A guest, a child, a TV, a podcast, a video call
  or a voice from a phone speaker can issue commands exactly like you can. Saying the wake word
  is the only gate, and the wake word is public.
- **Prompt injection.** The brain reads files, web pages and messages from other sessions. Text in
  any of them can contain instructions aimed at the agent. Spoken replies are also an output
  channel: anything it reads may be read aloud.
- **Permissive modes turn both of those into remote code execution.** The original private
  version ran Claude Code in an auto-approve permission mode. **This public version defaults to
  `plan` (intended read-only; enforced by tool allowlist and denylist, see Brain isolation).** Change it only if you accept
  the risk: `VOICE_HUB_PERMISSION_MODE` = `plan` (default), `manual`, `dontAsk`, `acceptEdits`,
  `auto`, `bypassPermissions`. The hub logs a warning at startup, and `--check` prints one, when
  a permissive mode is configured. Note that in the non-interactive `claude -p` mode used here
  nobody can click "Allow", so restrictive modes mean tools that need approval will not run.
- **Run it in a scratch folder.** The brain's working directory defaults to
  `~/.config/jarvis-voice-hub/workspace`, an empty folder. Do not point `VOICE_HUB_WORKSPACE` at a
  repository, your home folder or a folder with secrets. Do not run it in a session that holds
  credentials, and do not leave it running on a machine in a room with other people.
- The transcript of everything it hears is logged locally to `~/.config/jarvis-voice-hub/state/hub.log`.
  Audio itself is not saved, but transcripts, and what the brain says, are.

Planned but **not implemented**: speaker verification, confirmation steps for risky actions.

## Privacy

What runs **locally on your Mac**: the wake word model (openWakeWord), voice-activity detection
(Silero VAD), Whisper speech-to-text (mlx-whisper), and Kokoro text-to-speech. Microphone audio
is processed in memory by these and is never written to disk or uploaded.

What leaves your machine: **the transcript of what you say, and anything the Claude agent reads
(files, tool output), is sent to Anthropic through the Claude CLI**, under your own account and
Anthropic's terms. Model files are downloaded once from GitHub and Hugging Face.

On disk: `~/.config/jarvis-voice-hub/state/` (created `0700`; log files `0600`) holds `hub.log`,
which contains transcripts of what you said and what the assistant replied, plus the session id.
Delete it whenever you like.

## Behaviors you might not expect

- **Replies from background sessions can be spoken unprompted.** Results that arrive while you
  are not talking (for example a background Claude Code session finishing) are read aloud after a
  short ping, at any time, even if others are in the room.
- **It reacts to any voice or TV audio in the room.** There is no speaker verification; anything
  that says the wake word, and what follows, is treated as you.
- The brain process stays running after a conversation ends, and resumes its session on restart.
- Whisper can mishear; transcripts are guesses.

## Brain isolation

The brain (`claude -p`) is started with `--strict-mcp-config` (none of your global MCP servers),
`--setting-sources project` (your user-level settings, allow rules and hooks are not loaded),
`--disable-slash-commands`, and `--tools Read,Grep,Glob` (override with `VOICE_HUB_TOOLS`). In the
default `plan` mode, `Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch` are also explicitly
denied. Set `VOICE_HUB_ISOLATE=0` to switch this off, in which case the brain inherits your normal
Claude Code setup (not recommended). These flags exist in Claude Code 2.1.330. The file tools are
still not confined to the workspace folder, so keep sensitive files out of reach of the account.

## What it does (and only this)

- **Always-on wake word** with [openWakeWord](https://github.com/dscripka/openWakeWord); only that
  tiny model runs in standby. The default model is `hey_jarvis` (see the licence notes: it is a
  swappable setting).
- **Speech-to-text** with [mlx-whisper](https://github.com/ml-explore/mlx-examples) (default
  `whisper-large-v3-turbo`), loaded when you wake it and unloaded when the conversation ends.
  While the models load, mic audio is buffered, so you can start talking right away.
- **Voice-activity detection** with the Silero VAD bundled in openWakeWord decides when you start
  and stop talking. Recording also ends when the voice score drops and the level falls well under
  your own speaking level, so a quieter TV does not hold the recording open.
- **Whisper confidence check:** per-clip `no_speech_prob`, `avg_logprob` and `compression_ratio`
  are logged; clips with `avg_logprob < -1.0` are rejected as probable noise guesses, and repeated
  phrases and common "thank you."-style hallucinations are filtered out.
- **A persistent headless Claude Code session** (`claude -p`, stream-json) is the brain. Its
  session id is saved and resumed on restart. Say "new conversation" to reset it.
- **Spoken replies** with [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) (ONNX, local).
  Markdown, code, links and long answers are stripped or shortened for speech.
- **Late replies:** if a result arrives while you are not talking (for example a background
  session reports back), it is spoken after a short Ping. The brain is told to reply `(silent)`
  when there is nothing new.
- **Follow-up window:** after a reply you can keep talking for 7 s without the wake word.
  "Goodbye", "that's all", "stop" or silence end the conversation. Beeps: Tink = woke,
  Pop = recording stopped, Bottle = conversation ended.
- **Microphone handling:** follows the Mac's default input (reopens when headphones connect),
  reconnects if a Bluetooth mic goes silent, and releases the mic while another app (a call,
  dictation) is using it (via the `micusers` helper).
- **Graceful restart:** `./restart.sh` sends SIGUSR1; the hub finishes the sentence it is
  speaking, then re-executes itself.
- **HUD:** floating panel, see below. It also shows how many background Claude Code sessions are
  working (polled from `claude agents --json`).

## Requirements

- Apple Silicon Mac (mlx-whisper needs it), macOS 14.2+ (the `micusers` helper uses CoreAudio
  process objects; without it the hub still works but never pauses for other mic users)
- Python 3.12 (`brew install python@3.12`), Xcode command line tools (`clang`)
- [Claude Code CLI](https://claude.com/claude-code) installed and signed in (`claude` on PATH)
- A microphone and speaker; allow Microphone access for your terminal on first run
- About 2.5 GB of disk (Kokoro ~350 MB, Whisper ~1.6 GB on first use, Python packages)

## Install

```sh
git clone <repo-url> jarvis-voice-hub && cd jarvis-voice-hub
./setup.sh                      # venv in ./.venv, deps, Kokoro files, compiled mic helpers
.venv/bin/python hub.py --check # verifies config, models, helpers, claude CLI; no mic needed
```

`setup.sh` puts everything it downloads or compiles under `~/.config/jarvis-voice-hub`
(override with `VOICE_HUB_HOME`). Whisper downloads from Hugging Face the first time you wake the
assistant.

## Run

```sh
.venv/bin/python hub.py
```

Say the wake word, wait for the Tink, and talk. To start at login, `./setup.sh --launchd` writes
`~/Library/LaunchAgents/com.example.jarvis-voice-hub.plist` from `launchd/com.example.jarvis-voice-hub.plist.template`
(it does not load it; rename the label if you like, then `launchctl load` it).

### Configuration (environment variables; see `config.py`)

| Variable | Default | Meaning |
|---|---|---|
| `VOICE_HUB_NAME` | `Jarvis` | name used in the greeting, HUD and system prompt |
| `VOICE_HUB_WAKE_MODEL` | `hey_jarvis` | openWakeWord model name or path to a `.onnx` file |
| `VOICE_HUB_WAKE_THRESHOLD` | `0.5` | wake sensitivity |
| `VOICE_HUB_PERMISSION_MODE` | `plan` | Claude Code permission mode for the brain (see Security) |
| `VOICE_HUB_WORKSPACE` | `~/.config/jarvis-voice-hub/workspace` | brain working directory |
| `VOICE_HUB_MODEL` | `sonnet` | Claude model alias |
| `VOICE_HUB_WHISPER` | `mlx-community/whisper-large-v3-turbo` | Whisper repo |
| `KOKORO_VOICE`, `KOKORO_SPEED` | `af_heart`, `1.15` | TTS voice and speed |
| `VOICE_HUB_HOME` | `~/.config/jarvis-voice-hub` | models, helpers, logs, state |

The wake model name is only the *phrase you say*. The assistant name is separate: you can run
`VOICE_HUB_NAME=Computer` with any wake model.

## The HUD

`ui.py` is a borderless, translucent, non-activating panel (PyObjC) that floats above all Spaces
and never takes focus. The hub launches it and feeds it through an append-only event file
(`state/ui_events.jsonl`, lines like `{"k": "you", "t": "..."}`). It stays hidden until the wake
word, then shows an orb whose animation follows the state (STANDBY, LISTENING, THINKING,
SPEAKING, WORKING), plus the live transcript of you and the assistant. It hides a few seconds
after the conversation ends, stays up while background Claude Code jobs are running, and exits by
itself when the hub is gone.

Try it without a microphone or hub:

```sh
.venv/bin/python ui.py --events /tmp/events.jsonl &
echo '{"k":"wake"}' >> /tmp/events.jsonl
echo '{"k":"you","t":"list my sessions"}' >> /tmp/events.jsonl
echo '{"k":"assistant","t":"You have two sessions."}' >> /tmp/events.jsonl
echo '{"k":"end"}' >> /tmp/events.jsonl
```

## Known limitations

- **No voice ID.** See Security. Anyone who can be heard can talk to it.
- **macOS on Apple Silicon only.** No Linux or Windows port.
- **Single microphone,** the system default; no far-field array, no echo cancellation. It drains
  the mic buffer after speaking so it does not hear itself, but loud speakers near the mic are not
  handled well.
- **Noise handling is basic:** Silero VAD, a Whisper-confidence filter and a level-relative
  end-of-speech rule. A noisy room will still cause missed or garbled clips.
- English only (Whisper is called with `language="en"`, Kokoro with `en-us`).
- The wake word model is a generic pretrained one, with the false accepts and misses that implies.
- `hub.py` was developed against one machine and one Claude Code version; expect rough edges.
  It was verified here without a microphone (compile, `--check`, setup, HUD with synthetic
  events); the live audio path was not re-tested after the cleanup for publishing.

## Licences and attribution

jarvis-voice-hub itself is MIT (see `LICENSE`). Third-party pieces keep their own terms:

| Component | Licence | Notes |
|---|---|---|
| [openWakeWord](https://github.com/dscripka/openWakeWord) (code) | Apache-2.0 | |
| **openWakeWord pretrained wake-word models** (`hey_jarvis`, `alexa`, `hey_mycroft`, `hey_rhasspy`, ...) | **CC BY-NC-SA 4.0** | **Non-commercial, share-alike, attribution.** Per the openWakeWord README this is because of training data with unknown or restrictive licences. If you use or ship this commercially, train your own wake word (openWakeWord supports this) and set `VOICE_HUB_WAKE_MODEL`. `hey_jarvis` is only the name of that model file. |
| Silero VAD (bundled in openWakeWord) | MIT, (c) Silero Team | licence text is in openWakeWord's `vad.py` |
| openWakeWord feature models (melspectrogram, embedding) | embedding model derived from a Google TFHub module, Apache-2.0 per openWakeWord | |
| [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) | MIT | |
| Kokoro-82M model | Apache-2.0 | voices file licence not verified, see `THIRD_PARTY.md`; attribution: hexgrad/Kokoro-82M |
| [mlx-whisper](https://github.com/ml-explore/mlx-examples) | MIT | |
| Whisper weights (`mlx-community/whisper-large-v3-turbo`, converted from OpenAI Whisper) | MIT (OpenAI Whisper); the mlx-community model card has no explicit licence field | |
| [PyObjC](https://github.com/ronaldoussoren/pyobjc) | MIT | |
| [sounddevice](https://github.com/spatialaudio/python-sounddevice) / PortAudio | MIT | |
| Claude Code CLI | Anthropic's commercial terms, not redistributed here | you need your own account |

Licence statuses above were read from the installed package metadata and upstream READMEs on the
date of preparation (2026-11-20); check upstream before relying on them, especially for the
voice files and the Whisper conversion. Python dependencies pulled in transitively (numpy,
onnxruntime, torch, scipy, ...) were not individually audited.

See `THIRD_PARTY.md` for per-component licences and what is not verified (e.g. the Kokoro voices file).
Claude is a trademark of Anthropic. Not affiliated with or endorsed by Anthropic or any wake-word, TTS or ASR project listed here.
