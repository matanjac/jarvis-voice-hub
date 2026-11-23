"""Offline tests for speechmodel.py: no network, no download. Run: python test_speechmodel.py
HF_HOME is pointed at a temporary directory in a subprocess, so the real cache is never read."""
import os, subprocess, sys, tempfile, unittest

import speechmodel as S

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "mlx-community/whisper-large-v3-turbo"


def probe(home):
    env = dict(os.environ, HF_HOME=home, VOICE_HUB_WHISPER=REPO)
    env.pop("HF_HUB_CACHE", None)
    env.pop("HUGGINGFACE_HUB_CACHE", None)
    code = "import speechmodel as S; print(S.whisper_cached(), S.cached_path())"
    out = subprocess.run([sys.executable, "-c", code], cwd=HERE, env=env,
                         capture_output=True, text=True, check=True).stdout.split(None, 1)
    return out[0] == "True", out[1].strip()


def fake_cache(home, files):
    base = os.path.join(home, "hub", "models--" + REPO.replace("/", "--"))
    snap = os.path.join(base, "snapshots", "abc123")
    os.makedirs(snap)
    os.makedirs(os.path.join(base, "refs"))
    with open(os.path.join(base, "refs", "main"), "w") as f:
        f.write("abc123")
    for name in files:
        with open(os.path.join(snap, name), "w") as f:
            f.write("x")
    return snap


class Cache(unittest.TestCase):
    def test_empty_cache_is_false(self):
        with tempfile.TemporaryDirectory() as home:
            self.assertEqual(probe(home), (False, "None"))

    def test_complete_looking_cache_is_true(self):
        with tempfile.TemporaryDirectory() as home:
            snap = fake_cache(home, ["config.json", "weights.safetensors"])
            ok, path = probe(home)
            self.assertTrue(ok)
            self.assertEqual(os.path.realpath(path), os.path.realpath(snap))

    def test_config_without_weights_is_false(self):
        with tempfile.TemporaryDirectory() as home:
            fake_cache(home, ["config.json"])
            self.assertFalse(probe(home)[0])


class Progress(unittest.TestCase):
    def test_percent(self):
        self.assertEqual(S.percent(0, 1000), 0)
        self.assertEqual(S.percent(425, 1000), 42)
        self.assertEqual(S.percent(1000, 1000), 99)      # 100 only after the cache check
        self.assertEqual(S.percent(5000, 1000), 99)
        self.assertIsNone(S.percent(5, None))
        self.assertIsNone(S.percent(5, 0))

    def test_log_throttle(self):
        self.assertTrue(S.should_log(None, None, 0, 100.0))          # first line
        self.assertFalse(S.should_log(0, 100.0, 5, 105.0))           # +5 %, 5 s: quiet
        self.assertTrue(S.should_log(0, 100.0, 10, 105.0))           # +10 %
        self.assertTrue(S.should_log(0, 100.0, 1, 130.0))            # 30 s
        self.assertTrue(S.should_log(None, 100.0, None, 131.0))      # unknown total: by time only
        self.assertFalse(S.should_log(None, 100.0, None, 120.0))

    def test_dir_bytes_counts_incomplete(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "blobs"))
            for n, size in (("a", 10), ("b.incomplete", 5)):
                with open(os.path.join(d, "blobs", n), "wb") as f:
                    f.write(b"x" * size)
            self.assertEqual(S.dir_bytes(d), 15)

    def test_say(self):
        m = S.SpeechModel(lambda *_: None, lambda *_: None, "nobody/nothing")
        m.pct = 42
        self.assertIn("about 42 percent", m.say())
        m.failed = True
        self.assertIn("failed", m.say())


if __name__ == "__main__":
    unittest.main()
