# Third-party components

jarvis-voice-hub itself is MIT (see `LICENSE`). It does not redistribute any of the components
below: `setup.sh` and `pip` download them from their own sources. Statuses were read from the
official pages named in the Source column on 2026-11-22. Re-check upstream before relying on them.

| Component | Licence (as stated at source) | Attribution / terms | Source |
|---|---|---|---|
| openWakeWord, code | Apache-2.0 | keep licence notice if you redistribute | https://github.com/dscripka/openWakeWord |
| **openWakeWord pretrained wake-word models** (`hey_jarvis`, `alexa`, `hey_mycroft`, `hey_rhasspy`, ...) | **CC BY-NC-SA 4.0** | **Non-commercial use only**, attribution, share-alike. The README gives the reason as training data with "unknown or restrictive licensing". For any commercial use, train your own model. | same page |
| Silero VAD (bundled in openWakeWord) | MIT, (c) 2020-present Silero Team (LICENSE file) | keep copyright and permission notice. Note: the README badge alt text says "CC BY-NC 4.0" while the LICENSE file and displayed badge say MIT; the LICENSE file was taken as authoritative. | https://github.com/snakers4/silero-vad |
| kokoro-onnx (library) | MIT | notice if redistributed | https://github.com/thewh1teagle/kokoro-onnx |
| Kokoro-82M model (ONNX files from the kokoro-onnx release) | Apache-2.0 (model card and kokoro-onnx README) | notice if redistributed | https://huggingface.co/hexgrad/Kokoro-82M |
| mlx-whisper / mlx-examples | MIT, (c) 2023 Apple Inc. | notice if redistributed | https://github.com/ml-explore/mlx-examples |
| OpenAI Whisper (code and weights) | MIT (README: "code and model weights are released under the MIT License") | notice if redistributed | https://github.com/openai/whisper |
| python-sounddevice | MIT (README) | notice if redistributed | https://github.com/spatialaudio/python-sounddevice |
| NumPy | BSD 3-clause (LICENSE.txt) | binary redistributions must reproduce the notice; no endorsement use of the NumPy name | https://github.com/numpy/numpy |
| Claude Code CLI | Anthropic's terms; not redistributed | you need your own account. "Claude" is a trademark of Anthropic. | https://claude.com/claude-code |

## Not verified

- **Kokoro voices file** (`voices-v1.0.bin`): neither the kokoro-onnx README nor the Kokoro-82M
  card gives the voices a licence of their own; both point to `VOICES.md`, which lists voices with
  no licence statement. The model card says some training audio was CC BY (Koniwa tnc, CC BY 3.0,
  and SIWIS, CC BY 4.0) and tags five voices CC BY (Japanese `jf_gongitsune`, `jf_nezumi`,
  `jf_tebukuro`, `jm_kumo`; French `ff_siwis`). The default voice is `af_heart`. The licence of the
  voices file as a whole is therefore **not verified**; check upstream before commercial use.
- The v1.0 release page describes the voices file as holding 26 voices while `VOICES.md` lists 54;
  this was not resolved.
- **mlx-community/whisper-large-v3-turbo**: the model card states no licence and does not name the
  upstream licence. The MIT status above comes from OpenAI's repository, not from this card.
- **PyObjC** and **ONNX Runtime**: licence not confirmed from an official page in this pass
  (the PyObjC page shows no licence section; the ONNX Runtime page could not be fetched).
- Transitive dependencies (torch, scipy, numba, huggingface_hub, ...; see `requirements.lock`)
  were not audited.
- The SHA-256 checksums in `setup.sh` were computed from files downloaded earlier; upstream
  publishes none. Confirm them yourself.
