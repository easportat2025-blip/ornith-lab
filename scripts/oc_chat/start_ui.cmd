@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0..\.."
set "CHAT=http://127.0.0.1:8788"
set "PYW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if not exist "%PYW%" set "PYW=pythonw"

rem --- legacy UI mode: stop headless first, then start server + Chrome app ---
call "scripts\oc_chat\stop.cmd" >nul 2>&1
start "" /b "%PYW%" "scripts\oc_chat\server.py" --port 8788
powershell -NoProfile -Command "for($i=0;$i -lt 40;$i++){try{(Invoke-WebRequest -UseBasicParsing '%CHAT%/api/health' -TimeoutSec 1)|Out-Null;exit 0}catch{Start-Sleep -Milliseconds 300}};exit 1"
if errorlevel 1 (
  echo [oc_chat] server khong khoi dong duoc - xem scripts\oc_chat\server.err.log
  pause
  exit /b 1
)

set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
start "" "%CHROME%" --app=%CHAT%/ --window-size=1380,900 ^
  --user-data-dir="%LOCALAPPDATA%\oc_chat_profile" ^
  --no-first-run --no-default-browser-check --disable-features=Translate

endlocal
