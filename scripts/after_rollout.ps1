# after_rollout.ps1 - pipeline sau khi rollout-base COMPLETE:
#   curate -> upload dataset gui-selfplay -> wait READY -> push kernel SFT v21
# Tu dong: an toan (chi push khi du lieu du), nen chay khong can canh.
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'

$bundle = 'phase13-gui/out_rollout_base/rollout_bundle.zip'
if (-not (Test-Path $bundle)) {
  Write-Output 'THIEU bundle - chua tai xong'
  exit 1
}

Write-Output ("=== curate $(Get-Date -Format 'HH:mm:ss') ===")
python phase13-gui/rollout_curate.py --bundle $bundle --cap 600 --max-fail 2 --exclude-variants 2
if ($LASTEXITCODE -ne 0) { Write-Output 'curate loi'; exit 1 }

$n = (Get-Content 'phase13-gui/selfplay_dataset/traj.jsonl' | Measure-Object -Line).Lines
Write-Output ("rows sau curate: " + $n)
if ($n -lt 20) {
  Write-Output 'DUOI 20 row -> KHONG push (du lieu khong du)'
  exit 2
}

Write-Output ("=== upload dataset gui-selfplay $(Get-Date -Format 'HH:mm:ss') ===")
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\upload_selfplay.ps1
Write-Output ("UPLOAD-EXIT " + $LASTEXITCODE)
if ($LASTEXITCODE -ne 0) { Write-Output 'upload loi - dung'; exit 3 }

Write-Output ("=== push kernel SFT v21 $(Get-Date -Format 'HH:mm:ss') ===")
kaggle kernels push -p phase13-gui/kernel_v21
Write-Output ("PUSH-EXIT " + $LASTEXITCODE + " $(Get-Date -Format 'HH:mm:ss')")
