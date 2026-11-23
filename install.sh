#!/usr/bin/env bash
# jarvis-voice-hub bootstrap installer for a Mac that has nothing installed.
#
# Read it first, then run it:
#   curl -fsSLO https://raw.githubusercontent.com/matanjac/jarvis-voice-hub/main/install.sh
#   less install.sh && bash install.sh --dry-run && bash install.sh
# (The easier way is to let Claude Code do the install: see the top of README.md.)
#
# Everything lives inside main(), which is called on the very last line. If the download is cut
# off, bash hits a syntax error before running anything, so a truncated script cannot half-run.
set -euo pipefail

main() {
  local REPO_URL="https://github.com/matanjac/jarvis-voice-hub.git"
  local TARGET="$HOME/jarvis-voice-hub"
  local REF="${JARVIS_REF:-main}"
  local CONFIG_DIR="$HOME/.config/jarvis-voice-hub"
  local BREW_INSTALL_URL="https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"
  local ASSUME_YES=0 DRY_RUN=0

  usage() {
    cat <<'EOF'
jarvis-voice-hub installer (Apple Silicon Mac, macOS 14+)

Usage: install.sh [-y|--yes] [--dry-run] [-h|--help]
  -y, --yes   do not ask "Continue?" (use this for unattended runs)
  --dry-run   print every step it would take and change nothing (works on any machine)
  -h, --help  this text

Run it from a downloaded file (read it first); flags go after the file name, e.g.  bash install.sh --dry-run

Environment:
  JARVIS_REF  branch, tag or commit to install (default: main), e.g. JARVIS_REF=v0.1.0

It never uses sudo itself. Homebrew's own installer may ask for your password.
EOF
  }

  local arg
  for arg in "$@"; do
    case "$arg" in
      -y|--yes) ASSUME_YES=1 ;;
      --dry-run) DRY_RUN=1 ;;
      -h|--help) usage; return 0 ;;
      *) echo "Unknown option: $arg" >&2; usage >&2; return 2 ;;
    esac
  done

  say()  { printf '%s\n' "$*"; }
  step() { printf '\n== %s\n' "$*"; }
  warn() { printf 'warning: %s\n' "$*" >&2; }
  die()  { printf 'error: %s\n' "$*" >&2; exit 1; }
  # run CMD ARGS...: execute it, or only print it in dry-run. Children never read the script pipe.
  run() {
    if [ "$DRY_RUN" = 1 ]; then
      printf '   [dry-run] would run:'; printf ' %q' "$@"; printf '\n'
    else
      "$@" </dev/null
    fi
  }

  # ---- (1) platform and user checks ------------------------------------------------------
  local os arch macver macmajor
  os="$(uname -s)"; arch="$(uname -m)"
  if [ "$DRY_RUN" = 1 ]; then
    say "DRY RUN: nothing will be changed. Checks below are read-only."
    [ "$os" = "Darwin" ] || warn "this machine is $os; the real install only runs on macOS"
    [ "$arch" = "arm64" ] || warn "this machine is $arch; the real install needs Apple Silicon (arm64)"
    [ "$(id -u)" -ne 0 ] || warn "running as root; the real install refuses to"
  else
    [ "$os" = "Darwin" ] || die "this installer is for macOS only (found $os)."
    [ "$arch" = "arm64" ] || die "Apple Silicon (M1 or newer) is required: transcription uses MLX, which does not run on Intel Macs (found $arch)."
    [ "$(id -u)" -ne 0 ] || die "do not run this as root or with sudo. Run it as your normal user; it asks for your password only where macOS or Homebrew need it."
  fi
  if [ "$os" = "Darwin" ]; then
    macver="$(sw_vers -productVersion 2>/dev/null || echo 0)"
    macmajor="${macver%%.*}"
    case "$macmajor" in ''|*[!0-9]*) macmajor=0 ;; esac
    if [ "$macmajor" -lt 14 ]; then
      warn "macOS 14 or newer is expected (found $macver); continuing anyway"
    fi
  fi
  case "$REF" in
    ''|-*|*[!A-Za-z0-9._/-]*) die "JARVIS_REF '$REF' is not a plain branch, tag or commit name." ;;
  esac

  # Apple Silicon Homebrew lives here; set PATH by hand (no eval of brew shellenv).
  local BREW_BIN="/opt/homebrew/bin/brew"
  export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"

  # ---- (2) say what will happen, ask ------------------------------------------------------
  cat <<EOF

