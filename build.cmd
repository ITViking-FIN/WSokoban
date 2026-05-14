@echo off
REM Build a single-file WSokoban.exe with UPX compression.
REM Requires: upx.exe alongside this script (one ships in the repo).
cd /d %~dp0
set "PATH=%~dp0;%PATH%"
python -m PyInstaller WSokoban.spec --noconfirm --clean
