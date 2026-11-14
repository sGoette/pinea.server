#!/bin/sh
set -e

VERSION="$1"

if [ -z "$VERSION" ]; then
  echo "Usage: ./scripts/release.sh v0.1.0"
  exit 1
fi

case "$VERSION" in
  *[!A-Za-z0-9._-]*) echo "❌ Version may only contain A-Z a-z 0-9 . _ -"; exit 1 ;;
esac

echo "🚀 Building release $VERSION"

# Must run before anything is created in the repo (the release folder would count as a change).
# A build with uncommitted changes gets a "-dirty" commit, so it never counts as up to date.
COMMIT="$(git rev-parse HEAD)"
if [ -n "$(git status --porcelain)" ]; then
  COMMIT="$COMMIT-dirty"
fi

BUILD_DIR="build"
RELEASE_DIR="$VERSION"
ARCHIVE_NAME="pineaserver-$RELEASE_DIR.tar.gz"


rm -rf "$BUILD_DIR" "$RELEASE_DIR"
mkdir -p "$BUILD_DIR"
mkdir -p "$RELEASE_DIR"

npm run build

mkdir -p "$RELEASE_DIR/backend"
rsync -a \
  --exclude ".venv" \
  --exclude "__pycache__" \
  --exclude "*.pyc" \
  --exclude ".pytest_cache" \
  --exclude ".mypy_cache" \
  --exclude ".ruff_cache" \
  --exclude ".DS_Store" \
  backend/ "$RELEASE_DIR/backend/"

mkdir -p "$RELEASE_DIR/frontend"
rsync -a \
  --exclude "node_modules" \
  --exclude ".DS_Store" \
  dist/frontend/ "$RELEASE_DIR/frontend/"

if [ ! -f "$RELEASE_DIR/frontend/index.html" ]; then
  echo "❌ frontend/index.html not found in release output."
  echo "   Adjust your frontend build output path or update the rsync source."
  exit 1
fi

cp scripts/install.sh "$RELEASE_DIR/install.sh"
chmod +x "$RELEASE_DIR/install.sh"

cp scripts/pinea "$RELEASE_DIR/pinea"
chmod +x "$RELEASE_DIR/pinea"

cp scripts/update.sh "$RELEASE_DIR/update.sh"
chmod +x "$RELEASE_DIR/update.sh"

cp scripts/rebase.sh "$RELEASE_DIR/rebase.sh"
chmod +x "$RELEASE_DIR/rebase.sh"

# Linux install (systemd + self-update), see scripts/linux/install.sh
mkdir -p "$RELEASE_DIR/scripts/linux"
cp scripts/linux/install.sh scripts/linux/pinea-run.sh scripts/linux/pinea.service "$RELEASE_DIR/scripts/linux/"
chmod +x "$RELEASE_DIR/scripts/linux/install.sh" "$RELEASE_DIR/scripts/linux/pinea-run.sh"

# VERSION.json: lets the server know which commit it runs (used by the updater).
python3 - "$RELEASE_DIR/VERSION.json" "$VERSION" "$COMMIT" "$(git log -1 --format=%cI)" "$(git log -1 --format=%s)" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" <<'EOF'
import json, sys
path, name, commit, commit_date, message, built_at = sys.argv[1:]
with open(path, "w", encoding="utf-8") as f:
    json.dump({"name": name, "commit": commit, "commit_date": commit_date, "message": message, "built_at": built_at}, f, indent=2)
EOF

tar -czf $BUILD_DIR/"$ARCHIVE_NAME" "$RELEASE_DIR"

# version.json: published next to the tarball, read by the updater and install.sh
if command -v sha256sum >/dev/null 2>&1; then
  SHA256="$(sha256sum "$BUILD_DIR/$ARCHIVE_NAME" | cut -d' ' -f1)"
else
  SHA256="$(shasum -a 256 "$BUILD_DIR/$ARCHIVE_NAME" | cut -d' ' -f1)"
fi
python3 - "$RELEASE_DIR/VERSION.json" "$BUILD_DIR/version.json" "$SHA256" <<'EOF'
import json, sys
source, target, sha256 = sys.argv[1:]
with open(source, encoding="utf-8") as f:
    data = json.load(f)
data["sha256"] = sha256
with open(target, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
EOF

rm -rf "$RELEASE_DIR"

echo "✅ Created $BUILD_DIR/$ARCHIVE_NAME and $BUILD_DIR/version.json"