#!/usr/bin/env bash

set -e

echo "🐝 Installing Swarmbee..."

WORK_DIR="$HOME/.swarmbee"

mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

echo "📦 Downloading openclaw-lark..."

curl -L \
https://github.com/krisshaw123/Swarmbee/releases/latest/download/openclaw-lark.zip \
-o openclaw-lark.zip

echo "📦 Downloading swarmbee installer..."

curl -L \
https://github.com/krisshaw123/Swarmbee/releases/latest/download/swarmbee.sh \
-o swarmbee.sh

chmod +x swarmbee.sh

./swarmbee.sh