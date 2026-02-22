#!/bin/sh

VERSION="$1"

if [ -z "$VERSION" ]; then
  echo "Usage: update.sh v0.1.0"
  exit 1
fi

cd /usr/local/pinea.server/releases
fetch https://github.com/sGoette/pinea.server/releases/download/$VERSION/pineaserver-$VERSION.tar.gz
tar -xzf pineaserver-$VERSION.tar.gz
cd /usr/local/pinea.server/releases/$VERSION
sh install.sh