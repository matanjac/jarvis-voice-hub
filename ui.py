"""jarvis-voice-hub HUD: a small translucent always-on-top panel, hidden until the hub hears the
wake word. It tails ui_events.jsonl (written by hub.py) and shows the conversation live.
Never takes focus. Exits when the hub process goes away.

Run by the hub:  python ui.py <hub_pid>
Standalone demo: python ui.py --events /path/to/events.jsonl   (no hub needed; see README)
Events (one JSON per line, {"k": kind, "t": text}):
    reset | wake | listen | you | think | assistant | jobs | end
"""
import fcntl
import json
import os
import sys
import time

import objc
from AppKit import (
    NSApplication, NSApplicationActivationPolicyAccessory, NSBackingStoreBuffered, NSColor,
    NSFont, NSFloatingWindowLevel, NSMakeRect, NSMutableAttributedString, NSPanel,
    NSScreen, NSScrollView, NSTextField, NSTextView, NSVisualEffectView,
    NSWindowCollectionBehaviorCanJoinAllSpaces, NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowStyleMaskBorderless, NSWindowStyleMaskNonactivatingPanel,
    NSForegroundColorAttributeName, NSFontAttributeName, NSParagraphStyleAttributeName,
    NSMutableParagraphStyle, NSView, NSBezierPath, NSGradient,
)
from Foundation import NSObject, NSTimer
import math

import config as C

NAME = C.ASSISTANT_NAME
EVENTS = C.UI_EVENTS
LOCK = C.UI_LOCK
HUB_PID = 0
_args = sys.argv[1:]
if "--events" in _args:                      # standalone mode: tail a given file, no hub
    i = _args.index("--events")
    EVENTS = os.path.expanduser(_args[i + 1])
    LOCK = EVENTS + ".lock"
    del _args[i:i + 2]
if _args and _args[0].isdigit():
    HUB_PID = int(_args[0])
W, H = 440, 300
STAY_WHILE_WORKING = True # keep the panel up (status: Working) while background jobs run
ALPHA = 0.94              # whole-panel opacity: lower = more see-through
IDLE_HIDE = 60            # failsafe: hide if no event at all for this long (unless jobs are running)
HIDE_AFTER = 2.5          # s after the conversation ends


def dbg(msg):
    print(time.strftime('%H:%M:%S'), msg, file=sys.stderr, flush=True)


def alive(pid):
    if not pid:
        return True
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False



# ---------------------------------------------------------------- theme
COLORS = {            # state -> (r, g, b)
    "idle":   (0.25, 0.55, 0.85),
    "listen": (0.20, 0.88, 1.00),
    "think":  (1.00, 0.68, 0.18),
    "speak":  (0.45, 0.95, 1.00),
    "work":   (1.00, 0.78, 0.25),
}
LABELS = {"idle": "STANDBY", "listen": "LISTENING", "think": "THINKING", "speak": "SPEAKING",
          "work": "WORKING"}
ACCENT = (0.20, 0.88, 1.00)


def rgba(c, a):
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(c[0], c[1], c[2], a)


def arc(cx, cy, r, a0, a1, width, color):
    p = NSBezierPath.bezierPath()
    p.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_((cx, cy), r, a0, a1)
    p.setLineWidth_(width)
    color.set()
    p.stroke()


