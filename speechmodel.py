"""The Whisper speech model: cache check (never downloads) and a background downloader.

Why this exists: the model is over 1 GB. If it is missing, loading it on the first wake word used
to start a silent download on the main thread, so the hub looked frozen. Now the hub checks the
Hugging Face cache first (`whisper_cached`), and when the model is missing it downloads it in a
background thread (`SpeechModel`) with logged progress and panel notices, while the wake word
loop stays responsive.

Only the standard library is imported at the top; huggingface_hub is imported lazily.
"""
import os
import threading
import time

WEIGHT_FILES = ("weights.safetensors", "weights.npz")   # mlx_whisper loads one of these
LOG_EVERY_PCT = 10          # progress is logged at most every 10 percent ...
LOG_EVERY_SEC = 30          # ... or every 30 seconds, whichever comes first
POLL_SEC = 2.0
RETRY_FIRST, RETRY_MAX = 180.0, 900.0   # backoff after a failed download: 3 min, doubling, max 15 min
MISSING_HINT = "MISSING: run ./setup.sh (a large one-time download)"


def default_repo():
    return os.environ.get("VOICE_HUB_WHISPER", "mlx-community/whisper-large-v3-turbo")


def cached_path(repo=None):
    """Folder of the cached snapshot if config.json and a weights file are both in the Hugging Face
    cache, else None. Reads the cache only: never touches the network, never downloads."""
    repo = repo or default_repo()
    try:
        from huggingface_hub import try_to_load_from_cache
        cfg = try_to_load_from_cache(repo, "config.json")
        weights = [try_to_load_from_cache(repo, f) for f in WEIGHT_FILES]
    except Exception:
        return None
    if isinstance(cfg, str) and any(isinstance(w, str) for w in weights):
        return os.path.dirname(cfg)
    return None


def local_model_dir(repo=None):
    """Local snapshot directory of the cached model, resolved with local_files_only=True so no
    network call is possible. Raises if the model is not cached (the download path is separate)."""
    repo = repo or default_repo()
    from huggingface_hub import snapshot_download
    path = snapshot_download(repo, local_files_only=True)
    if not os.path.isdir(path):
        raise RuntimeError(f"cached model folder missing: {path}")
    return path


def whisper_cached(repo=None):
    return cached_path(repo) is not None


def cache_dir(repo):
    from huggingface_hub import constants
    return os.path.join(constants.HF_HUB_CACHE, "models--" + repo.replace("/", "--"))


def dir_bytes(path):
    """Total size of the files under `path` (partial `.incomplete` downloads included)."""
    total = 0
    for root, _dirs, files in os.walk(os.path.join(path, "blobs")):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def percent(done, total):
    """Whole percent 0..99 while downloading (100 is only reported once the cache check passes);
    None when the total size is unknown."""
    if not total or total <= 0:
        return None
    return max(0, min(99, int(100 * done / total)))


def should_log(last_pct, last_t, pct, now):
    """Progress log throttle: first line always, then +10 percent or 30 s since the last line."""
    if last_t is None:
        return True
    if pct is not None and (last_pct is None or pct >= last_pct + LOG_EVERY_PCT):
        return True
    return now - last_t >= LOG_EVERY_SEC


def total_bytes(repo):
    """Size of every file in the repo (what snapshot_download fetches), or None if unknown."""
    from huggingface_hub import HfApi
    info = HfApi().model_info(repo, files_metadata=True)
    sizes = [s.size for s in (info.siblings or []) if s.size]
    return sum(sizes) or None


class SpeechModel:
    """Background download of the Whisper model. `log(msg)` and `notice(status, text, error)` are
    callbacks supplied by the hub. Read `.ready` and `.pct` from any thread."""

    def __init__(self, log, notice, repo=None):
        self.repo = repo or default_repo()
        self.log, self.notice = log, notice
        self.ready = whisper_cached(self.repo)
        self.pct = None
        self.failed = False
        self.error = ""
        self._thread = None

    def start(self):
        """No-op if cached or already running."""
        if self.ready or (self._thread and self._thread.is_alive()):
            return
        self.log("Whisper model not downloaded yet; downloading now (large, one time)")
        self._thread = threading.Thread(target=self._run, name="whisper-download", daemon=True)
        self._thread.start()

    def say(self):
        """What to tell the user if they speak while the model is not ready."""
        if self.failed:
            return "My speech model download failed. I will keep retrying, check the log."
        if self.pct is None:
            return "I am still downloading my speech model."
        return f"I am still downloading my speech model, about {self.pct} percent done."

    def _download_once(self):
        from huggingface_hub import snapshot_download
        try:
            total = total_bytes(self.repo)
        except Exception as e:
            self.log(f"Whisper download: could not read the model size ({e!r}); progress will show MB only")
            total = None
        err = []

        def work():
            try:
                snapshot_download(self.repo)
            except BaseException as e:              # reported by the poller below
                err.append(e)

        w = threading.Thread(target=work, name="hf-snapshot", daemon=True)
        w.start()
        folder = cache_dir(self.repo)
        last_pct, last_t, last_shown = None, None, object()
        while w.is_alive():
            done = dir_bytes(folder)
            self.pct = percent(done, total)
            now = time.time()
            if should_log(last_pct, last_t, self.pct, now):
                last_pct, last_t = self.pct, now
                self.log(f"Whisper model download: {self.pct}%" if self.pct is not None
                         else f"Whisper model download: {done // 2**20} MB so far")
            if self.pct != last_shown:
                last_shown = self.pct
                self.notice(f"DOWNLOADING SPEECH MODEL {self.pct}%" if self.pct is not None
                            else "DOWNLOADING SPEECH MODEL",
                            "One time download, about 1.6 GB", False)
            time.sleep(POLL_SEC)
        if err:
            raise err[0]
        if not whisper_cached(self.repo):
            raise RuntimeError("download finished but config.json / weights are not in the cache")

    def _run(self):
        delay = RETRY_FIRST
        while True:
            try:
                self.failed = False
                self.notice("DOWNLOADING SPEECH MODEL", "One time download, about 1.6 GB", False)
                self._download_once()
                self.pct, self.ready, self.error = 100, True, ""
                self.log(f"Whisper model downloaded and cached at {cached_path(self.repo)}")
                self.notice("", "", False)
                return
            except Exception as e:
                self.failed, self.error = True, repr(e)
                self.log(f"Whisper model download FAILED: {e!r}; retrying in {int(delay // 60)} min")
                self.notice("SPEECH MODEL DOWNLOAD FAILED",
                            f"Retrying in {int(delay // 60)} min, see hub.log", True)
                time.sleep(delay)
                delay = min(delay * 2, RETRY_MAX)
