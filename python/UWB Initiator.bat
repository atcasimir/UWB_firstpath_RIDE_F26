@echo off
rem Small window for the PC of the initiator board: choose the port, press Start once.
cd /d "%~dp0"
python uwb_gui_initiator.py
if errorlevel 1 pause
