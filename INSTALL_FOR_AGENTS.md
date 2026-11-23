# Install instructions for an AI coding agent

You are an AI coding agent (for example Claude Code) and a person has asked you to install
jarvis-voice-hub on their Mac. The person is probably not technical and may have no GitHub account.
Follow this file in order. Explain each step in plain words before you do it, and wait for a clear
yes before every non-trivial step (installing a tool, running `./setup.sh`, starting the hub).

## Rules (never break these)

- Do not use `sudo`. Never ask for, see, read or type the user's Mac password.
- Do not run anything that is not in this repository, with one exception: the official Homebrew
  installer from https://brew.sh, and only if Homebrew is missing and the user agrees.
- Security settings: the default is the `safe` profile (plan mode, isolation on). The only way it
  changes is the single question in step 5, answered by the user. You write ONLY the chosen word
  to `~/.config/jarvis-voice-hub/profile` (via `hub.py --set-profile`, step 6) and never edit any
  other settings or permission file. Do not set `VOICE_HUB_PERMISSION_MODE`, `VOICE_HUB_ISOLATE`,
  `VOICE_HUB_TOOLS` or `VOICE_HUB_PROFILE`, and never touch the user's own Claude Code settings.
- Do not start the hub (`hub.py` without `--check`, or `--install-service`) before the user has
  chosen the safety mode, `--check` has passed and the user has confirmed (step 7). Run the hub
  only as the background service from step 7; never start it in your own session.
- Do not improvise. If any command fails, stop, show the exact command and its exact error, give the
  matching fix from the "Troubleshooting" table in README.md (or say none is documented), and wait.
- Do not use `rm -rf`. Do not use `launchctl` yourself and do not hand-write plists: the only way
  to install the background service is `hub.py --install-service` (step 7).
- Do not log in to GitHub. The repository is public and is cloned over HTTPS.

## Step 1. Check the Mac

Run `uname -m` and `sw_vers -productVersion`.

- `uname -m` must print `arm64` (Apple Silicon: M1 or newer). If it prints `x86_64`, stop: explain
  that the speech recognition (MLX) does not run on Intel Macs, so this project cannot work here.
- The macOS version must be 14 or newer (the first number is 14 or more). If older, stop and
  explain that they need to update macOS first.

## Step 2. Check the `claude` command is available

You are running inside Claude Code, so the user is already signed in: do not ask them about it.
Only run `claude --version` to confirm the `claude` command is on the PATH, because the hub starts
it as a separate process (its "brain", under the user's own account). If the command is not found
in a normal terminal, tell the user and stop; do not try to install or sign in on their behalf.

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

- It only acts after the wake word, but that is the only gate. Anyone or anything that says the
  wake phrase (a guest, a child, a TV, a video) can start a conversation, the detector can also
  false-trigger, and for a few seconds afterwards everything it hears is treated as your next
  instruction. There is no voice ID, and the wake word is public.
- Text the agent reads (files, web pages) can try to give it instructions (prompt injection).
- By default it runs in `plan` mode (read-only tools) with brain isolation on, in an empty scratch
  folder. That is the `safe` profile.
- Transcripts of what it hears are saved on this Mac in `~/.config/jarvis-voice-hub/state/hub.log`.

Ask whether they understand and want to continue. Then ask exactly ONE plain question:

> Which mode: 1) safe read-only (recommended, default), 2) use my own Claude Code permissions,
> 3) full power (can run commands, edit files, start helpers)?

Explain each option in two sentences, including the risk:

1. **safe** (profile `safe`): it can only read and search files in an empty scratch folder; it
   cannot run commands, edit files, browse the web or use your tools. The worst a stranger or a TV
   can do is make it read and speak what is in that folder.
2. **own permissions** (profile `own-settings`): it uses your own Claude Code settings and MCP
   servers, but anything your settings do not already allow is refused. Whatever you pre-approved
   there, anyone or anything that says the wake word (a guest, a TV, a video), or text it reads
   (prompt injection), can then use.
3. **full power** (profile `full`): it can run commands, edit files and start background helpers
   and report back by voice, without asking. Anyone or anything that says the wake word, a TV, a
   guest, or prompt injection from text it reads can then act with all those powers on this Mac.

Rules for the answer:

- If the user does not answer, or is unsure, use `safe`.
- For option 3, make the user type the word `FULL` themselves to confirm. Anything else means `safe`.
- Remember the answer; save it right after `./setup.sh` finishes in step 6 (that creates the
  environment). Save only the chosen word, nothing else, with one of these (this creates the file
  with owner-only permissions):

  ```sh
  .venv/bin/python hub.py --set-profile safe
  .venv/bin/python hub.py --set-profile own-settings
  .venv/bin/python hub.py --set-profile full --confirm FULL
  ```

  Do not edit any other file or setting. If `safe` was chosen you may skip this command, since
  `safe` is the default.
