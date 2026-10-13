#!/bin/bash
# Double-click in Finder (or run ./start_mac.command) to launch uTesla Reader.
# First run creates a local virtual environment in .venv and installs pyserial.
set -e
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    PY=""
    for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
        if command -v "$candidate" >/dev/null 2>&1 \
           && "$candidate" -c 'import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 9) and tkinter.TkVersion >= 8.6 else 1)' 2>/dev/null; then
            PY="$candidate"; break
        fi
    done
    if [ -z "$PY" ]; then
        echo "No Python 3.9+ with Tk 8.6 found. Install Python from https://www.python.org/downloads/macos/"
        echo "(or: brew install python python-tk) and run this script again."
        read -r -p "Press Enter to close."
        exit 1
    fi
    echo "Creating virtual environment with $PY ..."
    "$PY" -m venv .venv
    .venv/bin/python -m pip install --quiet --upgrade pip
    .venv/bin/python -m pip install --quiet -r requirements.txt
fi

exec .venv/bin/python -m utesla_reader "$@"
