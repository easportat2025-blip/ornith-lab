@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
set "PIDF=scripts\state\idle_ping.pid"
if not exist "%PIDF%" (
  echo [idle_ping] not running (no pid file)
  exit /b 0
)
set /p PID=<"%PIDF%"
taskkill /PID %PID% /F >nul 2>&1
del "%PIDF%" >nul 2>&1
echo [idle_ping] stopped pid %PID%
endlocal
