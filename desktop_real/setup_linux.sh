#!/usr/bin/env bash
# setup_linux.sh - install and start a REAL X11 desktop for the Ornith agent.
#
# Stack: Xvfb :99 (1280x800x24) + openbox + native apps
#        (xterm, gedit, pcmanfm, galculator, LibreOffice Writer).
# Tools: xdotool, wmctrl, xclip, ImageMagick, x11-utils, x11-apps.
#
# Tested target: Ubuntu 22.04 / 24.04 and Debian 12 (apt). Idempotent:
# running it twice does not reinstall or restart a healthy desktop.
#
# Usage:
#   bash setup_linux.sh                 # full install + start
#   bash setup_linux.sh --minimal       # core + xterm only (fast proof)
#   bash setup_linux.sh --skip-office   # no LibreOffice
#   bash setup_linux.sh --check         # report readiness, change nothing
#   bash setup_linux.sh --stop          # stop apps, WM and Xvfb
#   bash setup_linux.sh --vnc           # also start x11vnc on localhost:5900
#
# Logs: /tmp/ornith_desktop_setup.log, /tmp/ornith_xvfb.log,
#       /tmp/ornith_openbox.log, /tmp/ornith_x11vnc.log
#
# ASCII-only source on purpose (Windows cp1252 lesson).

set -u
set -o pipefail

DISPLAY_NUM="${DISPLAY_NUM:-:99}"
SCREEN_W="${SCREEN_W:-1280}"
SCREEN_H="${SCREEN_H:-800}"
SCREEN_D="${SCREEN_D:-24}"
LOG="${LOG:-/tmp/ornith_desktop_setup.log}"
VNC="${VNC:-0}"
MODE="full"       # full | nooffice | minimal
ACTION="setup"    # setup | check | stop

CORE_PKGS=(xvfb x11-utils x11-apps xdotool wmctrl xclip openbox dbus-x11
           imagemagick scrot poppler-utils)
APP_PKGS=(xterm gedit pcmanfm galculator fonts-dejavu-core fonts-liberation)
OFFICE_PKGS=(libreoffice-writer libreoffice-gtk3)
VNC_PKGS=(x11vnc)

usage() {
    cat <<'EOF'
Real X11 desktop setup (Ubuntu/Debian)

  bash setup_linux.sh [options]

Options:
  --check          report packages/display/WM and exit (no changes)
  --stop           stop apps, openbox, x11vnc and Xvfb for this display
  --minimal        install core tools + xterm only (fast proof)
  --skip-office    install apps but not LibreOffice/poppler
  --vnc            install and start x11vnc on localhost:5900
  --no-vnc         do not start x11vnc
  --display :99    X display number (default :99)
  --width 1280     screen width  (default 1280)
  --height 800     screen height (default 800)
  --depth 24       screen depth  (default 24)
  -h, --help       this help

Environment overrides: DISPLAY_NUM, SCREEN_W, SCREEN_H, SCREEN_D, LOG, VNC.
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --check) ACTION="check" ;;
        --stop) ACTION="stop" ;;
        --vnc) VNC=1 ;;
        --no-vnc) VNC=0 ;;
        --minimal) MODE="minimal" ;;
        --skip-office) MODE="nooffice" ;;
        --display) DISPLAY_NUM="${2:-}"; shift ;;
        --display=*) DISPLAY_NUM="${1#*=}" ;;
        --width) SCREEN_W="${2:-}"; shift ;;
        --width=*) SCREEN_W="${1#*=}" ;;
        --height) SCREEN_H="${2:-}"; shift ;;
        --height=*) SCREEN_H="${1#*=}" ;;
        --depth) SCREEN_D="${2:-}"; shift ;;
        --depth=*) SCREEN_D="${1#*=}" ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage; exit 2 ;;
    esac
    shift
done

case "$DISPLAY_NUM" in
    :*) ;;
    *) DISPLAY_NUM=":$DISPLAY_NUM" ;;
esac
XNUM="${DISPLAY_NUM#:}"
XNUM="${XNUM%%.*}"

mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
# Keep the user informed and keep a log at the same time.
exec > >(tee -a "$LOG") 2>&1

