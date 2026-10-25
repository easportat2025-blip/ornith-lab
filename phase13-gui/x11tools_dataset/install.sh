#!/bin/sh
# Cai xdotool OFFLINE (khong can apt/mang).
set -e
DIR=$(dirname "$0")
DEBS=$(ls "$DIR"/*.deb 2>/dev/null || true)
if [ -n "$DEBS" ]; then
  dpkg -i $DEBS
else
  # layout da giai nen: copy binary + lib
  cp "$DIR"/xdotool /usr/local/bin/ 2>/dev/null || true
  cp "$DIR"/libxdo.so* /usr/local/lib/ 2>/dev/null || true
  ldconfig
fi
xdotool --version || true
