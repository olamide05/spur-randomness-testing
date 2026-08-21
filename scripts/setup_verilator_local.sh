#!/usr/bin/env bash
# Install the distribution's Verilator package inside this repository.
# This fallback needs no root access; scripts/setup.sh remains the preferred
# system-wide installer.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="$REPO_ROOT/.tools/verilator"
VERILATOR_BIN="$INSTALL_DIR/usr/bin/verilator"

repair_layout() {
    if [ ! -e "$INSTALL_DIR/usr/include" ]; then
        ln -s share/verilator/include "$INSTALL_DIR/usr/include"
    fi
    if [ ! -e "$INSTALL_DIR/usr/bin/verilator_includer" ]; then
        ln -s ../share/verilator/bin/verilator_includer \
            "$INSTALL_DIR/usr/bin/verilator_includer"
    fi
}

if [ -x "$VERILATOR_BIN" ]; then
    repair_layout
    echo "Local Verilator already exists: $($VERILATOR_BIN --version)"
    exit 0
fi

if ! command -v apt-get >/dev/null 2>&1 || ! command -v dpkg-deb >/dev/null 2>&1; then
    echo "ERROR: rootless package installation requires apt-get and dpkg-deb." >&2
    exit 1
fi

echo "Downloading the Verilator package without installing system-wide..."
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT
(
    cd "$TEMP_DIR"
    apt-get download verilator
)

shopt -s nullglob
PACKAGES=("$TEMP_DIR"/verilator_*.deb)
if [ "${#PACKAGES[@]}" -ne 1 ]; then
    echo "ERROR: expected one downloaded Verilator package." >&2
    exit 1
fi

mkdir -p "$INSTALL_DIR"
dpkg-deb -x "${PACKAGES[0]}" "$INSTALL_DIR"

# The packaged Perl driver normally uses compiled-in /usr paths. Give the
# extracted package a self-contained VERILATOR_ROOT layout for the Web UI.
repair_layout

echo "Local Verilator ready: $($VERILATOR_BIN --version)"
