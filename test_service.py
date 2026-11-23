"""Tests for service.py. Never loads anything into launchd. Run: python3 -m unittest test_service"""
import contextlib
import io
import os
import plistlib
import tempfile
import unittest

import service


class ServiceTests(unittest.TestCase):
    def test_status_not_installed(self):
        with tempfile.TemporaryDirectory() as d:
            old = service.PLIST
            service.PLIST = os.path.join(d, "nope.plist")
            try:
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = service.status()
            finally:
                service.PLIST = old
        self.assertEqual(rc, 0)
        self.assertIn("not installed", buf.getvalue())

    def test_plist_contents(self):
        d = plistlib.loads(service.render_plist("/x/.venv/bin/python", "/y/bin").encode())
        self.assertEqual(d["Label"], "com.jarvis-voice-hub")
        self.assertEqual(d["ThrottleInterval"], 10)
        self.assertTrue(d["RunAtLoad"])
        self.assertEqual(d["KeepAlive"], {"SuccessfulExit": False})
        self.assertEqual(d["ProgramArguments"][0], "/x/.venv/bin/python")
        path = d["EnvironmentVariables"]["PATH"].split(":")
        for p in ("/opt/homebrew/bin", "/usr/local/bin", "/y/bin"):
            self.assertIn(p, path)
        self.assertTrue(any(p.endswith("/.local/bin") for p in path))
        self.assertNotIn("__", service.render_plist("/p", None))

    def test_parse_print(self):
        info = service.parse_print("x = {\n\tstate = running\n\tpid = 123\n\tlast exit code = (never exited)\n}")
        self.assertEqual((info["state"], info["pid"]), ("running", "123"))


if __name__ == "__main__":
    unittest.main()
