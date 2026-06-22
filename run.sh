#!/bin/bash

# Project Skynet Launcher
# This script ensures the environment is correct and launches the orchestrator.

PROJECT_ROOT="/home/sadi/Skynet"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment not found. Please run setup first."
    exit 1
fi

cd "$PROJECT_ROOT"
echo "--- Initializing Skynet ---"
$VENV_PYTHON -m core.autonomous_orchestrator
