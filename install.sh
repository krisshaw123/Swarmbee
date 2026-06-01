#!/usr/bin/env bash

set -e

echo "🐝 Installing Swarmbee..."

WORK_DIR="$HOME/.swarmbee"

mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

echo "📦 Downloading openclaw-lark..."

curl -L \
https://raw.githubusercontent.com/krisshaw123/Swarmbee/main/openclaw-lark.zip \
-o openclaw-lark.zip

echo "📦 Downloading installer..."

curl -L \
https://raw.githubusercontent.com/krisshaw123/Swarmbee/main/swarmbee.sh \
-o swarmbee.sh

chmod +x swarmbee.sh

./swarmbee.sh