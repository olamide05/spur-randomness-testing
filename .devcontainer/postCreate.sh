#!/usr/bin/env bash
#
# postCreateCommand for GitHub Codespaces / Dev Containers.
# Installs system + Python dependencies and compiles the NIST STS suite.
#
set -euo pipefail

echo "=================================================="
echo " SPUR Randomness Testing Framework - environment setup"
echo "=================================================="

make install