jarvis-voice-hub installer
This will, on this Mac:
  1. Make sure git is available (installs the Xcode Command Line Tools if missing).
       -> macOS shows a dialog: click "Install" and accept the licence. It can take several minutes.
  2. Make sure Homebrew is installed (runs the official installer from https://brew.sh if missing).
       -> it may ask for your Mac password (it uses sudo itself), and shows what it will do first.
  3. Install Python 3.12 with Homebrew if python3.12 is missing.
  4. Clone $REPO_URL
       into $TARGET (ref: $REF). If the folder exists it is updated with git pull --ff-only.
  5. Run ./setup.sh (Python venv + packages, ~350 MB speech model, tiny C mic helpers under
       $CONFIG_DIR), then 'hub.py --check'. About 2.5 GB of disk in total.
  6. Check whether Claude Code is installed and logged in (it will NOT install it for you).
It does not start the hub, does not change your shell profile, and never uses sudo itself.

EOF
  if [ "$ASSUME_YES" = 1 ] || [ "$DRY_RUN" = 1 ]; then
    [ "$DRY_RUN" = 1 ] || say "(-y given: not asking)"
  else
    local ans=""
    if ! { : </dev/tty; } 2>/dev/null; then
      die "no terminal to ask for confirmation. Re-run with -y:  bash install.sh -y"
    fi
    printf 'Continue? [y/N] ' >/dev/tty
    read -r ans </dev/tty || ans=""
    case "$ans" in y|Y|yes|YES|Yes) ;; *) say "Cancelled. Nothing was changed."; return 0 ;; esac
  fi

  # ---- (3) git, Homebrew, Python ---------------------------------------------------------
  step "Step 1/6: git (Xcode Command Line Tools)"
  clt_ready() {
    local p
    p="$(xcode-select -p 2>/dev/null)" || return 1
    [ -x "$p/usr/bin/git" ] && [ -x "$p/usr/bin/clang" ]
  }
  if clt_ready; then
    say "   Command Line Tools present: $(git --version 2>/dev/null || echo git)"
  elif [ "$DRY_RUN" = 1 ]; then
    say "   Command Line Tools missing."
    run xcode-select --install
    say "   [dry-run] would then wait until the tools exist (you click Install in the macOS dialog)."
  else
    say "   Command Line Tools missing. A macOS dialog will open now."
    say "   >>> Click \"Install\" in that dialog and accept the licence. This script waits. <<<"
    xcode-select --install </dev/null >/dev/null 2>&1 || true
    local waited=0
    until clt_ready; do
      if [ "$waited" -ge 3600 ]; then
        die "gave up waiting for the Command Line Tools after 60 minutes. Finish the macOS install, then re-run this script."
      fi
      if [ $((waited % 60)) -eq 0 ]; then
        say "   still waiting for the Command Line Tools install to finish (click Install in the dialog if you have not)..."
      fi
      sleep 5; waited=$((waited + 5))
    done
    say "   Command Line Tools installed."
  fi

  step "Step 2/6: Homebrew"
  if [ -x "$BREW_BIN" ] || command -v brew >/dev/null 2>&1; then
    say "   Homebrew present."
  elif [ "$DRY_RUN" = 1 ]; then
    say "   Homebrew missing. [dry-run] would run the official installer from https://brew.sh:"
    say "   /bin/bash -c \"\$(curl -fsSL $BREW_INSTALL_URL)\""
  else
    say "   Homebrew missing. Running the official installer from https://brew.sh (it may ask for your password)."
    # Exactly the command published on https://brew.sh. stdin comes from the terminal so the
    # installer can prompt, and never reads this script from the pipe.
    /bin/bash -c "$(curl -fsSL "$BREW_INSTALL_URL")" </dev/tty
    [ -x "$BREW_BIN" ] || die "Homebrew installer finished but $BREW_BIN was not found."
  fi

  step "Step 3/6: Python 3.12"
  if command -v python3.12 >/dev/null 2>&1; then
    say "   python3.12 present: $(python3.12 --version 2>&1)"
  else
    say "   python3.12 missing."
    run brew install python@3.12
    if [ "$DRY_RUN" = 0 ]; then
      command -v python3.12 >/dev/null 2>&1 || die "python3.12 still not on PATH after brew install."
    fi
  fi

  # ---- (4) clone or update ---------------------------------------------------------------
  step "Step 4/6: the code ($REPO_URL @ $REF -> $TARGET)"
  # If this script sits next to setup.sh and hub.py (a downloaded zip or a clone), use that folder.
  LOCAL_COPY=0
  if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    _d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "$_d/setup.sh" ] && [ -f "$_d/hub.py" ]; then TARGET="$_d"; LOCAL_COPY=1; fi
  fi
  if [ "$LOCAL_COPY" = 1 ]; then
    say "   Running from a local copy at $TARGET: skipping the download."
  elif [ -e "$TARGET" ] && [ ! -d "$TARGET/.git" ]; then
    die "$TARGET exists but is not a git checkout. Move it aside and re-run."
  elif [ -d "$TARGET/.git" ]; then
    say "   $TARGET already exists: updating."
    run git -C "$TARGET" fetch --tags origin
    run git -C "$TARGET" checkout "$REF"
    if [ "$DRY_RUN" = 1 ]; then
      say "   [dry-run] would run 'git pull --ff-only origin $REF' if $REF is a branch."
    elif git -C "$TARGET" symbolic-ref -q HEAD >/dev/null; then
      git -C "$TARGET" pull --ff-only origin "$REF" </dev/null
    else
      say "   $REF is a tag or commit (detached HEAD); nothing to pull."
    fi
  else
    run git clone "$REPO_URL" "$TARGET"
    run git -C "$TARGET" checkout "$REF"
  fi

  # ---- (5) setup and check ---------------------------------------------------------------
  step "Step 5/6: setup.sh and hub.py --check"
  local check_rc=0 check_out=""
  if [ "$DRY_RUN" = 1 ]; then
    say "   [dry-run] would run: cd $TARGET && ./setup.sh"
    say "   [dry-run] would run: .venv/bin/python hub.py --check"
  else
    cd "$TARGET"
    ./setup.sh </dev/null
    check_out="$(.venv/bin/python hub.py --check </dev/null 2>&1)" || check_rc=$?
    printf '%s\n' "$check_out"
    echo
    if [ "$check_rc" -eq 0 ] && ! printf '%s' "$check_out" | grep -q 'MISSING'; then
      say "Result: install check passed."
    else
      say "Result: the check reported problems (exit code $check_rc). Lines marked [MISSING] above say what is absent;"
      say "the troubleshooting table in $TARGET/README.md covers the common ones. A missing Claude Code CLI is fixed in the next step."
    fi
  fi

  # ---- (6) Claude Code -------------------------------------------------------------------
  step "Step 6/6: Claude Code (the brain)"
  if command -v claude >/dev/null 2>&1; then
    say "   claude found: $(claude --version 2>/dev/null || echo installed)"
    if [ "$DRY_RUN" = 1 ]; then
      say "   [dry-run] would check login with 'claude auth status'."
    elif claude auth status </dev/null >/dev/null 2>&1; then
      say "   Claude Code is logged in."
    else
      say "   Could not confirm that Claude Code is logged in. Run  claude  once in a terminal and complete the sign-in."
    fi
  else
    say "   Claude Code is not installed. This script does not install it for you. To install and log in:"
    say "     1. curl -fsSL https://claude.ai/install.sh | bash      (official installer; read it first if you like)"
    say "     2. open a new terminal window, run:  claude"
    say "     3. complete the sign-in in your browser, then type /exit"
  fi

  # ---- final instructions ----------------------------------------------------------------
  local term_name
  case "${TERM_PROGRAM:-}" in
    Apple_Terminal) term_name="Terminal" ;;
    iTerm.app) term_name="iTerm" ;;
    ghostty) term_name="Ghostty" ;;
    vscode) term_name="Visual Studio Code" ;;
    '') term_name="your terminal app" ;;
    *) term_name="$TERM_PROGRAM" ;;
  esac
  cat <<EOF