class OrbView(NSView):
    """Orb avatar that changes with state: calm ring when listening,
    fast amber spin when thinking, a pulsing waveform halo when speaking."""

    def drawRect_(self, rect):
        b = self.bounds()
        cx, cy = b.size.width / 2, b.size.height / 2
        R = min(b.size.width, b.size.height) / 2 - 2
        t, st = self.t, self.state
        c = COLORS[st]
        spin = {"idle": 0.25, "listen": 0.7, "think": 3.2, "speak": 1.6, "work": 2.0}[st]
        pulse = {"idle": 0.04, "listen": 0.10, "think": 0.18, "speak": 0.30, "work": 0.14}[st]
        wob = 1 + pulse * (math.sin(t * 5.0) * 0.6 + math.sin(t * 8.3 + 1) * 0.4)

        # soft glow
        g = NSGradient.alloc().initWithStartingColor_endingColor_(rgba(c, 0.55), rgba(c, 0.0))
        g.drawFromCenter_radius_toCenter_radius_options_((cx, cy), 0, (cx, cy), R * 1.0 * wob, 0)
        # outer ring + rotating segments
        arc(cx, cy, R * 0.96, 0, 360, 1.0, rgba(c, 0.35))
        for i in range(3):
            a = math.degrees(t * spin) + i * 120
            arc(cx, cy, R * 0.86, a, a + 70, 2.4, rgba(c, 0.95))
        # counter-rotating dashed ring
        for i in range(12):
            a = -math.degrees(t * spin * 0.6) + i * 30
            arc(cx, cy, R * 0.70, a, a + 14, 1.4, rgba(c, 0.55))
        # speaking: audio-style radial bars
        if st == "speak":
            for i in range(28):
                ang = i / 28 * 2 * math.pi
                amp = 0.35 + 0.65 * abs(math.sin(t * 7 + i * 1.7) * math.sin(t * 3.1 + i))
                r0, r1 = R * 0.52, R * (0.52 + 0.16 * amp)
                p = NSBezierPath.bezierPath()
                p.moveToPoint_((cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)))
                p.lineToPoint_((cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)))
                p.setLineWidth_(1.6)
                rgba(c, 0.9).set()
                p.stroke()
        # inner triangle
        tri = NSBezierPath.bezierPath()
        for i in range(3):
            ang = t * spin * 0.5 + i * 2 * math.pi / 3 + math.pi / 2
            pt = (cx + R * 0.40 * math.cos(ang), cy + R * 0.40 * math.sin(ang))
            tri.moveToPoint_(pt) if i == 0 else tri.lineToPoint_(pt)
        tri.closePath()
        tri.setLineWidth_(1.4)
        rgba(c, 0.85).set()
        tri.stroke()
        # bright core
        g2 = NSGradient.alloc().initWithStartingColor_endingColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 1, 1, 0.95), rgba(c, 0.0))
        g2.drawFromCenter_radius_toCenter_radius_options_((cx, cy), 0, (cx, cy), R * 0.34 * wob, 0)


class HudFrame(NSView):
    """Cyan corner brackets and a thin top line over the panel."""

    def drawRect_(self, rect):
        b = self.bounds()
        w, h = b.size.width, b.size.height
        col, L, m = rgba(ACCENT, 0.85), 18, 6
        p = NSBezierPath.bezierPath()
        for (x, y, dx, dy) in ((m, m, 1, 1), (w - m, m, -1, 1), (m, h - m, 1, -1), (w - m, h - m, -1, -1)):
            p.moveToPoint_((x + dx * L, y))
            p.lineToPoint_((x, y))
            p.lineToPoint_((x, y + dy * L))
        p.setLineWidth_(1.6)
        col.set()
        p.stroke()
        q = NSBezierPath.bezierPath()
        q.moveToPoint_((m + L + 8, h - m))
        q.lineToPoint_((w - m - L - 8, h - m))
        q.setLineWidth_(0.6)
        rgba(ACCENT, 0.35).set()
        q.stroke()

    def hitTest_(self, pt):
        return None            # never swallow clicks/drags


