#!/usr/bin/env bash
#
# postCreateCommand for GitHub Codespaces / Dev Containers.
# Installs system + Python build dependencies and compiles the NIST STS suite.
#
set -euo pipefail

echo "=================================================="
echo " SPUR Randomness Testing Framework - environment setup"
echo "=================================================="

# ------------------------------------------------------------------
# 1. System build tools (gcc, make, unzip, curl) for building NIST STS
# ------------------------------------------------------------------
echo "[1/3] Installing system build tools (build-essential, gcc, make)..."
if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
else
    SUDO=""
fi
export DEBIAN_FRONTEND=noninteractive
$SUDO apt-get update -y
$SUDO apt-get install -y --no-install-recommends \
    build-essential gcc make curl unzip

# ------------------------------------------------------------------
# 2. Python dependencies
# ------------------------------------------------------------------
echo "[2/3] Installing Python dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# ------------------------------------------------------------------
# 3. Download (if needed) + build the NIST Statistical Test Suite
# ------------------------------------------------------------------
echo "[3/3] Setting up NIST STS 2.1.2..."
bash scripts/setup_sts.sh

echo ""
echo "=================================================="
echo " Setup complete. Verifying the framework..."
echo "=================================================="
python test_framework.py

echo ""
echo "Environment is ready. Try:  python verify_v1.py"