================================================================
$( [ "$DRY_RUN" = 1 ] && echo "Dry run finished. Nothing was changed." || echo "Install finished." )

Next steps
  1. Microphone permission. Start the hub from $term_name. The first time, macOS asks whether
     $term_name may use the microphone: click Allow. If you clicked Don't Allow, or no dialog
     appeared, open System Settings > Privacy & Security > Microphone, switch $term_name on,
     then quit and reopen $term_name.
  2. Run the hub in the foreground (Ctrl-C stops it):
       cd "$TARGET" && .venv/bin/python hub.py
  3. Say "hey jarvis", wait for the Tink sound, then ask "what time is it" and "what is in this folder".
  4. The floating panel appears bottom right: LISTENING, then THINKING with a seconds timer,
     your words with a "Heard clearly" tag, then SPEAKING while the reply is read out. After a few
     seconds of silence it plays a Bottle sound and hides. The first wake can pause a while while
     the ~1.6 GB Whisper model downloads once.
  Safe defaults are on (read-only "plan" mode, brain isolation). Read "Security" in
  $TARGET/README.md before changing them.

Uninstall (these commands are only printed, never run by this script; check the paths first)
  # stop the hub with Ctrl-C, then:
  rm -r "$CONFIG_DIR"
  rm -r "$TARGET"
  # optional: switch $term_name off under System Settings > Privacy & Security > Microphone.
  # Homebrew, Python and the Command Line Tools stay installed; remove them separately if you want.
================================================================
EOF
}

main "$@"
