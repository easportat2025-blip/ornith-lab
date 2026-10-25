# after_rollout_v21.ps1 - sau khi rollout v21 (vong self-play 2) COMPLETE:
#   curate bundle -> upload dataset gui-selfplay (version moi) -> wait READY.
# (KHONG push kernel: hang doi gpu_queue.json lo push.)
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'

$bundle = 'phase13-gui/out_rollout_v21/rollout_bundle.zip'
if (-not (Test-Path $bundle)) {
  Write-Output 'THIEU bundle - chua tai xong'
  exit 1
}

Write-Output ("=== curate rollout v21 $(Get-Date -Format 'HH:mm:ss') ===")
python phase13-gui/rollout_curate.py --bundle $bundle --cap 600 --max-fail 2 --exclude-variants 2 --stage phase13-gui/selfplay_dataset_v21 --out-jsonl gui-selfplay-v21.jsonl
if ($LASTEXITCODE -ne 0) { Write-Output 'curate loi'; exit 1 }

$n = (Get-Content 'phase13-gui/selfplay_dataset_v21/traj.jsonl' | Measure-Object -Line).Lines
Write-Output ("rows sau curate: " + $n)
if ($n -lt 20) {
  Write-Output 'DUOI 20 row -> khong upload (du lieu khong du)'
  exit 2
}

Write-Output ("=== upload dataset gui-selfplay (version v21-rollout) $(Get-Date -Format 'HH:mm:ss') ===")
New-Item -ItemType Directory -Force -Path "$env:TEMP\.kaggle\uploads" | Out-Null
kaggle datasets version -p phase13-gui/selfplay_dataset_v21 -m "selfplay from rollout v21 $(Get-Date -Format 'HH:mm')"
$code = $LASTEXITCODE
Write-Output ("UPLOAD-EXIT " + $code)
if ($code -ne 0) { Write-Output 'upload loi - dung'; exit 3 }

Write-Output '=== wait dataset READY ==='
for ($i = 1; $i -le 60; $i++) {
  $st = (kaggle datasets status khoadangnguye/gui-selfplay 2>&1 | Out-String)
  Write-Output ("  [$i] " + ($st -replace "`r?`n", ' '))
  if ($st -match 'active|ready' -and $st -notmatch 'processing|in_progress') {
    Write-Output ("READY " + (Get-Date -Format 'HH:mm:ss'))
    exit 0
  }
  Start-Sleep -Seconds 15
}
exit 2