log()  { printf '%s [setup] %s\n' "$(date +%H:%M:%S)" "$*"; }
warn() { printf '%s [setup] WARN: %s\n' "$(date +%H:%M:%S)" "$*"; }
die()  { printf '%s [setup] FAIL: %s\n' "$(date +%H:%M:%S)" "$*"; exit 1; }

cmd_ok() { command -v "$1" >/dev/null 2>&1; }
any_cmd() {
    local name
    for name in "$@"; do
        if cmd_ok "$name"; then
            return 0
        fi
    done
    return 1
}

if [ "$(id -u)" -eq 0 ]; then
    SUDO=()
elif cmd_ok sudo; then
    SUDO=(sudo)
else
    SUDO=()
fi

run_root() {
    "${SUDO[@]}" "$@"
}

need_root() {
    if [ "$(id -u)" -eq 0 ]; then
        return 0
    fi
    if [ "${#SUDO[@]}" -eq 0 ]; then
        die "need root or sudo to install packages"
    fi
    if ! sudo -n true 2>/dev/null; then
        die "sudo needs a password; run as root or enable passwordless sudo"
    fi
}

display_ready() {
    xdpyinfo -display "$DISPLAY_NUM" >/dev/null 2>&1
}

xvfb_running() {
    pgrep -f "(^|/)Xvfb[ ]+${DISPLAY_NUM}([ ]|$)" >/dev/null 2>&1
}

pid_has_display() {
    local pid="$1"
    local disp="$2"
    [ -r "/proc/$pid/environ" ] || return 1
    tr '\0' '\n' < "/proc/$pid/environ" | grep -qx "DISPLAY=$disp"
}

stop_process() {
    local pid="$1"
    kill "$pid" 2>/dev/null || true
    local i
    for i in 1 2 3 4 5 6 7 8 9 10; do
        if ! kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
        sleep 0.2
    done
    kill -9 "$pid" 2>/dev/null || true
}

core_ok() {
    cmd_ok Xvfb && cmd_ok xdotool && cmd_ok wmctrl && cmd_ok xclip \
        && cmd_ok openbox && any_cmd import xwd && cmd_ok xdpyinfo
}

apps_ok() {
    cmd_ok xterm && cmd_ok gedit && any_cmd pcmanfm thunar \
        && cmd_ok galculator
}

office_ok() {
    any_cmd libreoffice soffice && cmd_ok pdftotext
}

install_group() {
    local label="$1"
    shift
    if [ "$#" -eq 0 ]; then
        return 0
    fi
    log "installing $label: $*"
    if run_root env DEBIAN_FRONTEND=noninteractive timeout 1200 \
            apt-get install -y --no-install-recommends "$@"; then
        log "$label: OK"
        return 0
    fi
    warn "group install failed; retrying one package at a time"
    local pkg
    for pkg in "$@"; do
        if ! run_root env DEBIAN_FRONTEND=noninteractive timeout 600 \
                apt-get install -y --no-install-recommends "$pkg"; then
            warn "package failed: $pkg"
        fi
    done
}

install_needed() {
    local need=0
    if ! core_ok; then
        need=1
    fi
    if [ "$MODE" = "minimal" ]; then
        if ! cmd_ok xterm; then
            need=1
        fi
    else
        if ! apps_ok; then
            need=1
        fi
    fi
    if [ "$MODE" = "full" ] && ! office_ok; then
        need=1
    fi
    if [ "$VNC" -eq 1 ] && ! cmd_ok x11vnc; then
        need=1
    fi
    if [ "$need" -eq 0 ]; then
        log "all required commands are present; skipping apt"
        return 0
    fi
    need_root
    if ! cmd_ok apt-get; then
        die "apt-get not found (this script supports Ubuntu/Debian only)"
    fi
    log "apt-get update"
    if ! run_root env DEBIAN_FRONTEND=noninteractive timeout 300 \
            apt-get update -qq; then
        warn "apt-get update failed; continuing with cached indexes"
    fi
    install_group "core" "${CORE_PKGS[@]}"
    if [ "$MODE" = "minimal" ]; then
        install_group "xterm" xterm
    else
        install_group "apps" "${APP_PKGS[@]}"
    fi
    if [ "$MODE" = "full" ]; then
        install_group "office" "${OFFICE_PKGS[@]}"
        local avail
        avail=$(df -Pk / 2>/dev/null | awk 'NR==2 {print $4}')
        if [ -n "$avail" ] && [ "$avail" -lt 2000000 ]; then
            warn "less than 2 GB free on /; LibreOffice may fail to install"
        fi
    fi
    if [ "$VNC" -eq 1 ]; then
        install_group "vnc" "${VNC_PKGS[@]}"
    fi
}

