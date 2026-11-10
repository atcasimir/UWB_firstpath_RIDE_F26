@echo off
rem Main window: run this on the PC of the responder board.
cd /d "%~dp0"
python uwb_gui.py
if errorlevel 1 pause