- Tell the user how to change it later: run the same command with another word, or edit the
  one-word file `~/.config/jarvis-voice-hub/profile`, or set `VOICE_HUB_PROFILE`, then restart the
  hub. `hub.py --check` always shows the active profile.

## Step 6. Run setup and the check

Tell the user what `./setup.sh` does: creates a Python environment in the repo folder, installs
pinned packages, downloads the Kokoro speech model (about 350 MB, checksum verified), compiles two
small microphone helpers from `native/*.c`, downloads the Whisper speech model from Hugging Face
(a large one-time download, over 1 GB, which can take several minutes: tell the user it is normal
and do not interrupt it; without it the hub looks stuck on LISTENING at the first wake word),
and writes only inside the repo folder and
`~/.config/jarvis-voice-hub`. About 2.5 GB in total, a few minutes. After confirmation:

```sh
cd ~/jarvis-voice-hub
./setup.sh
```

Then save the mode chosen in step 5 (see there), and run the check:

```sh
.venv/bin/python hub.py --check
```

Report the result of each command in plain language. In the `--check` output, everything should be
OK (optional helpers may be flagged), the `profile` line must show the mode the user chose (and
the one-line summary and any warning must match it), and the `claude` CLI must be found. If something fails, apply the rule "do not improvise".

## Step 7. Install the background service, then microphone permission

The hub runs as a normal user-level macOS LaunchAgent (label `com.jarvis-voice-hub`): in the
background, no Terminal needed, started at every login, restarted if it crashes (not if it exits
cleanly). Do this only after setup and `--check` have passed and the user has chosen the safety
mode (step 5).

First explain, then ask for confirmation. Say: "I will install the hub as a background service.
macOS will then show a dialog saying that 'python' (or 'Python') wants to access the microphone;
you must click Allow. The permission belongs to the python program inside this folder, not to your
Terminal. Are you ready, and will you click Allow when it appears?" Optionally preview first with
`.venv/bin/python hub.py --install-service --dry-run` (prints the plist and the launchctl commands,
changes nothing). Wait for a yes, then run:

```sh
cd ~/jarvis-voice-hub
.venv/bin/python hub.py --install-service
```

It refuses to run as root, writes `~/Library/LaunchAgents/com.jarvis-voice-hub.plist`, checks it
with `plutil -lint`, loads it with `launchctl bootstrap gui/<uid>` and prints exactly what it did.
Report that output in plain language. If it says a hub is already running, ask the user to stop
that one (Ctrl-C in its terminal) and run the command again.

Walk the user through the microphone dialog:

- Within a few seconds of the first start macOS shows "python wants to access the microphone". They
  click **Allow**. The hub speaks "<name> is online" a moment later.
- If they missed or denied it: System Settings > Privacy & Security > Microphone, switch the
  Python entry on (it may only appear after the first attempt), then run `./restart.sh`.
- Check the log: `tail -f ~/.config/jarvis-voice-hub/state/hub.log` (press Ctrl-C to stop watching;
  that does not stop the hub). About 3 seconds after start it prints `mic check: level ... - ok`.
  If it says `level 0.0000 - SILENT: microphone permission missing?`, the permission is missing.
- Status at any time: `.venv/bin/python hub.py --service-status` (loaded or not, pid, last exit
  status, last 10 log lines).

Then tell them to say the wake word ("hey jarvis") and continue with step 8.

To stop and remove the service: `.venv/bin/python hub.py --uninstall-service` (boots it out and
deletes the plist). `./restart.sh` restarts it gracefully. Running `hub.py` in a Terminal window
(foreground, Ctrl-C to stop) is only a troubleshooting option: stop the service first, because only
one hub can use the microphone.

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
If the log shows `mic check ... SILENT`, microphone permission is missing: use step 7 or the table in README.md.

## Step 9. Post-install checklist

Walk through the checklist in README.md under "After install: what to verify" and report which
items passed and which were not tried. Also tell the user how to stop it (`.venv/bin/python hub.py --uninstall-service`)
and that the full uninstall steps are in README.md ("Uninstall"); do not run them.

## Step 10. Privacy summary (tell the user)

- Audio stays on this Mac: wake word, voice detection, speech-to-text (Whisper) and text-to-speech
  (Kokoro) all run locally. Audio is not saved or uploaded.
- The text transcript of what they say, and anything the agent reads, is sent to Anthropic through
  their own Claude Code login, under their own account and Anthropic's terms.
- Transcripts are logged locally in `~/.config/jarvis-voice-hub/state/hub.log`; they can delete it
  at any time. Model files were downloaded once from GitHub and Hugging Face.
