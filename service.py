"""Run the hub as a user-level macOS LaunchAgent: install, uninstall, status.

Used by `hub.py --install-service | --uninstall-service | --service-status`. Only standard
library, so it works before anything else is set up. It never uses sudo, never asks a question,
and prints exactly what it did. With dry_run=True it prints the plist and the launchctl commands
and changes nothing.
"""
import fcntl
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
from xml.sax.saxutils import escape

import config as C

LABEL = "com.jarvis-voice-hub"
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "launchd", LABEL + ".plist.template")
HOME = os.path.expanduser("~")
PLIST = os.path.join(HOME, "Library", "LaunchAgents", LABEL + ".plist")
OUT_FILE = os.path.join(C.STATE_DIR, "hub.out")


def domain():
    return f"gui/{os.getuid()}"


def target():
    return f"{domain()}/{LABEL}"


def service_path(claude_dir=None):
    """PATH for the service: the claude CLI must be found (launchd's default PATH is tiny)."""
    dirs = [os.path.join(HOME, ".local", "bin"), "/opt/homebrew/bin", "/usr/local/bin"]
    if claude_dir:
        dirs.append(claude_dir)
    dirs += ["/usr/bin", "/bin", "/usr/sbin", "/sbin"]
    seen = []
    for d in dirs:
        if d not in seen:
            seen.append(d)
    return ":".join(seen)


def venv_python():
    p = os.path.join(HERE, ".venv", "bin", "python")
    return p if os.path.exists(p) else sys.executable   # not resolved: keeps the venv's packages


def render_plist(python=None, claude_dir=None):
    with open(TEMPLATE, encoding="utf-8") as f:
        text = f.read()
    extra = ""
    if os.environ.get("VOICE_HUB_HOME"):
        extra = (f"\n    <key>VOICE_HUB_HOME</key><string>{escape(C.HOME_DIR)}</string>")
    values = {
        "__PYTHON__": python or venv_python(),
        "__REPO_DIR__": HERE,
        "__HOME__": HOME,
        "__PATH__": service_path(claude_dir),
        "__STATE_DIR__": C.STATE_DIR,
    }
    for k, v in values.items():
        text = text.replace(k, escape(v))
    text = text.replace("__EXTRA_ENV__", extra)
    plistlib.loads(text.encode("utf-8"))          # must parse
    return text


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def is_loaded():
    return _run(["launchctl", "print", target()]).returncode == 0


def _hub_running_elsewhere():
    """True if some hub (for example one in a Terminal) already holds the single-instance lock."""
    if not os.path.exists(C.HUB_LOCK):
        return False
    try:
        fd = os.open(C.HUB_LOCK, os.O_RDONLY)
    except OSError:
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return False
    except OSError:
        return True
    finally:
        os.close(fd)


def _refuse_root():
    if os.geteuid() == 0:
        print("Refusing to run as root: the service must belong to your own user. "
              "Run this without sudo.", file=sys.stderr)
        return True
    return False


