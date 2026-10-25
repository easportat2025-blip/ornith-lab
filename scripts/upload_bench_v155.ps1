# upload_bench_v155.ps1 - upload dataset B15.5 (T13-T18) len Kaggle + wait READY.
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'
$stage = 'phase13-gui/bench_v155_dataset'
if (-not (Test-Path "$stage/bench_v155_bundle.zip")) {
  Write-Output 'THIEU bundle - chay make_bench_v155.py truoc'
  exit 1
}
New-Item -ItemType Directory -Force -Path "$env:TEMP\.kaggle\uploads" | Out-Null
Write-Output ("=== upload B15.5 dataset $(Get-Date -Format 'HH:mm:ss') ===")
kaggle datasets create -p phase13-gui/bench_v155_dataset
$code = $LASTEXITCODE
if ($code -ne 0) {
  kaggle datasets version -p phase13-gui/bench_v155_dataset -m "bench v155 $(Get-Date -Format 'HH:mm')"
  $code = $LASTEXITCODE
}
Write-Output ("UPLOAD-EXIT " + $code + " $(Get-Date -Format 'HH:mm:ss')")

Write-Output '=== wait dataset READY ==='
for ($i = 1; $i -le 60; $i++) {
  $st = (kaggle datasets status khoadangnguye/ornith-gui-bench-v155 2>&1 | Out-String)
  Write-Output ("  [$i] " + ($st -replace "`r?`n", ' '))
  if ($st -match 'active|ready' -and $st -notmatch 'processing|in_progress') {
    Write-Output ("READY " + (Get-Date -Format 'HH:mm:ss'))
    exit 0
  }
  Start-Sleep -Seconds 15
}
Write-Output 'WARN: chua READY sau 15p'
exit 2
