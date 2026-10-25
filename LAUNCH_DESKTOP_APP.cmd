@echo off
REM ============================================================
REM  LAUNCH DESKTOP APP (Ornith Agent Desktop)
REM  - chay bus_desktop.py (server 8777 + SSE + API)
REM  - mo Chrome o che do --app (cua so desktop, khong address bar)
REM  - tu dong dung neu co instance dang chay
REM ============================================================
chcp 65001 > nul
cd /d "C:\Users\Admin\Desktop\New folder"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
REM --- dung instance cu (neu co) ---
taskkill /F /IM python.exe /FI "WINDOWTITLE eq bus_desktop*" 2>nul
REM --- start server nen ---
start "bus_desktop" /B python scripts\bus_desktop.py --port 8777
timeout /t 2 /nobreak > nul
REM --- mo Chrome che do --app (cua so desktop) ---
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app="http://127.0.0.1:8777/" --window-size=1280,800
echo.
echo  Desktop app dang chay tai http://127.0.0.1:8777
echo  (dong cua so nay de dung server)
pause
:cleanup
taskkill /F /FI "WINDOWTITLE eq bus_desktop*" 2>nul