MISSING=0

check_one() {
    local label="$1"
    shift
    local name found=""
    for name in "$@"; do
        if cmd_ok "$name"; then
            found="$(command -v "$name" 2>/dev/null || true)"
            break
        fi
    done
    if [ -n "$found" ]; then
        log "  [OK]   $label ($found)"
    else
        log "  [MISS] $label (need: $*)"
        MISSING=$((MISSING + 1))
    fi
}

do_check() {
    MISSING=0
    log "check: mode=$MODE display=$DISPLAY_NUM screen=${SCREEN_W}x${SCREEN_H}x${SCREEN_D}"
    log "core packages: ${CORE_PKGS[*]}"
    if [ "$MODE" != "minimal" ]; then
        log "app packages: ${APP_PKGS[*]}"
    fi
    if [ "$MODE" = "full" ]; then
        log "office packages: ${OFFICE_PKGS[*]}"
    fi
    if [ "$VNC" -eq 1 ]; then
        log "vnc packages: ${VNC_PKGS[*]}"
    fi
    log "commands:"
    check_one "Xvfb" Xvfb
    check_one "xdotool" xdotool
    check_one "wmctrl" wmctrl
    check_one "xclip" xclip
    check_one "openbox" openbox
    check_one "screenshot (import|xwd)" import xwd
    check_one "xdpyinfo" xdpyinfo
    if [ "$MODE" = "minimal" ]; then
        check_one "xterm" xterm
    else
        check_one "xterm" xterm
        check_one "gedit" gedit
        check_one "file manager (pcmanfm|thunar)" pcmanfm thunar
        check_one "galculator" galculator
    fi
    if [ "$MODE" = "full" ]; then
        check_one "LibreOffice (libreoffice|soffice)" libreoffice soffice
        check_one "pdftotext" pdftotext
    fi
    if [ "$VNC" -eq 1 ]; then
        check_one "x11vnc" x11vnc
    fi

    if display_ready; then
        local dims
        dims=$(xdpyinfo -display "$DISPLAY_NUM" 2>/dev/null \
            | awk '/dimensions:/ {print $2; exit}')
        log "  [OK]   display $DISPLAY_NUM running (${dims:-unknown})"
    else
        log "  [MISS] display $DISPLAY_NUM not running"
        MISSING=$((MISSING + 1))
    fi
    if DISPLAY="$DISPLAY_NUM" wmctrl -m >/dev/null 2>&1; then
        local wm
        wm=$(DISPLAY="$DISPLAY_NUM" wmctrl -m 2>/dev/null \
            | awk -F': ' '/^Name:/ {print $2; exit}')
        log "  [OK]   window manager: ${wm:-unknown}"
    else
        log "  [MISS] window manager (openbox) not running"
        MISSING=$((MISSING + 1))
    fi

    if [ "$MISSING" -eq 0 ]; then
        log "READY: desktop is usable"
        return 0
    fi
    log "NOT READY: $MISSING missing item(s)"
    return 1
}

start_xvfb() {
    if display_ready; then
        log "display $DISPLAY_NUM already running"
        return 0
    fi
    if ! cmd_ok Xvfb; then
        die "Xvfb is not installed"
    fi
    if xvfb_running; then
        log "Xvfb process exists but display is not ready; waiting"
        local i
        for i in $(seq 1 30); do
            if display_ready; then
                return 0
            fi
            sleep 0.2
        done
        warn "stale Xvfb process; killing it"
        pkill -f "(^|/)Xvfb[ ]+${DISPLAY_NUM}([ ]|$)" 2>/dev/null || true
        sleep 0.5
    fi
    rm -f "/tmp/.X${XNUM}-lock" 2>/dev/null || true
    nohup Xvfb "$DISPLAY_NUM" -screen 0 \
        "${SCREEN_W}x${SCREEN_H}x${SCREEN_D}" -ac -nolisten tcp -dpi 96 \
        -noreset >/tmp/ornith_xvfb.log 2>&1 &
    local i
    for i in $(seq 1 50); do
        if display_ready; then
            break
        fi
        sleep 0.2
    done
    if ! display_ready; then
        warn "Xvfb did not start; log:"
        tail -n 20 /tmp/ornith_xvfb.log 2>/dev/null || true
        return 1
    fi
    log "Xvfb started on $DISPLAY_NUM (${SCREEN_W}x${SCREEN_H}x${SCREEN_D})"
    return 0
}

