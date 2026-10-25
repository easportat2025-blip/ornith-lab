"""upload_selfplay.ps1 - upload dataset khoadangnguye/gui-selfplay (self-play d1) len Kaggle.

Chay SAU khi rollout_curate.py da stage phase13-gui/selfplay_dataset/.
Neu dataset da ton tai -> tao version moi (kaggle datasets version).
"""
$env:PYTHONIOENCODING = 'utf-8'
Set-Location 'C:\Users\Admin\Desktop\New folder'

$stage = 'phase13-gui/selfplay_dataset'
if (-not (Test-Path "$stage/traj.jsonl")) {
  Write-Output "THIEU $stage/traj.jsonl - chay rollout_curate.py truoc"
  exit 1
}

New-Item -ItemType Directory -Force -Path "$env:TEMP\.kaggle\uploads" | Out-Null
New-Item -ItemType Directory -Force -Path "$env:TEMP\.kaggle\uploads\phase13-gui" | Out-Null

Write-Output ("=== upload $(Get-Date -Format 'HH:mm:ss') ===")
kaggle datasets create -p $stage
$code = $LASTEXITCODE
if ($code -ne 0) {
  Write-Output "create loi (co the da ton tai) -> thu version"
  kaggle datasets version -p $stage -m "selfplay d1 update $(Get-Date -Format 'HH:mm')"
  $code = $LASTEXITCODE
}
Write-Output ("UPLOAD-EXIT " + $code + " $(Get-Date -Format 'HH:mm:ss')")

# RULE (tu fail 15:31): dataset version phai READY truoc khi push kernel
# (push cung luc -> Kaggle resolve nham version cu).
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
Write-Output 'WARN: dataset chua READY sau 15p - can check thu cong'
exit 2
