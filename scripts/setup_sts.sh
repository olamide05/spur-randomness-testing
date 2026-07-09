#!/usr/bin/env bash
#
# Downloads (if necessary) and builds the NIST SP 800-22 Statistical Test Suite
# (STS 2.1.2). Safe to run repeatedly - it is idempotent.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STS_DIR="$REPO_ROOT/sts/sts-2.1.2"
STS_URL="https://csrc.nist.gov/CSRC/media/Projects/Random-Bit-Generation/documents/sts-2_1_2.zip"

echo "--- NIST STS setup ---"

# ------------------------------------------------------------------
# 1. Download the STS source if it is not already present in the repo
# ------------------------------------------------------------------
if [ ! -f "$STS_DIR/src/assess.c" ]; then
    echo "NIST STS source not found - downloading from NIST..."
    mkdir -p "$REPO_ROOT/sts"
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    if curl -fSL "$STS_URL" -o "$tmp/sts.zip"; then
        unzip -q "$tmp/sts.zip" -d "$REPO_ROOT/sts"
        echo "Downloaded and extracted NIST STS."
    else
        echo "ERROR: failed to download NIST STS from:" >&2
        echo "       $STS_URL" >&2
        echo "       Please download it manually into $STS_DIR" >&2
        exit 1
    fi
else
    echo "NIST STS source already present at $STS_DIR"
fi

# ------------------------------------------------------------------
# 2. Build the 'assess' binary from source
# ------------------------------------------------------------------
echo "Building the 'assess' binary with make..."
mkdir -p "$STS_DIR/obj"
make -C "$STS_DIR" clean >/dev/null 2>&1 || true
make -C "$STS_DIR"

if [ ! -x "$STS_DIR/assess" ]; then
    echo "ERROR: build finished but $STS_DIR/assess was not produced." >&2
    exit 1
fi

# ------------------------------------------------------------------
# 3. Ensure the output directory structure STS requires exists
#    (assess does NOT create these directories itself)
# ------------------------------------------------------------------
echo "Ensuring STS output directories exist..."
( cd "$STS_DIR/experiments" && bash create-dir-script >/dev/null 2>&1 || true )

echo "NIST STS ready: $STS_DIR/assess"