start_wm() {
    if DISPLAY="$DISPLAY_NUM" wmctrl -m >/dev/null 2>&1; then
        local wm
        wm=$(DISPLAY="$DISPLAY_NUM" wmctrl -m 2>/dev/null \
            | awk -F': ' '/^Name:/ {print $2; exit}')
        log "window manager already running: ${wm:-unknown}"
        return 0
    fi
    if ! cmd_ok openbox; then
        die "openbox is not installed"
    fi
    DISPLAY="$DISPLAY_NUM" nohup openbox --sm-disable \
        >/tmp/ornith_openbox.log 2>&1 &
    local i
    for i in $(seq 1 50); do
        if DISPLAY="$DISPLAY_NUM" wmctrl -m >/dev/null 2>&1; then
            local wm
            wm=$(DISPLAY="$DISPLAY_NUM" wmctrl -m 2>/dev/null \
                | awk -F': ' '/^Name:/ {print $2; exit}')
            log "openbox started: ${wm:-openbox}"
            return 0
        fi
        sleep 0.2
    done
    warn "openbox did not start; log:"
    tail -n 20 /tmp/ornith_openbox.log 2>/dev/null || true
    return 1
}

start_vnc() {
    if [ "$VNC" -ne 1 ]; then
        return 0
    fi
    if ! cmd_ok x11vnc; then
        warn "x11vnc is not installed"
        return 1
    fi
    if pgrep -f "x11vnc.*${DISPLAY_NUM}" >/dev/null 2>&1; then
        log "x11vnc already running"
        return 0
    fi
    DISPLAY="$DISPLAY_NUM" nohup x11vnc -display "$DISPLAY_NUM" \
        -forever -shared -nopw -rfbport 5900 -localhost -bg \
        -o /tmp/ornith_x11vnc.log >/dev/null 2>&1
    sleep 1
    if pgrep -f "x11vnc.*${DISPLAY_NUM}" >/dev/null 2>&1; then
        log "x11vnc listening on localhost:5900 (use an SSH tunnel)"
        return 0
    fi
    warn "x11vnc did not start; see /tmp/ornith_x11vnc.log"
    return 1
}

do_stop() {
    log "stopping desktop on $DISPLAY_NUM"
    local names=(xterm gedit pcmanfm thunar galculator soffice.bin
                 soffice libreoffice xclip x11vnc openbox)
    local name pid
    for name in "${names[@]}"; do
        while read -r pid; do
            if [ -n "$pid" ] && pid_has_display "$pid" "$DISPLAY_NUM"; then
                stop_process "$pid"
            fi
        done < <(pgrep -x "$name" 2>/dev/null || true)
    done
    local lock="/tmp/.X${XNUM}-lock"
    if [ -f "$lock" ]; then
        local lpid
        lpid=$(cat "$lock" 2>/dev/null || true)
        if [ -n "$lpid" ] && grep -q "Xvfb" "/proc/$lpid/cmdline" 2>/dev/null; then
            stop_process "$lpid"
        fi
    fi
    rm -f "$lock" "/tmp/.X11-unix/X${XNUM}" 2>/dev/null || true
    log "stop done (idempotent)"
    return 0
}

log "mode=$MODE action=$ACTION display=$DISPLAY_NUM screen=${SCREEN_W}x${SCREEN_H}x${SCREEN_D}"
case "$ACTION" in
    check)
        do_check
        exit $?
        ;;
    stop)
        do_stop
        exit $?
        ;;
esac

install_needed
start_xvfb || exit 1
start_wm || exit 1
start_vnc || true
do_check

