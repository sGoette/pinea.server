#!/bin/sh
# Started by systemd (pinea.service). Installed to <root>/bin/ by install.sh, outside the
# release folders, so a broken release can't break the rollback.
#
# Rollback: after a self-update the app writes data/update/pending (path of the previous
# release) and the new release removes it once it has started successfully. If the new release
# fails to start MAX_ATTEMPTS times, `current` is switched back to the previous release.
set -u

ROOT="${PINEA_ROOT:-/usr/local/pinea.server}"
CURRENT="$ROOT/current"
STATE="$ROOT/data/update"
# Empty host = listen on all IPv4 and IPv6 addresses (two sockets). Set PINEA_HOST=0.0.0.0 for IPv4 only.
HOST="${PINEA_HOST-}"
PORT="${PINEA_PORT:-4000}"
MAX_ATTEMPTS=3

if [ -f "$STATE/pending" ]; then
    attempts=$(cat "$STATE/attempts" 2>/dev/null || echo 0)
    attempts=$((attempts + 1))
    echo "$attempts" > "$STATE/attempts"

    if [ "$attempts" -gt "$MAX_ATTEMPTS" ]; then
        previous=$(cat "$STATE/pending")
        failed=$(readlink -f "$CURRENT")
        if [ -n "$previous" ] && [ -d "$previous" ]; then
            echo "pinea-run: $failed failed to start $MAX_ATTEMPTS times, rolling back to $previous" >&2
            ln -sfn "$previous" "$CURRENT"
            echo "$failed" > "$STATE/rolled_back"
        else
            echo "pinea-run: $failed keeps failing, but the previous release '$previous' is gone" >&2
        fi
        rm -f "$STATE/pending" "$STATE/attempts"
    fi
fi

exec "$CURRENT/.venv/bin/python" -m uvicorn app.main:app \
    --app-dir "$CURRENT/backend" \
    --host "$HOST" \
    --port "$PORT"
