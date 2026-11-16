#!/bin/sh
# pinea.server installer for Debian/Ubuntu. Run as root.
#
# Install, or update to the latest build of main:
#   curl -fsSL https://raw.githubusercontent.com/sGoette/pinea.server/main/scripts/linux/install.sh -o install.sh
#   sudo sh install.sh
#
# Options:
#   --tarball FILE   install this release tarball instead of downloading the latest build
#   --no-start       install everything but don't (re)start the service, e.g. to copy an
#                    existing database and posters into data/ before the first start
#   --skip-apt       don't install/upgrade system packages
#   --no-port80      don't forward port 80 to 4000 (by default http://<host>/ works without :4000)
#   --no-avahi       don't announce the machine's host name (<hostname>.local) via avahi
#
# Running it again is safe. It updates the system packages, the systemd unit and the runner
# script, installs the latest build if it isn't the running one, and restarts the service.
# Day-to-day updates can also be done from the web UI (Settings -> Server updates).
set -eu

ROOT="${PINEA_ROOT:-/usr/local/pinea.server}"
SERVICE_USER="${PINEA_USER:-pineaserver}"
UPDATE_BASE_URL="${PINEA_UPDATE_URL:-https://github.com/sGoette/pinea.server/releases/download/main-build}"
TARBALL_NAME="pineaserver-main.tar.gz"
KEEP_RELEASES=3

TARBALL=""
START=1
APT=1
PORT80=1
AVAHI=1

info() { echo "✅  $*"; }
warn() { echo "⚠️  $*" >&2; }
die()  { echo "❌  $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
    case "$1" in
        --tarball)  [ $# -ge 2 ] || die "--tarball needs a file"; TARBALL="$2"; shift 2 ;;
        --no-start) START=0; shift ;;
        --skip-apt) APT=0; shift ;;
        --no-port80) PORT80=0; shift ;;
        --no-avahi) AVAHI=0; shift ;;
        -h|--help)  sed -n '2,20p' "$0"; exit 0 ;;
        *)          die "Unknown option: $1" ;;
    esac
done

# --- Preconditions ---
[ "$(id -u)" -eq 0 ] || die "Run as root (sudo sh install.sh)."
command -v apt-get >/dev/null 2>&1 || die "This installer supports Debian/Ubuntu (apt) only."
command -v systemctl >/dev/null 2>&1 || die "systemd is required."

# --- System packages ---
if [ "$APT" -eq 1 ]; then
    info "Installing system packages (python3, venv, ffmpeg)"
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 python3-venv ffmpeg curl ca-certificates tar
    if [ "$PORT80" -eq 1 ]; then
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends nftables
    fi
    if [ "$AVAHI" -eq 1 ]; then
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends avahi-daemon
    fi
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' \
    || die "Python >= 3.11 required, found $(python3 --version 2>&1)"

# --- Service user and folders ---
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    info "Creating system user $SERVICE_USER"
    useradd --system --user-group --home-dir "$ROOT" --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi
mkdir -p "$ROOT/releases" "$ROOT/data/db" "$ROOT/data/posters" "$ROOT/data/update" "$ROOT/logs" "$ROOT/bin"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --- Get the release tarball ---
if [ -z "$TARBALL" ]; then
    info "Downloading latest build from $UPDATE_BASE_URL"
    curl -fsSL "$UPDATE_BASE_URL/version.json" -o "$TMP/version.json"
    curl -fSL --progress-bar "$UPDATE_BASE_URL/$TARBALL_NAME" -o "$TMP/release.tar.gz"
    expected="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["sha256"])' "$TMP/version.json")"
    actual="$(sha256sum "$TMP/release.tar.gz" | cut -d' ' -f1)"
    [ "$expected" = "$actual" ] || die "Checksum mismatch (a new build was probably published meanwhile). Run again."
    TARBALL="$TMP/release.tar.gz"
fi
[ -f "$TARBALL" ] || die "Tarball not found: $TARBALL"

tar -tzf "$TARBALL" > "$TMP/entries" || die "Not a valid .tar.gz: $TARBALL"
NAME="$(head -n1 "$TMP/entries" | cut -d/ -f1)"
case "$NAME" in
    ""|*[!A-Za-z0-9._-]*) die "Unexpected release name in tarball: '$NAME'" ;;
esac
if grep -v -e "^$NAME\$" -e "^$NAME/" "$TMP/entries" >/dev/null; then
    die "Tarball contains files outside of $NAME/"
fi

RELEASE="$ROOT/releases/$NAME"
CURRENT_TARGET="$(readlink -f "$ROOT/current" 2>/dev/null || true)"

# --- Install the release ---
if [ "$CURRENT_TARGET" = "$RELEASE" ] && [ -x "$RELEASE/.venv/bin/python" ]; then
    info "$NAME is already installed and active"
