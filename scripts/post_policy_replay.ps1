# post_policy_replay.ps1 - sau khi kernel policy-replay COMPLETE: dong goi du lieu
# (traj.jsonl + shots.zip) thanh dataset tren acc A de mix vao v22.
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'

Write-Output ("=== tai output policy-replay $(Get-Date -Format 'HH:mm:ss') ===")
kaggle kernels output khoadangnguye/ornith-policy-replay -p phase13-gui/out_policy_replay --file-pattern "traj\.jsonl|shots\.zip|replay_summary\.json" --force
Write-Output ("DOWNLOAD-EXIT " + $LASTEXITCODE)

if (-not (Test-Path 'phase13-gui/out_policy_replay/traj.jsonl')) {
  Write-Output 'THIEU traj.jsonl - dung'
  exit 1
}

$stage = 'phase13-gui/policy_replay_dataset'
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item 'phase13-gui/out_policy_replay/traj.jsonl' "$stage/traj.jsonl" -Force
if (Test-Path 'phase13-gui/out_policy_replay/shots.zip') {
  Copy-Item 'phase13-gui/out_policy_replay/shots.zip' "$stage/shots.zip" -Force
}
'{"title": "Ornith policy replay train data", "id": "khoadangnguye/ornith-policy-replay-data", "licenses": [{"name": "other"}]}' |
  Set-Content -Path "$stage/dataset-metadata.json" -Encoding ascii

Write-Output '=== upload dataset ==='
kaggle datasets create -p $stage
$code = $LASTEXITCODE
if ($code -ne 0) {
  kaggle datasets version -p $stage -m "policy replay $(Get-Date -Format 'HH:mm')"
  $code = $LASTEXITCODE
}
Write-Output ("UPLOAD-EXIT " + $code)
if ($code -ne 0) { exit 1 }

Write-Output '=== wait READY ==='
for ($i = 1; $i -le 60; $i++) {
  $st = (kaggle datasets status khoadangnguye/ornith-policy-replay-data 2>&1 | Out-String)
  Write-Output ("  [$i] " + ($st -replace "`r?`n", ' '))
  if ($st -match 'active|ready' -and $st -notmatch 'processing|in_progress') {
    Write-Output ("READY " + (Get-Date -Format 'HH:mm:ss'))
    exit 0
  }
  Start-Sleep -Seconds 15
}
exit 2
