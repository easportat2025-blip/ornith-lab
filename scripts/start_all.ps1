# start_all.ps1 - khoi dong TOAN BO pipeline nen (dung cho Scheduled Task khi
# may Windows bat len).
#
# Key lay tu HKCU:\Environment (registry - KHONG ghi key vao file) -> dua vao env
# cua process roi spawn cac worker DETACHED.
#
#   watchdog A  -> scripts/logs/watchdog.log    (queue gpu_queue.json)
#   watchdog B  -> scripts/logs/watchdog_B.log  (queue gpu_queue_B.json)
#   space_sync  -> scripts/logs/space_sync.log   (day state len Space moi 3')
#   agent_md    -> scripts/logs/agent_md_watch.log (watcher agent.md)
$ErrorActionPreference = 'Continue'
$root = 'C:\Users\Admin\Desktop\New folder'
Set-Location $root
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$py = 'C:\Users\Admin\AppData\Local\Programs\Python\Python312\python.exe'
if (-not (Test-Path $py)) { $py = (Get-Command python).Source }

# --- 1) doc key tu registry (user env) ---
$reg = Get-ItemProperty -Path 'HKCU:\Environment' -ErrorAction SilentlyContinue
function Get-Reg($n) { if ($reg -and $reg.PSObject.Properties.Name -contains $n) { return $reg.$n } return $null }
$env:KAGGLE_KEY_A = Get-Reg 'KAGGLE_KEY_A'
$env:KAGGLE_KEY_B = Get-Reg 'KAGGLE_KEY_B'
$env:ACC_SRC_USERNAME = Get-Reg 'ACC_SRC_USERNAME'
$env:ACC_SRC_KEY = Get-Reg 'ACC_SRC_KEY'
$env:HF_TOKEN = Get-Reg 'HF_TOKEN'
$env:HF_TOKEN_2 = Get-Reg 'HF_TOKEN_2'
$ok = ($env:KAGGLE_KEY_A -and $env:KAGGLE_KEY_B)
Write-Output ("[start_all] key A/B: " + $(if ($ok) { 'OK' } else { 'THIEU (KAGGLE_KEY_A/B trong HKCU:\Environment)' }))
Write-Output ("[start_all] HF_TOKEN: " + $(if ($env:HF_TOKEN) { 'co' } else { 'thieu' }))

# --- 2) watchdog A + B (tu restart, tu doc key tu env) ---
# guard: dung cac process cu truoc (space_sync / watcher agent.md) de khong
# chay trung
Write-Output '[start_all] dung process cu (space_sync / agent_md_watch / bus / watch_bus / space_revive / space_sync_docker)...'
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {
  $_.CommandLine -match 'space_sync_loop|watch_agent_md|scripts\\bus\.py|watch_bus|space_revive|space_sync_docker' } | ForEach-Object {
  try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {}
}
if ($ok) {
  Write-Output '[start_all] khoi dong watchdog A + B...'
  & $py "$root\scripts\restart_watchdogs.py"
}

# --- 3) space_sync (day state len HF Space) ---
if ($env:HF_TOKEN) {
  Write-Output '[start_all] khoi dong space_sync...'
  $logDir = "$root\scripts\logs"
  New-Item -ItemType Directory -Force -Path $logDir | Out-Null
  $env:SPACE_SYNC_INTERVAL = '180'
  Start-Process -FilePath $py -ArgumentList "`"$root\scripts\space_sync_loop.py`"" `
    -WorkingDirectory $root -WindowStyle Hidden `
    -RedirectStandardOutput "$logDir\space_sync.log" `
    -RedirectStandardError "$logDir\space_sync.err" -ErrorAction SilentlyContinue
}

# --- 4) watcher agent.md ---
Write-Output '[start_all] khoi dong watcher agent.md...'
$logDir = "$root\scripts\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$env:WATCH_LOOP = '1'
Start-Process -FilePath $py -ArgumentList "`"$root\scripts\watch_agent_md.py`"" `
  -WorkingDirectory $root -WindowStyle Hidden `
  -RedirectStandardOutput "$logDir\agent_md_watch.log" `
  -RedirectStandardError "$logDir\agent_md_watch.err" -ErrorAction SilentlyContinue

# --- 4b) space_sync_docker (day state vao /ingest cua Space DOCKER) ---
if ($env:HF_TOKEN) {
  Write-Output '[start_all] khoi dong space_sync_docker (Space Docker)...'
  $env:SPACE_SYNC_INTERVAL = '180'
  Start-Process -FilePath $py -ArgumentList "`"$root\scripts\space_sync_docker_loop.py`"" `
    -WorkingDirectory $root -WindowStyle Hidden `
    -RedirectStandardOutput "$logDir\space_sync_docker.log" `
    -RedirectStandardError "$logDir\space_sync_docker.err" -ErrorAction SilentlyContinue
}

# --- 4c) space_revive (thu mo lai Space Docker khi HF bao PAUSED) ---
if ($env:HF_TOKEN) {
  Write-Output '[start_all] khoi dong space_revive...'
  $env:SPACE_REVIVE_INTERVAL = '600'
  Start-Process -FilePath $py -ArgumentList "`"$root\scripts\space_revive.py`"" `
    -WorkingDirectory $root -WindowStyle Hidden `
    -RedirectStandardOutput "$logDir\space_revive.out" `
    -RedirectStandardError "$logDir\space_revive.err" -ErrorAction SilentlyContinue
}

Write-Output '[start_all] xong. Kiem tra: Get-Content scripts\logs\watchdog.log -Tail 3'

# --- 5) BUS tin nhanh (trao chuyen tuc thien) + subscriber (day tin vao session) ---
Write-Output '[start_all] khoi dong BUS + watch_bus...'
$env:BUS_URL = 'http://127.0.0.1:8777'
Start-Process -FilePath $py -ArgumentList "`"$root\scripts\bus.py`"" `
  -WorkingDirectory $root -WindowStyle Hidden `
  -RedirectStandardOutput "$logDir\bus.log" `
  -RedirectStandardError "$logDir\bus.err" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Start-Process -FilePath $py -ArgumentList "`"$root\scripts\watch_bus.py`"" `
  -WorkingDirectory $root -WindowStyle Hidden `
  -RedirectStandardOutput "$logDir\watch_bus.log" `
  -RedirectStandardError "$logDir\watch_bus.err" -ErrorAction SilentlyContinue