def install(dry_run=False, plist_out=None):
    if _refuse_root():
        return 2
    if plist_out is None and sys.platform != "darwin":
        print("The service is for macOS only.", file=sys.stderr)
        return 2
    python = venv_python()
    if not os.path.exists(python):
        print(f"Python not found: {python}. Run ./setup.sh first.", file=sys.stderr)
        return 1
    claude = shutil.which("claude")
    if not claude:
        print("WARNING: `claude` is not on this shell's PATH; the service PATH will not find it "
              "unless it lives in ~/.local/bin, /opt/homebrew/bin or /usr/local/bin.")
    text = render_plist(python, os.path.dirname(claude) if claude else None)

    if plist_out:                                  # hidden test option: write only here
        with open(plist_out, "w", encoding="utf-8") as f:
            f.write(text)
        r = _run(["plutil", "-lint", plist_out]) if shutil.which("plutil") else None
        print(f"wrote {plist_out} (nothing loaded)")
        print(r.stdout.strip() if r else "plutil not available; skipped lint")
        return 0 if (r is None or r.returncode == 0) else 1

    cmds = [["plutil", "-lint", PLIST],
            ["launchctl", "bootout", target()],    # only if already loaded
            ["launchctl", "bootstrap", domain(), PLIST]]
    if dry_run:
        print(f"DRY RUN: nothing is written or run. Would write {PLIST} (mode 0644):\n")
        print(text)
        print(f"Would create {OUT_FILE} (mode 0600) and the state dir if missing.")
        print("Would run:")
        for c in cmds:
            print("  " + " ".join(c) + ("   # only if already loaded" if c[1] == "bootout" else ""))
        if _hub_running_elsewhere():
            print("NOTE: a hub is running right now; stop it first or the service will exit.")
        return 0

    if _hub_running_elsewhere() and not is_loaded():
        print("A hub is already running (probably in a Terminal). Stop it first (Ctrl-C there), "
              "then run --install-service again; two hubs would fight for the microphone.",
              file=sys.stderr)
        return 1
    C.ensure_dirs()
    C.private_open(OUT_FILE, "a").close()
    os.makedirs(os.path.dirname(PLIST), exist_ok=True)
    with open(PLIST, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(PLIST, 0o644)
    print(f"wrote {PLIST}")
    r = _run(["plutil", "-lint", PLIST])
    print(r.stdout.strip() or r.stderr.strip())
    if r.returncode != 0:
        print("plist failed validation; not loading it.", file=sys.stderr)
        return 1
    if is_loaded():
        _run(["launchctl", "bootout", target()])
        print(f"was already loaded: ran launchctl bootout {target()}")
    r = _run(["launchctl", "bootstrap", domain(), PLIST])
    if r.returncode != 0:
        print(f"launchctl bootstrap failed: {r.stderr.strip() or r.stdout.strip()}", file=sys.stderr)
        return 1
    print(f"ran launchctl bootstrap {domain()} {PLIST}")
    print(f"""
The hub now runs in the background, starts at every login and restarts if it crashes.
 - First start: macOS asks whether "python" (or "Python") may access the microphone. Click Allow.
   If you missed it: System Settings > Privacy & Security > Microphone, switch Python on, then
   run ./restart.sh or: .venv/bin/python hub.py --install-service
 - Watch the log : tail -f {C.LOG}
 - Status        : .venv/bin/python hub.py --service-status
 - Stop + remove : .venv/bin/python hub.py --uninstall-service""")
    return 0


def uninstall(dry_run=False):
    if _refuse_root():
        return 2
    cmd = ["launchctl", "bootout", target()]
    if dry_run:
        print("DRY RUN: nothing is run or removed. Would run (if loaded):")
        print("  " + " ".join(cmd))
        print(f"Would delete {PLIST}")
        return 0
    if is_loaded():
        r = _run(cmd)
        print(f"ran {' '.join(cmd)}" + ("" if r.returncode == 0 else f" (failed: {r.stderr.strip()})"))
    else:
        print("service was not loaded")
    if os.path.exists(PLIST):
        os.remove(PLIST)
        print(f"removed {PLIST}")
    else:
        print(f"{PLIST} did not exist")
    print(f"Logs and models stay in {C.HOME_DIR}; the hub no longer runs in the background.")
    return 0


def _tail(path, n):
    try:
        with open(path, "r", errors="replace") as f:
            return f.read().splitlines()[-n:]
    except OSError:
        return None


def parse_print(out):
    """Pull state, pid and last exit status out of `launchctl print` text."""
    info = {}
    for raw in out.splitlines():
        line = raw.strip()
        for key, name in (("state = ", "state"), ("pid = ", "pid"),
                          ("last exit code = ", "last_exit"), ("runs = ", "runs")):
            if line.startswith(key) and name not in info:
                info[name] = line[len(key):]
    return info


def status():
    if not os.path.exists(PLIST):
        print(f"service: not installed ({PLIST} does not exist)")
        print("install with: .venv/bin/python hub.py --install-service")
        return 0
    print(f"service: installed ({PLIST})")
    if sys.platform != "darwin" or not shutil.which("launchctl"):
        print("launchctl not available; cannot read the loaded state")
        return 0
    r = _run(["launchctl", "print", target()])
    if r.returncode != 0:
        print("loaded : no (plist exists but is not loaded; run --install-service)")
    else:
        info = parse_print(r.stdout)
        print("loaded : yes")
        print(f"state  : {info.get('state', 'unknown')}")
        print(f"pid    : {info.get('pid', 'none (not running right now)')}")
        print(f"last exit status: {info.get('last_exit', 'unknown')}   runs: {info.get('runs', '?')}")
    for path, n in ((C.LOG, 10), (OUT_FILE, 5)):
        lines = _tail(path, n)
        print(f"--- last {n} lines of {path}" + ("" if lines is not None else " (no file yet)"))
        for ln in lines or []:
            print(ln)
    return 0
