#!/bin/bash
# macOS: double-click this file in Finder to open the small window for the initiator board.
# First time only: right-click it, choose Open, and confirm (macOS asks once for files
# that came from another computer). If it opens in a text editor instead, see Help,
# section "On a Mac".
cd "$(dirname "$0")" || exit 1

# Use a Python whose window toolkit works. The one built into macOS (/usr/bin/python3)
# ships an old Tk that shows blank windows, so it is only tried last.
PY=""
for candidate in /Library/Frameworks/Python.framework/Versions/Current/bin/python3 \
                 /opt/homebrew/bin/python3 /usr/local/bin/python3 "$(command -v python3)"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ] && \
       "$candidate" -c "import tkinter, sys; sys.exit(0 if tkinter.TkVersion >= 8.6 else 1)" 2>/dev/null; then
        PY="$candidate"
        break
    fi
done

if [ -z "$PY" ]; then
    echo "No Python with a working window toolkit (Tk 8.6 or newer) was found."
    echo "Install Python from https://www.python.org/downloads/ and then run:"
    echo "    python3 -m pip install pyserial numpy matplotlib"
    echo "(With Homebrew Python:  brew install python-tk)"
    read -n 1 -s -r -p "Press any key to close."
    exit 1
fi

if ! "$PY" -c "import serial" 2>/dev/null; then
    echo "pyserial is not installed for $PY. Run:"
    echo "    $PY -m pip install pyserial numpy matplotlib"
    read -n 1 -s -r -p "Press any key to close."
    exit 1
fi

"$PY" uwb_gui_initiator.py
status=$?
if [ $status -ne 0 ]; then
    echo
    read -n 1 -s -r -p "The program ended with an error (see above). Press any key to close."
fi
