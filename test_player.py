"""Tests for hub.Player with a fake sounddevice OutputStream (no audio device needed).
Run: python3 -m unittest test_player"""
import threading
import time
import unittest
from unittest import mock

import numpy as np

import hub


class FakeStream:
    instances = []
    underrun_on = ()          # write indexes that report an underrun

    def __init__(self, **kw):
        self.kw, self.active, self.written, self.starts, self.stops = kw, False, [], 0, 0
        self.aborted = self.closed = False
        self.write_delay = 0.0
        FakeStream.instances.append(self)

    def start(self):
        self.active = True
        self.starts += 1

    def stop(self):
        self.active = False
        self.stops += 1

    def abort(self):
        self.active = False
        self.aborted = True

    def close(self):
        self.closed = True

    def write(self, data):
        time.sleep(self.write_delay)
        self.written.append(len(data))
        return (len(self.written) - 1) in FakeStream.underrun_on


class PlayerTests(unittest.TestCase):
    def setUp(self):
        FakeStream.instances, FakeStream.underrun_on = [], ()
        self.logs = []
        for p in (mock.patch.object(hub.sd, "OutputStream", FakeStream),
                  mock.patch.object(hub, "log", self.logs.append)):
            p.start()
            self.addCleanup(p.stop)

    def test_plays_everything_and_uses_config(self):
        n = hub.Player.CHUNK * 3 + 100
        p = hub.Player(np.zeros(n), 24000)
        s = FakeStream.instances[0]
        self.assertEqual(s.kw["latency"], hub.C.PLAYBACK_LATENCY)
        self.assertEqual(s.kw["blocksize"], hub.Player.CHUNK)
        p.start()
        self.assertTrue(p.done.wait(2))
        self.assertEqual(sum(s.written), n)
        self.assertEqual(p.pos, n)
        self.assertTrue(s.closed)
        self.assertEqual(p.underruns, 0)
        self.assertEqual(self.logs, [])

    def test_underruns_counted_and_logged(self):
        FakeStream.underrun_on = (0, 2)
        p = hub.Player(np.zeros(hub.Player.CHUNK * 4), 24000)
        p.start()
        self.assertTrue(p.done.wait(2))
        self.assertEqual(p.underruns, 2)
        self.assertTrue(any("2 underrun(s)" in m for m in self.logs))

    def test_pause_resume_keeps_position(self):
        p = hub.Player(np.zeros(hub.Player.CHUNK * 40), 24000)
        s = FakeStream.instances[0]
        s.write_delay = 0.01
        p.start()
        time.sleep(0.05)
        p.pause()
        time.sleep(0.1)
        self.assertFalse(s.active)
        frozen = p.pos
        time.sleep(0.1)
        self.assertEqual(p.pos, frozen)        # nothing played while paused
        self.assertFalse(p.done.is_set())
        p.resume()
        self.assertTrue(p.done.wait(3))
        self.assertEqual(p.pos, hub.Player.CHUNK * 40)   # carried on, nothing skipped or repeated
        self.assertEqual(sum(s.written), hub.Player.CHUNK * 40)
        self.assertGreaterEqual(s.starts, 2)   # restarted after the pause

    def test_stop_aborts_early(self):
        p = hub.Player(np.zeros(hub.Player.CHUNK * 200), 24000)
        s = FakeStream.instances[0]
        s.write_delay = 0.01
        p.start()
        time.sleep(0.05)
        p.stop()
        self.assertTrue(p.done.is_set())
        self.assertTrue(s.aborted and s.closed)
        self.assertLess(p.pos, hub.Player.CHUNK * 200)


class SpeakTests(unittest.TestCase):
    def setUp(self):
        FakeStream.instances, FakeStream.underrun_on = [], ()
        for p in (mock.patch.object(hub.sd, "OutputStream", FakeStream),
                  mock.patch.object(hub, "log", lambda m: None)):
            p.start()
            self.addCleanup(p.stop)
        m = hub.Models()
        m._kt = threading.Thread(target=lambda: None)
        m._kt.start()
        m.kokoro = mock.Mock()
        m.kokoro.create.return_value = (np.zeros(hub.Player.CHUNK * 100), 24000)
        self.m = m

    def intr(self, button=False, wake=False, stop=False):
        i = mock.Mock()
        i.button.return_value = button
        i.wake_fired.return_value = wake
        i.voice_stop.return_value = stop
        return i

    def test_button_cancels(self):
        FakeStream.write_delay = 0
        with mock.patch.object(FakeStream, "write", lambda s, d: time.sleep(0.01)):
            self.assertTrue(self.m.speak("x", self.intr(button=True)))

    def test_voice_cancel_disabled_ignores_wake(self):
        i = self.intr(wake=True, stop=True)
        with mock.patch.object(hub.C, "VOICE_CANCEL", False), \
                mock.patch.object(hub.C, "SPEAK_POLL", 0.001):
            self.assertFalse(self.m.speak("x", i))
        i.wake_fired.assert_not_called()
        i.mic.drain.assert_called()

    def test_no_interrupter_plays_through(self):
        self.assertFalse(self.m.speak("x"))
        self.assertEqual(sum(FakeStream.instances[0].written), hub.Player.CHUNK * 100)


if __name__ == "__main__":
    unittest.main()
