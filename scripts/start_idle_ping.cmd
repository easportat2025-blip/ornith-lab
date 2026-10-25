@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
set "PYW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if not exist "%PYW%" set "PYW=pythonw"
set "PIDF=scripts\state\idle_ping.pid"

if exist "%PIDF%" (
  set /p OLDPID=<"%PIDF%"
  tasklist /FI "PID eq %OLDPID%" 2>nul | findstr /i "python" >nul
  if not errorlevel 1 (
    echo [idle_ping] already running pid %OLDPID%
    exit /b 0
  )
)

start "" /b "%PYW%" "scripts\idle_ping.py"
echo [idle_ping] started; log scripts\logs\idle_ping.log
endlocal