else
    info "Installing $NAME"
    rm -rf "$RELEASE"
    tar -xzf "$TARBALL" -C "$ROOT/releases" --no-same-owner
    for required in backend/app/main.py backend/requirements.txt frontend/index.html scripts/linux/pinea-run.sh scripts/linux/pinea.service; do
        [ -f "$RELEASE/$required" ] || die "Release is missing $required"
    done

    info "Creating Python environment and installing dependencies"
    python3 -m venv "$RELEASE/.venv"
    PIP_NO_CACHE_DIR=1 "$RELEASE/.venv/bin/python" -m pip install --disable-pip-version-check --no-input \
        -r "$RELEASE/backend/requirements.txt"
fi

# --- Runner script and systemd unit (always taken from the release being installed) ---
info "Installing runner script and systemd unit"
install -m 0755 "$RELEASE/scripts/linux/pinea-run.sh" "$ROOT/bin/pinea-run.sh"
sed -e "s#@ROOT@#$ROOT#g" -e "s#@USER@#$SERVICE_USER#g" \
    "$RELEASE/scripts/linux/pinea.service" > /etc/systemd/system/pinea.service

# --- Activate ---
ln -sfn "$RELEASE" "$ROOT/current"
rm -f "$ROOT/data/update/pending" "$ROOT/data/update/attempts"

# The server user owns everything (needed for self-updates), except the runner script.
chown -R "$SERVICE_USER:$SERVICE_USER" "$ROOT"
chown -R root:root "$ROOT/bin"

# The main LAN interface = the one with the default route (not an internal storage network)
LAN_IF="$(ip route show default 2>/dev/null | awk '{ for (i = 1; i < NF; i++) if ($i == "dev") { print $(i + 1); exit } }')"

# --- Port 80 -> 4000 (the server itself stays on 4000, which the tvOS app gets via Bonjour) ---
if [ "$PORT80" -eq 1 ]; then
    if command -v nft >/dev/null 2>&1; then
        info "Forwarding port 80 to 4000 (nftables)"
        mkdir -p /etc/nftables.d
        cat > /etc/nftables.d/pinea.nft <<'NFT'
# Managed by pinea.server install.sh: http://<host>/ -> port 4000
table ip pinea_http {
    chain prerouting {
        type nat hook prerouting priority dstnat; policy accept;
        tcp dport 80 redirect to :4000
    }
}
NFT
        [ -f /etc/nftables.conf ] || printf '#!/usr/sbin/nft -f\nflush ruleset\n' > /etc/nftables.conf
        grep -q '/etc/nftables.d/' /etc/nftables.conf || printf '\ninclude "/etc/nftables.d/*.nft"\n' >> /etc/nftables.conf
        systemctl enable nftables >/dev/null 2>&1
        systemctl restart nftables || warn "nftables failed to load, check: nft -c -f /etc/nftables.conf"
    else
        warn "nft not found, skipping port 80 forwarding (run without --skip-apt)"
    fi
fi

# --- <hostname>.local via avahi: only on the LAN interface and IPv4 (the server listens on IPv4 only) ---
if [ "$AVAHI" -eq 1 ]; then
    if [ -f /etc/avahi/avahi-daemon.conf ] && [ -n "$LAN_IF" ]; then
        info "Announcing $(hostname).local on $LAN_IF (avahi)"
        sed -i -e "s/^#*allow-interfaces=.*/allow-interfaces=$LAN_IF/" \
               -e "s/^#*use-ipv6=.*/use-ipv6=no/" \
               -e "s/^#*publish-aaaa-on-ipv4=.*/publish-aaaa-on-ipv4=no/" /etc/avahi/avahi-daemon.conf
        systemctl enable avahi-daemon >/dev/null 2>&1
        systemctl restart avahi-daemon || warn "avahi-daemon failed to start"
    else
        warn "avahi not installed or no default route, skipping <hostname>.local"
    fi
fi

# --- Remove old releases ---
ls -1dt "$ROOT"/releases/*/ 2>/dev/null | tail -n +$((KEEP_RELEASES + 1)) | while read -r old; do
    old="${old%/}"
    if [ "$(readlink -f "$old")" != "$RELEASE" ]; then
        info "Removing old release $(basename "$old")"
        rm -rf "$old"
    fi
done

# --- Start ---
systemctl daemon-reload
systemctl enable pinea >/dev/null 2>&1

if [ "$START" -eq 0 ]; then
    systemctl stop pinea 2>/dev/null || true
    info "Installed $NAME. Service not started (--no-start). Start it with: systemctl start pinea"
    exit 0
fi

if [ ! -s "$ROOT/data/db/database.sqlite" ]; then
    warn "No database in $ROOT/data/db/ yet, the server will create a new, empty one."
    warn "To migrate an existing server instead: re-run with --no-start, copy database.sqlite and the posters into data/, then start."
fi

info "Restarting service"
systemctl restart pinea

i=0
until curl -fsS "http://127.0.0.1:4000/api/health" >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -ge 30 ]; then
        warn "The server didn't answer within 30s. Check: journalctl -u pinea -e  and  $ROOT/data/pinea.log"
        exit 1
    fi
    sleep 1
done

info "pinea.server $NAME is running on port 4000"
if [ "$PORT80" -eq 1 ] && [ "$AVAHI" -eq 1 ]; then
    info "Web UI: http://$(hostname).local"
fi
