@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto dependencies
py -3.12 -c "import struct; assert struct.calcsize('P') == 8" >nul 2>&1
if not errorlevel 1 (
  py -3.12 -m venv .venv
  if errorlevel 1 goto failed
  goto dependencies
)
python -c "import sys,struct; assert sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8" >nul 2>&1
if errorlevel 1 (
  echo Install 64-bit Python 3.12, then run this setup again.
  goto failed
)
python -m venv .venv
if errorlevel 1 goto failed
:dependencies
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" scripts\setup_model.py
if errorlevel 1 goto failed
where npm.cmd >nul 2>&1
if errorlevel 1 (
  echo Install Node.js 22.12 or newer, then run setup again.
  goto failed
)
pushd frontend
call npm.cmd ci
if errorlevel 1 (
  popd
  goto failed
)
call npm.cmd run build
if errorlevel 1 (
  popd
  goto failed
)
popd
echo Setup complete. Open Start Portal.bat.
pause
exit /b 0
:failed
echo Setup did not finish. Review the message above and README.md.
pause
exit /b 1
