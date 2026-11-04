@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -B serve_portal.py
  goto finished
)
set "PORTAL_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%PORTAL_PYTHON%" (
  "%PORTAL_PYTHON%" -B serve_portal.py
  goto finished
)
py -3.12 -B serve_portal.py
:finished
if errorlevel 1 (
  echo See the error above. Run Setup Windows.bat if this is a new installation.
  pause
)
