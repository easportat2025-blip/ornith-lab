# upload_dataset.ps1 - upload mot dataset staging len Kaggle + wait READY.
# Usage: powershell -File scripts\upload_dataset.ps1 -Stage phase14-blender/train3d_dataset -Id hhjiji/ornith-gui-train3d
param(
  [Parameter(Mandatory = $true)][string]$Stage,
  [Parameter(Mandatory = $true)][string]$Id
)
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'

if (-not (Test-Path "$Stage/dataset-metadata.json")) {
  Write-Output "THIEU $Stage/dataset-metadata.json"
  exit 1
}
New-Item -ItemType Directory -Force -Path "$env:TEMP\.kaggle\uploads" | Out-Null
# CLI tao sidecar .json trong temp theo component DAU cua stage path
$first = ($Stage -split '[\\/]')[0]
if ($first) {
  New-Item -ItemType Directory -Force -Path "$env:TEMP\.kaggle\uploads\$first" | Out-Null
}
Write-Output ("=== upload $Id $(Get-Date -Format 'HH:mm:ss') ===")
kaggle datasets create -p $Stage
$code = $LASTEXITCODE
if ($code -ne 0) {
  kaggle datasets version -p $Stage -m "update $(Get-Date -Format 'HH:mm')"
  $code = $LASTEXITCODE
}
Write-Output ("UPLOAD-EXIT " + $code + " $(Get-Date -Format 'HH:mm:ss')")
if ($code -ne 0) { exit 1 }

Write-Output '=== wait dataset READY ==='
for ($i = 1; $i -le 60; $i++) {
  $st = (kaggle datasets status $Id 2>&1 | Out-String)
  Write-Output ("  [$i] " + ($st -replace "`r?`n", ' '))
  if ($st -match 'active|ready' -and $st -notmatch 'processing|in_progress') {
    Write-Output ("READY " + (Get-Date -Format 'HH:mm:ss'))
    exit 0
  }
  Start-Sleep -Seconds 15
}
Write-Output 'WARN: chua READY sau 15p'
exit 2
