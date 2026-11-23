# Install instructions for an AI coding agent

You are an AI coding agent (for example Claude Code) and a person has asked you to install
jarvis-voice-hub on their Mac. The person is probably not technical and may have no GitHub account.
Follow this file in order. Explain each step in plain words before you do it, and wait for a clear
yes before every non-trivial step (installing a tool, running `./setup.sh`, starting the hub).

## Rules (never break these)

- Do not use `sudo`. Never ask for, see, read or type the user's Mac password.
- Do not run anything that is not in this repository, with one exception: the official Homebrew
  installer from https://brew.sh, and only if Homebrew is missing and the user agrees.
- Do not change the security defaults: leave the permission mode at `plan` and brain isolation on.
  Do not set `VOICE_HUB_PERMISSION_MODE`, `VOICE_HUB_ISOLATE` or `VOICE_HUB_TOOLS`.
- Do not start the hub (`hub.py` without `--check`) before the user confirms that macOS microphone
  permission is ready for their terminal app (step 7).
- Do not improvise. If any command fails, stop, show the exact command and its exact error, give the
  matching fix from the "Troubleshooting" table in README.md (or say none is documented), and wait.
- Do not use `rm -rf`. Do not start the hub in the background or through launchd.
- Do not log in to GitHub. The repository is public and is cloned over HTTPS.

## Step 1. Check the Mac

Run `uname -m` and `sw_vers -productVersion`.

- `uname -m` must print `arm64` (Apple Silicon: M1 or newer). If it prints `x86_64`, stop: explain
  that the speech recognition (MLX) does not run on Intel Macs, so this project cannot work here.
- The macOS version must be 14 or newer (the first number is 14 or more). If older, stop and
  explain that they need to update macOS first.

## Step 2. Check Claude Code is logged in

Run `claude --version`. Then ask the user whether they have signed in to Claude Code on this Mac.
If `claude` is missing or they are not signed in, do nothing else: tell them to open a new
Terminal window, run `claude` once, and complete the sign-in in the browser, then start again.
(The hub's "brain" is a Claude Code session under their own account.)

## Step 3. Check and, if needed, install the tools

Check each tool. For each one that is missing, say what it is and why it is needed, ask for
confirmation, and only then install it.

1. **git**: `git --version`. If missing (macOS may pop up a dialog by itself), ask permission to run
   `xcode-select --install`. This opens a macOS dialog; the user must click **Install** and wait
   (several minutes). The Command Line Tools also provide `clang`, which `setup.sh` needs. Afterwards
   re-check `git --version` and `clang --version`.
2. **Homebrew**: `command -v brew` (also check `/opt/homebrew/bin/brew`). If missing, explain that
   Homebrew is the standard Mac package manager, and that its installer will ask for the user's Mac
   password in the terminal: they must type it themselves; you never see or type it. After
   confirmation, run only the official command from https://brew.sh (open that page, or fetch it,
   to copy the current command exactly; do not use any other source). Then follow the "Next steps"
   the installer prints so that `brew` is on the PATH, and verify with `brew --version`.
3. **Python 3.12**: `python3.12 --version`. If missing, after confirmation run
   `brew install python@3.12`, then verify `python3.12 --version`.

## Step 4. Clone the repository over HTTPS

If `~/jarvis-voice-hub` already exists, tell the user and ask whether to reuse it (then run
`git -C ~/jarvis-voice-hub pull --ff-only`); do not delete anything. Otherwise:

```sh
git clone https://github.com/matanjac/jarvis-voice-hub.git ~/jarvis-voice-hub
cd ~/jarvis-voice-hub
```

No GitHub account or login is needed. If the clone asks for a username or password or says the
repository was not found, stop and tell the user (the repository may not be public yet).

## Step 5. Explain the security model

Read the section "Security: read this first" in `~/jarvis-voice-hub/README.md`, then tell the user
in plain words, in your own short summary:

- The microphone is an open door to an AI agent. Anyone or anything it can hear (a guest, a child,
  a TV, a video call) can give it commands. There is no voice ID; the wake word is public.
- Text the agent reads (files, web pages) can try to give it instructions (prompt injection).
- Therefore it runs in `plan` mode (read-only tools) with brain isolation on, in an empty scratch
  folder, and you will not change that.
- Transcripts of what it hears are saved on this Mac in `~/.config/jarvis-voice-hub/state/hub.log`.

Ask whether they understand and want to continue.

## Step 6. Run setup and the check

Tell the user what `./setup.sh` does: creates a Python environment in the repo folder, installs
pinned packages, downloads the Kokoro speech model (about 350 MB, checksum verified), compiles two
small microphone helpers from `native/*.c`, and writes only inside the repo folder and
`~/.config/jarvis-voice-hub`. About 2.5 GB in total, a few minutes. After confirmation:

```sh
cd ~/jarvis-voice-hub
./setup.sh
.venv/bin/python hub.py --check
```

Report the result of each command in plain language. In the `--check` output, everything should be
OK (optional helpers may be flagged), the permission mode must read `plan`, and the `claude` CLI
must be found. If something fails, apply the rule "do not improvise".

## Step 7. Microphone permission, then start

Do not start the hub yet. Explain: when the hub first uses the microphone, macOS shows a dialog
asking whether the terminal app (Terminal, iTerm, or the app they are running Claude Code in) may
access the microphone. They must click **Allow**. It can be fixed later under System Settings >
Privacy & Security > Microphone by switching their terminal app on. The terminal only appears in
that list after its first microphone request, so on a fresh Mac it may be missing until the first
start. Ask: "Are you ready, and will you click Allow when the dialog appears?" Wait for yes.

Then start the hub in a foreground terminal so they can watch the log and stop it with Ctrl-C:

```sh
cd ~/jarvis-voice-hub
.venv/bin/python hub.py
```

(If you cannot keep a foreground process running, give the user these two lines to run in their own
Terminal window instead.) Do not use launchd or the background.

## Step 8. First-run test

Tell the user to try this, one thing at a time:

1. Say "hey jarvis" and wait for the Tink sound.
2. Ask "what time is it", then "what is in this folder".

Expected: a floating panel appears at the bottom right and shows LISTENING, then THINKING with a
seconds timer and an activity line (for example "Reading a file"), a CANCEL button while it works,
their words with a "Heard clearly" tag, then SPEAKING while the reply is spoken aloud. After a few
seconds of silence it plays a Bottle sound and hides. To test Cancel: ask something slow (for
example "summarise every file in this folder") and press CANCEL in the panel; the panel shows
CANCELLED and RETRY, and the next question still works. Saying "goodbye" ends the conversation.
If the log shows `mic check ... SILENT`, microphone permission is missing: use the table in README.md.

## Step 9. Post-install checklist

Walk through the checklist in README.md under "After install: what to verify" and report which
items passed and which were not tried. Also tell the user how to stop it (Ctrl-C in its terminal)
and that the uninstall steps are in README.md ("Uninstall"); do not run them.

## Step 10. Privacy summary (tell the user)

- Audio stays on this Mac: wake word, voice detection, speech-to-text (Whisper) and text-to-speech
  (Kokoro) all run locally. Audio is not saved or uploaded.
- The text transcript of what they say, and anything the agent reads, is sent to Anthropic through
  their own Claude Code login, under their own account and Anthropic's terms.
- Transcripts are logged locally in `~/.config/jarvis-voice-hub/state/hub.log`; they can delete it
  at any time. Model files were downloaded once from GitHub and Hugging Face.
