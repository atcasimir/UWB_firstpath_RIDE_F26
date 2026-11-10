#!/usr/bin/env python3
"""
uwb_platform.py - the few things that differ between Windows, macOS and Linux:
fonts, colours that must stay readable in macOS Dark Mode, how to open a file or
folder with the system's default program, and how serial ports are named.
Everything else in this folder is the same on every system.
"""

import os
import subprocess
import sys

IS_WINDOWS = os.name == "nt"
IS_MAC = sys.platform == "darwin"

if IS_WINDOWS:
    UI_FONT, MONO_FONT = "Segoe UI", "Consolas"
    UI_SIZE, MONO_SIZE = 10, 9
elif IS_MAC:
    UI_FONT, MONO_FONT = "Helvetica Neue", "Menlo"
    UI_SIZE, MONO_SIZE = 13, 11          # Tk on macOS draws the same point size smaller
else:
    UI_FONT, MONO_FONT = "DejaVu Sans", "DejaVu Sans Mono"
    UI_SIZE, MONO_SIZE = 10, 9


def ui(delta=0, bold=False):
    """A font for labels: ui() normal, ui(1, True) one point larger and bold."""
    return (UI_FONT, UI_SIZE + delta, "bold") if bold else (UI_FONT, UI_SIZE + delta)


def mono(delta=0):
    return (MONO_FONT, MONO_SIZE + delta)


def dark_mode():
    """True when macOS is in Dark Mode (window backgrounds are dark, so grey text must be light)."""
    if not IS_MAC:
        return False
    try:
        out = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"], capture_output=True, text=True,
                             timeout=2)
        return out.stdout.strip().lower() == "dark"
    except Exception:
        return False


_DARK = dark_mode()
HINT = "#a9afba" if _DARK else "#555555"   # explanatory text
SOFT = "#cfd3da" if _DARK else "#333333"   # secondary values


def open_path(path):
    """Open a file or folder with whatever the system uses for it (Explorer, Finder, the browser...)."""
    if IS_WINDOWS:
        os.startfile(path)  # noqa: only exists on Windows
    elif IS_MAC:
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def use_native_theme(ttk):
    """Windows: the 'vista' look. macOS and Linux keep the default, which is already native."""
    if IS_WINDOWS:
        try:
            ttk.Style().theme_use("vista")
        except Exception:
            pass


# Ports that are never a board (macOS lists these among the serial ports).
_NOT_A_BOARD = ("bluetooth", "debug-console", "wlan-debug", "wlan", "incoming-port")


def is_board_port(port):
    """False for the Mac's built-in pseudo ports."""
    text = ("%s %s" % (getattr(port, "device", ""), getattr(port, "description", "") or "")).lower()
    return not any(word in text for word in _NOT_A_BOARD)


def is_stlink(port):
    """The ST-LINK virtual COM port of a Nucleo board (USB vendor 0x0483 = STMicroelectronics)."""
    return (getattr(port, "vid", None) == 0x0483
            or "stlink" in (getattr(port, "description", "") or "").lower().replace("-", "").replace(" ", "")
            or "stmicro" in (getattr(port, "manufacturer", "") or "").lower())


PORT_EXAMPLE = "COM5" if IS_WINDOWS else ("/dev/cu.usbmodem1103" if IS_MAC else "/dev/ttyACM0")
LAUNCHERS = ("UWB Capture.bat", "UWB Initiator.bat") if IS_WINDOWS else ("UWB Capture.command", "UWB Initiator.command")
