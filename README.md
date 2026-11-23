# jarvis-voice-hub

A hands-free, always-on voice layer for [Claude Code](https://claude.com/claude-code) on a Mac.
Say a wake word, talk, and a headless Claude Code session (the "brain") answers out loud. A small
floating panel (the HUD) shows what it heard and what it is doing.

An independent hobby project, not affiliated with, endorsed by, or sponsored by Marvel, Disney, or any company named Jarvis.

*"jarvis-voice-hub" is a working name. The assistant's own name is configurable (default `Jarvis`).*

## Install (the easy way): let Claude Code do it

Open Claude Code on your Mac and paste this:

```text
Install https://github.com/matanjac/jarvis-voice-hub on this Mac. Clone it over HTTPS (no GitHub account needed), then read INSTALL_FOR_AGENTS.md in the repo and follow it exactly. Ask me before installing anything. Never change the security settings. If anything fails, stop and tell me the exact error.
```

Claude explains each step and asks before it does it. It will install, only if missing and only
after you say yes: Apple's Command Line Tools (you click Install), Homebrew, and Python 3.12; then it
sets up this project in `~/jarvis-voice-hub` (about 2.5 GB). It will ask you to understand the
security notes below and to allow microphone access for your terminal. It never uses `sudo` and
never sees your Mac password (Homebrew asks you for it directly, only if Homebrew is missing).

Requirements: an Apple Silicon Mac (M1 or newer, macOS 14+) and [Claude Code](https://claude.com/claude-code)
installed and logged in. The instructions Claude follows are in [INSTALL_FOR_AGENTS.md](INSTALL_FOR_AGENTS.md); read them first if you like.

**Status:** not yet tested end to end on a clean Mac.

## Install with Claude Code

This is the longer, manual-friendly version of the easy install at the top (the short prompt plus
[INSTALL_FOR_AGENTS.md](INSTALL_FOR_AGENTS.md) is the recommended path; both end in the same `./setup.sh`). Read "Security: read this first" below before you run the hub: the microphone is
an open door to the agent.

**Status of these instructions:** the feature set was tested on the developer's Mac (macOS 27.0,
Apple Silicon). **The full install flow below has not yet been tested on a clean machine.** The
first run on a second Mac is that test; treat any surprise as a bug to report.

### 1. Prerequisites (you do these first)

- Apple Silicon Mac (M1 or newer). Developed on macOS 27.0; README minimum is macOS 14.2, which
  has not been tried.
- Xcode command line tools: `xcode-select --install` (needed for `clang`, `git`).
- [Homebrew](https://brew.sh), then `brew install python@3.12`.
- Python 3.12 available as `python3.12` (`python3.12 --version`).
- The Claude Code CLI installed and logged in: run `claude` once and complete the sign-in, then
  check `claude --version` works in a new terminal window.
- git. No GitHub account or login is needed while the repository is public (clone over HTTPS).
  Only for a private fork: `brew install gh`, `gh auth login`, `gh auth status` first.
- A microphone and speaker, about 2.5 GB free disk, and internet access (models download from
  GitHub and Hugging Face).
- You sitting at that Mac: the first run needs you to click a macOS permission dialog.

### 2. A longer prompt (alternative to the short one at the top)

```text
Install the project jarvis-voice-hub on this Mac. Clone https://github.com/matanjac/jarvis-voice-hub into ~/jarvis-voice-hub over HTTPS (no GitHub login is needed; if the clone fails with an authentication error, stop and tell me, and do not look for or use any credentials). Read INSTALL_FOR_AGENTS.md and README.md (especially "Security: read this first" and "Install with Claude Code") and docs/ARCHITECTURE.md before doing anything else. Then run ./setup.sh and afterwards `.venv/bin/python hub.py --check`. If any step fails, do not improvise or work around it: report the exact failing command, its error output and the fix from the README troubleshooting table (or say that none is documented), and wait for me. Do not use sudo or run any script that is not in the repo. Do not change the security defaults: leave the permission mode at `plan`, leave brain isolation on, and do not set VOICE_HUB_PERMISSION_MODE, VOICE_HUB_ISOLATE or VOICE_HUB_TOOLS. Do not start the hub (`hub.py` without --check) until I confirm that macOS microphone permission is granted to my terminal app. Before that, tell me exactly what to expect: macOS shows a dialog asking whether the terminal app may access the microphone, which I must answer Allow; it can be granted or fixed afterwards under System Settings > Privacy & Security > Microphone by switching my terminal app on (the terminal appears in that list only after its first microphone request, so on a fresh Mac it may be missing until the first start). When I say I am ready, start the hub in a foreground terminal with `.venv/bin/python hub.py` (not launchd, not in the background) so I can watch the log and stop it with Ctrl-C. Then tell me what to try: say "hey jarvis", wait for the Tink sound, then ask "what time is it" and then "what is in this folder". The floating panel should appear at the bottom right, show LISTENING, then THINKING with a seconds timer and an activity line, show CANCEL while it works, show my words with a "Heard clearly" tag, speak the reply aloud and show SPEAKING; after a few seconds of silence it should play a Bottle sound and hide. Finish by walking me through the post-install checklist in the README and reporting which items passed.
```

### 3. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `setup.sh`: `python3.12 not found` | Python 3.12 missing | `brew install python@3.12`, open a new terminal |
| `setup.sh`: `clang: command not found` or a dialog about developer tools | Xcode command line tools missing | `xcode-select --install`, wait, rerun `./setup.sh` |
| `git clone` asks for a password or says repository not found | The repository is not public yet, or it is a private fork | Check the URL; for a private fork only: `gh auth login`, `gh auth status`, clone again |
| `checksum mismatch` for a Kokoro file | Interrupted or changed download | Rerun `./setup.sh` (bad files are discarded); if it persists, upstream changed the file, report it, do not edit the checksum blindly |
| `--check` shows `[MISSING]` Kokoro files | `setup.sh` did not finish | Rerun `./setup.sh` |
| `--check`: `claude CLI` not on PATH | Claude Code not installed or not in this shell's PATH | Install Claude Code, open a new terminal, `claude --version` |
| Brain gives no answer, log shows the brain restarting | `claude` not logged in | Run `claude` interactively once and sign in |
| Log says `mic check ... SILENT: no mic permission?` | Terminal has no microphone permission | System Settings > Privacy & Security > Microphone: switch your terminal on, then quit and restart the terminal and the hub |
| No permission dialog ever appeared and the terminal is not in the list | The dialog is shown on first microphone use, and it may have been dismissed | Start the hub once with you present, click Allow; if you clicked Don't Allow, switch it on in the list (or `tccutil reset Microphone`, which resets the microphone choice for ALL apps, and start again) |
| Wake word never triggers | Wrong input device, too quiet, or threshold | Check the `listening on:` line in the log; speak clearly 1 m away; try `VOICE_HUB_WAKE_THRESHOLD=0.35` |
| Wake word triggers but the transcript is empty or "Ignored noise" | Whisper rejected the clip (low confidence) | Speak louder and closer; see `hub.log` for the `avg_logprob` |
| Long pause after the first wake | Whisper model (~1.6 GB) downloading from Hugging Face | Wait once; later wakes are fast |
| No sound or no spoken reply | Output device muted, or Kokoro failed | Check volume; read the end of `~/.config/jarvis-voice-hub/state/hub.log` |
| HUD never appears | `ui.py` failed to start | `cat ~/.config/jarvis-voice-hub/state/ui.err` |
| "another jarvis-voice-hub is already running" | A previous hub is still running | Quit it with Ctrl-C in its terminal, or `./restart.sh` |
| Replies say tools are unavailable or the brain refuses to edit files | Intended: default `plan` mode is read-only | Leave it. Changing it is a security decision, see "Security" |

### 4. Uninstall

Nothing is installed outside the repo folder and `~/.config/jarvis-voice-hub`, unless you ran
`./setup.sh --launchd` (which only writes a plist and does not load it). To remove everything:

1. Stop the hub (Ctrl-C in its terminal).
2. If you used launchd: `launchctl unload ~/Library/LaunchAgents/com.example.jarvis-voice-hub.plist` and delete that plist.
3. Delete `~/.config/jarvis-voice-hub` (models, compiled helpers, logs with transcripts, session id).
4. Delete the cloned repo folder (it contains the `.venv`).
5. Optional: remove the terminal's microphone permission in System Settings > Privacy & Security > Microphone.

The delete commands are deliberately not scripted here: check the paths, then remove them yourself
(Finder to the Trash, or `rm -r` on exactly those two folders).

### 5. After install: what to verify

- [ ] `hub.py --check` has no `[MISSING]` lines except the optional helpers, and prints permission mode `plan`.
- [ ] The log shows `mic check: level ... - ok`, not `SILENT`.
- [ ] You hear "Jarvis is online." at start, and the wake word gives a Tink and the panel shows LISTENING.
- [ ] After you speak, the panel shows your words with a tag ("Heard clearly" or "Unsure") and the log shows `heard (...)`.
- [ ] The reply is spoken aloud and shown, the panel shows an activity line and a THINKING timer while the brain works.
- [ ] Cancel: ask something slow ("summarise every file in this folder"), press CANCEL in the panel (and, separately, say "hey jarvis, never mind"): speech stops, the panel shows `CANCELLED · LISTENING` and RETRY, and a new question still works in the same conversation.
- [ ] Background reply: start a background Claude Code session from another terminal that finishes after a minute; the panel shows its name under "Working", and when it reports back a Ping plays and the result is spoken (or nothing is, if it replies `(silent)`).
- [ ] Say "goodbye": Bottle sound, panel hides.

Not tested on a clean machine: the whole of this section, the microphone-permission dialog flow,
`setup.sh` from a fresh checkout, the Cancel/background-reply checks with real audio on this
public repository (the cancel logic and HUD were exercised with synthetic events and a fake brain
process, not live audio).

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
- **Cancel:** the HUD's CANCEL button, or the wake word followed by "stop", "cancel", "never mind"
  or "hold on", stops the brain and any speech while it thinks or talks. The brain process is
  terminated but the session is kept; a RETRY button re-sends your last request.
- **HUD:** floating panel, see below. It shows a live activity line from the brain's tool events
  ("Reading a file"), a THINKING timer, a mic level bar, a "Heard clearly / Unsure / Ignored noise"
  tag per transcription, and the names of working background Claude Code sessions (polled from
  `claude agents --json`).

## Requirements

- Apple Silicon Mac (mlx-whisper needs it), macOS 14.2+ (the `micusers` helper uses CoreAudio
  process objects; without it the hub still works but never pauses for other mic users)
- Python 3.12 (`brew install python@3.12`), Xcode command line tools (`clang`)
- [Claude Code CLI](https://claude.com/claude-code) installed and signed in (`claude` on PATH)
- A microphone and speaker; allow Microphone access for your terminal on first run
- About 2.5 GB of disk (Kokoro ~350 MB, Whisper ~1.6 GB on first use, Python packages)

## Install

Easiest path: [let Claude Code do it](#install-the-easy-way-let-claude-code-do-it). By hand:

```sh
git clone https://github.com/matanjac/jarvis-voice-hub.git ~/jarvis-voice-hub && cd ~/jarvis-voice-hub
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
SPEAKING, WORKING), plus the live transcript of you and the assistant, a CANCEL button while it
thinks or speaks (status then reads `CANCELLED · LISTENING` with a RETRY button), a live activity
line, a mic level bar and the transcription tag. It hides a few seconds
after the conversation ends, stays up while background Claude Code jobs are running, and exits by
itself when the hub is gone.

Try it without a microphone or hub:

```sh
.venv/bin/python ui.py --events /tmp/events.jsonl &
echo '{"k":"wake"}' >> /tmp/events.jsonl
echo '{"k":"you","t":"list my sessions"}' >> /tmp/events.jsonl
echo '{"k":"assistant","t":"You have two sessions."}' >> /tmp/events.jsonl
echo '{"k":"activity","t":"Reading a file"}' >> /tmp/events.jsonl   # then watch THINKING tick
echo '{"k":"stopped"}' >> /tmp/events.jsonl                           # CANCELLED + Retry
echo '{"k":"end"}' >> /tmp/events.jsonl
```

The event and command formats are documented in `docs/ARCHITECTURE.md`.

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
  events, a fake brain process for the cancel logic); the live audio path, including Cancel and voice cancel, was not re-tested on this public copy.

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
