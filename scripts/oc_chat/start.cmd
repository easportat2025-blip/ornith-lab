@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0..\.."
set "CHAT=http://127.0.0.1:8788"
set "PYW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if not exist "%PYW%" set "PYW=pythonw"
set "OC_CHAT_HEADLESS=1"

rem --- headless server only: no Chrome, no app.html, no UI process ---
powershell -NoProfile -Command "try{(Invoke-WebRequest -UseBasicParsing '%CHAT%/api/health' -TimeoutSec 2)|Out-Null;exit 0}catch{exit 1}"
if errorlevel 1 (
  start "" /b "%PYW%" "scripts\oc_chat\server.py" --port 8788 --headless
  powershell -NoProfile -Command "for($i=0;$i -lt 40;$i++){try{(Invoke-WebRequest -UseBasicParsing '%CHAT%/api/health' -TimeoutSec 1)|Out-Null;exit 0}catch{Start-Sleep -Milliseconds 300}};exit 1"
  if errorlevel 1 (
    echo [oc_chat] headless server khong khoi dong duoc - xem scripts\oc_chat\server.err.log
    pause
    exit /b 1
  )
)

echo [oc_chat] headless API: %CHAT%/api/ping
echo [oc_chat] UI (neu can): scripts\oc_chat\start_ui.cmd
endlocal