class View:
    def __init__(self):
        self.offset = os.path.getsize(EVENTS) if os.path.exists(EVENTS) else 0
        self.hide_at = None
        self.last_event = time.time()
        self.jobs = 0
        self.ended = False
        self.ticks = 0
        self.build()

    def build(self):
        scr = NSScreen.mainScreen().visibleFrame()
        rect = NSMakeRect(scr.origin.x + scr.size.width - W - 24, scr.origin.y + 24, W, H)
        style = NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel
        p = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, NSBackingStoreBuffered, False)
        p.setLevel_(NSFloatingWindowLevel + 1)
        p.setOpaque_(False)
        p.setBackgroundColor_(NSColor.clearColor())
        p.setHasShadow_(True)
        p.setAlphaValue_(ALPHA)
        p.setMovableByWindowBackground_(True)
        p.setHidesOnDeactivate_(False)
        p.setBecomesKeyOnlyIfNeeded_(True)
        p.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces
                                 | NSWindowCollectionBehaviorFullScreenAuxiliary)
        fx = NSVisualEffectView.alloc().initWithFrame_(NSMakeRect(0, 0, W, H))
        fx.setMaterial_(13)              # HUD window (blur)
        fx.setBlendingMode_(0)
        fx.setState_(1)
        fx.setWantsLayer_(True)
        fx.layer().setCornerRadius_(14)
        fx.layer().setMasksToBounds_(True)
        fx.layer().setBorderWidth_(1.0)
        fx.layer().setBorderColor_(rgba(ACCENT, 0.55).CGColor())
        p.setContentView_(fx)

        # deep-blue tint over the blur
        tint = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, W, H))
        tint.setWantsLayer_(True)
        tint.layer().setBackgroundColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.01, 0.04, 0.09, 0.80).CGColor())
        fx.addSubview_(tint)

        # avatar
        self.orb = OrbView.alloc().initWithFrame_(NSMakeRect(18, H - 18 - 92, 92, 92))
        self.orb.t, self.orb.state = 0.0, "idle"
        fx.addSubview_(self.orb)

        mono = NSFont.fontWithName_size_("Menlo-Bold", 13) or NSFont.boldSystemFontOfSize_(13)
        mono_s = NSFont.fontWithName_size_("Menlo", 11) or NSFont.systemFontOfSize_(11)

        def label(frame, font, color, text=""):
            f = NSTextField.alloc().initWithFrame_(frame)
            f.setEditable_(False)
            f.setBezeled_(False)
            f.setDrawsBackground_(False)
            f.setFont_(font)
            f.setTextColor_(color)
            f.setStringValue_(text)
            return f

        self.title = label(NSMakeRect(124, H - 52, W - 140, 20), mono, rgba(ACCENT, 1.0),
                           NAME.upper())
        self.status = label(NSMakeRect(124, H - 76, W - 140, 18), mono_s, rgba(ACCENT, 0.75))
        self.sub = label(NSMakeRect(124, H - 98, W - 140, 16), mono_s, rgba(ACCENT, 0.45),
                         "VOICE ASSISTANT // ONLINE")
        for v in (self.title, self.status, self.sub):
            fx.addSubview_(v)

        sv = NSScrollView.alloc().initWithFrame_(NSMakeRect(14, 16, W - 28, H - 128))
        sv.setDrawsBackground_(False)
        sv.setHasVerticalScroller_(True)
        sv.setAutohidesScrollers_(True)
        tv = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, W - 28, H - 128))
        tv.setEditable_(False)
        tv.setSelectable_(True)
        tv.setDrawsBackground_(False)
        tv.setVerticallyResizable_(True)
        tv.setHorizontallyResizable_(False)
        tv.setTextContainerInset_((4, 4))
        sv.setDocumentView_(tv)
        fx.addSubview_(sv)

        fx.addSubview_(HudFrame.alloc().initWithFrame_(NSMakeRect(0, 0, W, H)))
        self.panel, self.tv, self.fx = p, tv, fx
        self.state = "idle"
        self.t0 = time.time()
        self.set_status("")

    # -- rendering
    def set_status(self, s):
        low = s.lower()
        if self.jobs and (not s or low.startswith(("standby", "thinking"))):
            state, text = "work", f"WORKING · {self.jobs} BACKGROUND JOB{'S' if self.jobs != 1 else ''}"
        else:
            state = ("listen" if low.startswith("listening") else
                     "think" if low.startswith("thinking") else
                     "speak" if low.startswith("speaking") else "idle")
            text = LABELS[state]
            if self.jobs:
                text += f"  ·  {self.jobs} JOB{'S' if self.jobs != 1 else ''} RUNNING"
        self.state = state
        self.orb.state = state
        self.status.setStringValue_(text)
        color = COLORS[state]
        self.status.setTextColor_(rgba(color, 0.95))

    def frame(self):
        self.orb.t = time.time() - self.t0
        if self.panel.isVisible():
            self.orb.setNeedsDisplay_(True)

    def add(self, who, text):
        para = NSMutableParagraphStyle.alloc().init()
        para.setParagraphSpacing_(9)
        mine = who == "you"
        mono_s = NSFont.fontWithName_size_("Menlo", 10) or NSFont.systemFontOfSize_(10)
        label = NSMutableAttributedString.alloc().initWithString_("YOU".ljust(8) if mine else NAME.upper()[:7].ljust(8))
        label.addAttributes_range_({
            NSFontAttributeName: mono_s,
            NSForegroundColorAttributeName: rgba(ACCENT if not mine else (0.6, 0.7, 0.8),
                                                 0.9 if not mine else 0.7),
            NSParagraphStyleAttributeName: para}, (0, label.length()))
        body = NSMutableAttributedString.alloc().initWithString_(text + "\n")
        body.addAttributes_range_({
            NSFontAttributeName: NSFont.systemFontOfSize_(14),
            NSForegroundColorAttributeName: (rgba((0.62, 0.74, 0.86), 0.95) if mine
                                             else NSColor.colorWithCalibratedRed_green_blue_alpha_(
                                                 0.88, 0.98, 1.0, 1.0)),
            NSParagraphStyleAttributeName: para}, (0, body.length()))
        st = self.tv.textStorage()
        st.appendAttributedString_(label)
        st.appendAttributedString_(body)
        self.tv.scrollRangeToVisible_((st.length(), 0))

    def clear(self):
        self.tv.textStorage().setAttributedString_(NSMutableAttributedString.alloc().initWithString_(""))

    def handle(self, e):
        k, t = e.get("k"), e.get("t", "")
        self.last_event = time.time()
        dbg(f"event {k} {t[:40]!r}")
        if k == "reset":
            self.clear()
            self.ended = True
            self.hide_at = None
            self.panel.orderOut_(None)
            return
        if k == "jobs":
            try:
                self.jobs = int(t)
            except ValueError:
                return
            if self.ended and not self.panel.isVisible() and self.jobs and STAY_WHILE_WORKING:
                self.clear()
                self.panel.orderFrontRegardless()
            if self.ended:
                self.set_status("Standby")
                if self.jobs and STAY_WHILE_WORKING:
                    self.hide_at = None
                elif not self.jobs and self.panel.isVisible():
                    self.hide_at = time.time() + HIDE_AFTER
            return
        if k == "wake":
            self.ended = False
            self.clear()
            self.hide_at = None
            self.set_status("Listening…")
            self.panel.orderFrontRegardless()
        elif k == "listen":
            self.set_status("Listening…")
        elif k == "you":
            self.add("you", t)
            self.set_status("Thinking…")
        elif k == "think":
            self.set_status("Thinking…")
        elif k == "assistant":
            if not self.panel.isVisible():
                self.clear()
                self.panel.orderFrontRegardless()
            self.hide_at = None
            self.add("assistant", t)
            self.set_status("Speaking…")
        elif k == "end":
            self.ended = True
            self.set_status("Standby")
            self.hide_at = (None if (self.jobs and STAY_WHILE_WORKING)
                            else time.time() + HIDE_AFTER)

    def tick(self):
        self.ticks += 1
        if self.ticks % 20 == 0 and not alive(HUB_PID):
            NSApplication.sharedApplication().terminate_(None)
        if self.hide_at and time.time() >= self.hide_at:
            self.panel.orderOut_(None)
            self.hide_at = None
            dbg("hidden (conversation ended)")
        elif (self.panel.isVisible() and time.time() - self.last_event > IDLE_HIDE
              and not (self.jobs and STAY_WHILE_WORKING)):
            self.panel.orderOut_(None)
            self.ended = True
            dbg("hidden (idle failsafe)")
        try:
            size = os.path.getsize(EVENTS)
        except OSError:
            return
        if size < self.offset:             # file was truncated (hub restarted)
            self.offset = 0
            self.clear()
            self.panel.orderOut_(None)
        if size == self.offset:
            return
        with open(EVENTS, "rb") as f:
            f.seek(self.offset)
            chunk = f.read()
        nl = chunk.rfind(b"\n")
        if nl < 0:
            return
        self.offset += nl + 1
        for line in chunk[:nl].decode("utf-8", "replace").splitlines():
            try:
                self.handle(json.loads(line))
            except Exception:
                pass


class Controller(NSObject):
    """Thin ObjC shim: the timer calls tick:, everything else is plain Python."""

    def initWithView_(self, view):
        self = objc.super(Controller, self).init()
        self.view = view
        return self

    def tick_(self, _timer):
        self.view.tick()

    def frame_(self, _timer):
        self.view.frame()


def main():
    C.ensure_dirs()
    lock = C.private_open(LOCK, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return                              # another panel is already running
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)   # no Dock icon
    ctl = Controller.alloc().initWithView_(View())
    NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        0.15, ctl, b"tick:", None, True)
    NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        1 / 30, ctl, b"frame:", None, True)
    app.run()


if __name__ == "__main__":
    main()
