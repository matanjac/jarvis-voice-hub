# Architecture

```
                       +--------------------------------------------+
   microphone ───────► |  hub.py  (one process, main thread)        |
   (sounddevice,       |                                            |
    16 kHz, 80 ms      |  Mic: callback -> queue (buffers audio     |
    frames)            |       while models load / brain thinks)    |
                       |                                            |
   STANDBY             |  openWakeWord ── score > threshold? ──┐    |
   (only this runs)    |                                       │    |
                       |  WAKE  (Tink)                         ▼    |
                       |   ├─ load Kokoro (thread) + Whisper (main) |
                       |   └─ loop:                                 |
                       |       Silero VAD  ->  record utterance     |
                       |       (Pop)                                |
                       |       mlx-whisper -> text + confidence     |
                       |       reject if avg_logprob < -1.0         |
                       |       goodbye? / "new conversation"?       |
                       |       Brain.ask(text)  ──────────────┐     |
                       |       Kokoro -> speakers   ◄─ reply ─┤     |
                       |       follow-up window (7 s)         │     |
                       |  END (Bottle) -> unload models       │     |
                       +---------+----------------------------┼-----+
                                 │ append JSON lines          │ stdin/stdout, stream-json
                                 ▼                            ▼
                        state/ui_events.jsonl        `claude -p` (persistent subprocess)
                                 │                   cwd = scratch workspace
                                 ▼                   --permission-mode plan (default)
                       ui.py  floating HUD           session id -> state/brain_session.txt
                       (PyObjC, own process)
```

## Pieces

| File | Role |
|---|---|
| `hub.py` | wake word, recording, STT, brain client, TTS, mic handling, restart signal |
| `ui.py` | HUD process (orb, Cancel/Retry buttons, activity line, mic level bar); tails the event file, writes commands; exits when the hub pid is gone |
| `config.py` | all paths and settings, env-var overridable |
| `native/defaultmic.c` | prints the current default input device name (CoreAudio) |
| `native/micusers.c` | lists processes currently capturing audio input (CoreAudio, macOS 14.2+) |
| `setup.sh` | venv, deps, Kokoro files, compiles the helpers, optional launchd plist |
| `INSTALL_FOR_AGENTS.md` | step-by-step install instructions for an AI coding agent (the recommended path: the user pastes a short prompt into Claude Code, which clones over HTTPS and follows this file) |
| `restart.sh` | SIGUSR1 to the pid in `state/hub.pid` |

## Control flow notes

- **Models are per-conversation.** Whisper and Kokoro are loaded at wake and freed at the end, so
  standby memory is just the wake model. MLX requires Whisper to load on the main thread; Kokoro
  loads in a background thread. The mic callback keeps filling its queue meanwhile.
- **Brain protocol.** One JSON user message per line on stdin; the hub waits for a `result`
  event on stdout (180 s timeout). A reader thread pushes every `result` into a queue. Results
  that arrive with no question pending are "late" results; `take_late()` returns them to be
  spoken (skipping `(silent)`).
- **Mic watchdog.** No audio for 2 s means reopen the current default device. Every ~3 s the
  default device name is compared; every ~1 s `micusers` is polled and the hub releases the mic
  while another process is using it.
- **Restart.** `./restart.sh` sends `SIGUSR1`, which sets a flag; the hub re-executes (`os.execv`) at a safe point (idle loop
  or right after a spoken sentence). The file lock is close-on-exec, so the new process takes it.
- **HUD events** (hub -> `state/ui_events.jsonl`, one `{"k": kind, "t": text}` per line):

  | kind | `t` | effect in the panel |
  |---|---|---|
  | `reset` | | clear and hide (sent at hub start) |
  | `wake` / `listen` | | show panel, status LISTENING |
  | `you` / `assistant` | transcript / reply text | add a line; status THINKING (with a seconds timer) / SPEAKING |
  | `think` | | status THINKING |
  | `activity` | short label such as "Reading a file"; empty clears | replaces the subtitle line while the brain works. Built from tool names only (never tool inputs or outputs) |
  | `level` | mic level `0`..`1`, at most 4 per second | thin level bar beside the orb while listening |
  | `heard` | `clear` / `unsure` / `ignored` | tag "Heard clearly" / "Unsure" / "Ignored noise" for 4 s after each transcription (clear = avg_logprob >= -0.6) |
  | `stopped` | | request cancelled: status "CANCELLED - LISTENING" and a Retry button |
  | `jobs` | `{"n": 2, "names": ["a", "b"]}` (a plain integer string also works) | WORKING status, plus a "Working: a, b" line (names sanitised, at most 3) |
  | `end` | | status STANDBY, hide a few seconds later (stays up while jobs run) |

  A background thread in the hub runs `claude agents --json` every 6 s and emits `jobs`.
- **HUD commands** (panel -> hub, `state/ui_commands.jsonl`, same format): `{"k":"stop"}` from the
  Cancel button (visible while THINKING or SPEAKING) and `{"k":"retry"}` from the Retry button
  (visible after a cancel). The hub truncates the file at startup and ignores clicks made before
  the current question.
- **Cancel.** While `Brain.ask` waits (polled every 20 ms) and while a reply is being spoken, the
  hub honours (1) the Cancel button and (2) the wake word followed within about 3 s by
  "stop", "cancel", "never mind" or "hold on" (transcribed with Whisper; low-confidence clips are
  ignored, and a bare "stop" without the wake word does nothing). Cancelling terminates the
  `claude -p` subprocess but keeps `brain_session.txt`, so the next question resumes the same
  conversation; speech is cut off, the panel shows CANCELLED and Retry for 15 s, and Retry
  re-sends the last transcript without re-speaking it.
- **State files** (all under `~/.config/jarvis-voice-hub/state/`): `hub.log`, `ui.err`, `hub.pid`,
  `brain_session.txt`, `ui_events.jsonl`, `ui_commands.jsonl`, lock files. Delete `brain_session.txt` to forget the
  conversation.

## Trust boundaries

Everything audible is untrusted input to the brain; everything the brain reads (files, web, other
sessions) is untrusted input too. The only controls are the permission mode passed to
`claude -p`, the scratch working directory and the system prompt. See README "Security".
