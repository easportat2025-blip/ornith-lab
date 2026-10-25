@echo off
chcp 65001 >nul
setlocal
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8788" ^| findstr "LISTENING"') do (
  taskkill /PID %%p /F >nul 2>&1
)
echo oc_chat stopped (port 8788)
endlocal
