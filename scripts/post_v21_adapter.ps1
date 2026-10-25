# post_v21_adapter.ps1 - sau khi kernel SFT v21 COMPLETE: tai adapter gui_lora
# va tao dataset khoadangnguye/ornith-gui-lora-v21 (goi helper Python de dung
# cach gom zip + kiem output, tranh bug CLI bo qua thu muc / exit 0 khi loi).
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'

Write-Output ("=== tai adapter v21 $(Get-Date -Format 'HH:mm:ss') ===")
kaggle kernels output khoadangnguye/ornith-gui-sft-v21 -p phase13-gui/out_sft_v21 --file-pattern "gui_lora/.*|gui_result\.json" --force
Write-Output ("DOWNLOAD-EXIT " + $LASTEXITCODE)

if (-not (Test-Path 'phase13-gui/out_sft_v21/gui_lora/adapter_config.json')) {
  Write-Output 'THIEU adapter_config.json - dung'
  exit 1
}

Write-Output '=== upload dataset lora-v21 ==='
python scripts/upload_adapter_dataset.py khoadangnguye/ornith-gui-sft-v21 phase13-gui/out_sft_v21/gui_lora khoadangnguye/ornith-gui-lora-v21 "Ornith GUI LoRA v21 (action-only + selfplay)"
$rc = $LASTEXITCODE
Write-Output ("UPLOAD-EXIT " + $rc)
if ($rc -ne 0) { exit 1 }

Write-Output '=== wait dataset READY ==='
for ($i = 1; $i -le 60; $i++) {
  $st = (kaggle datasets status khoadangnguye/ornith-gui-lora-v21 2>&1 | Out-String)
  Write-Output ("  [$i] " + ($st -replace "`r?`n", ' '))
  if ($st -match 'active|ready' -and $st -notmatch 'processing|in_progress') {
    Write-Output ("READY " + (Get-Date -Format 'HH:mm:ss'))
    exit 0
  }
  Start-Sleep -Seconds 15
}
Write-Output 'WARN: chua READY sau 15p'
exit 2
