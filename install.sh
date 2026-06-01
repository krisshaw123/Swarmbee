#!/usr/bin/env bash

set -e

echo "🐝 Installing Swarmbee..."

WORK_DIR="$HOME/.swarmbee"

mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

echo "📦 Downloading openclaw-lark..."

curl -fL \
https://github.com/krisshaw123/Swarmbee/raw/main/openclaw-lark.zip \
-o openclaw-lark.zip

echo "📦 Downloading swarmbee installer..."

curl -fL \
https://github.com/krisshaw123/Swarmbee/raw/main/swarmbee.sh \
-o swarmbee.sh

chmod +x swarmbee.sh

echo "🚀 Starting installer..."

./swarmbee.sh