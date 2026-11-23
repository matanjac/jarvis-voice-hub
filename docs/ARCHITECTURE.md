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
| `ui.py` | HUD process; tails the event file; exits when the hub pid is gone |
| `config.py` | all paths and settings, env-var overridable |
| `native/defaultmic.c` | prints the current default input device name (CoreAudio) |
| `native/micusers.c` | lists processes currently capturing audio input (CoreAudio, macOS 14.2+) |
| `setup.sh` | venv, deps, Kokoro files, compiles the helpers, optional launchd plist |
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
- **Restart.** `SIGUSR1` sets a flag; the hub re-executes (`os.execv`) at a safe point (idle loop
  or right after a spoken sentence). The file lock is close-on-exec, so the new process takes it.
- **HUD events.** `reset | wake | listen | you | think | assistant | jobs | end`. A background
  thread in the hub runs `claude agents --json` every 6 s and emits `jobs` with the number of
  busy background sessions.
- **State files** (all under `~/.config/jarvis-voice-hub/state/`): `hub.log`, `ui.err`, `hub.pid`,
  `brain_session.txt`, `ui_events.jsonl`, lock files. Delete `brain_session.txt` to forget the
  conversation.

## Trust boundaries

Everything audible is untrusted input to the brain; everything the brain reads (files, web, other
sessions) is untrusted input too. The only controls are the permission mode passed to
`claude -p`, the scratch working directory and the system prompt. See README "Security".
