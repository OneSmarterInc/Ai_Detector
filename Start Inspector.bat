@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run Setup Windows.bat first. See README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -B run_inspector.py
if errorlevel 1 (
  echo Could not start. See the error above and README.md.
  pause
)
