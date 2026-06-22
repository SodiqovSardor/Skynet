#!/bin/bash
# Skynet — Setup Script
# Creates a virtual environment and installs dependencies.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo " SKYNET — Setup"
echo "============================================================"
echo ""

# Check Python
PYTHON="python3"
if ! command -v "$PYTHON" &> /dev/null; then
    PYTHON="python"
    if ! command -v "$PYTHON" &> /dev/null; then
        echo "[ERROR] Python 3 not found. Please install Python 3.11+."
        exit 1
    fi
fi

echo "[1/3] Creating virtual environment..."
"$PYTHON" -m venv venv

echo "[2/3] Installing dependencies..."
./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -r requirements.txt -q

echo "[3/3] Verifying installation..."
./venv/bin/python -c "
from core.brain import Brain, Message
from actuators.registry import registry
from sensors.system_sensors import get_system_stats, get_network_status
print('  ✓ Core modules loaded')
print(f'  ✓ {len(registry.tools)} tools registered: {list(registry.tools.keys())}')
print('  ✓ Installation complete')
"

echo ""
echo "============================================================"
echo " SKYNET is ready."
echo " Run:  ./run.sh"
echo "============================================================"
