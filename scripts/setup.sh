#!/usr/bin/env bash
# Install all system/Python dependencies and build NIST STS.
# Intended for Debian/Ubuntu hosts, Codespaces, and the supplied devcontainer.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ "${1:-}" != "--skip-system" ]; then
    if ! command -v apt-get >/dev/null 2>&1; then
        echo "ERROR: automatic system-package installation currently supports Debian/Ubuntu (apt-get)." >&2
        exit 1
    fi

    if [ "$(id -u)" -eq 0 ]; then
        APT=(apt-get)
    elif command -v sudo >/dev/null 2>&1; then
        APT=(sudo apt-get)
    else
        echo "ERROR: root or sudo access is required to install system packages." >&2
        exit 1
    fi

    echo "[1/4] Installing compiler, Verilator, and setup utilities..."
    export DEBIAN_FRONTEND=noninteractive
    "${APT[@]}" update -y
    "${APT[@]}" install -y --no-install-recommends \
        build-essential \
        curl \
        gcc \
        make \
        python3 \
        python3-pip \
        python3-venv \
        unzip \
        verilator
else
    echo "[1/4] Skipping system packages (--skip-system)."
fi

for tool in gcc make; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: required tool '$tool' is not installed." >&2
        exit 1
    fi
done
if ! command -v verilator >/dev/null 2>&1 \
    && [ ! -x "$REPO_ROOT/.tools/verilator/usr/bin/verilator" ]; then
    echo "ERROR: Verilator is not installed. Run scripts/setup_verilator_local.sh or install it system-wide." >&2
    exit 1
fi

echo "[2/4] Creating the Python virtual environment..."
if [ ! -x .venv/bin/python ] || ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo "[3/4] Building NIST STS 2.1.2..."
bash scripts/setup_sts.sh

echo "[4/4] Running the automated checks..."
.venv/bin/python -m pytest -q

echo
echo "Setup complete. Start the UI with:"
echo "  .venv/bin/python webui/app.py"
echo "Then open http://127.0.0.1:5000"
