# post_v22_adapter.ps1 - sau khi kernel SFT v22 COMPLETE: tai adapter gui_lora,
# upload dataset hhjiji/ornith-gui-lora-v22, cho den khi READY.
# (KHONG push kernel gate: hang doi gpu_queue.json tu push.)
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'

Write-Output ("=== tai adapter v22 gui_lora/ $(Get-Date -Format 'HH:mm:ss') ===")
kaggle kernels output khoadangnguye/ornith-gui-sft-v22 -p phase13-gui/out_sft_v22 --file-pattern "gui_lora/.*|gui_result\.json" --force
Write-Output ("DOWNLOAD-EXIT " + $LASTEXITCODE)

if (-not (Test-Path 'phase13-gui/out_sft_v22/gui_lora/adapter_config.json')) {
  Write-Output 'THIEU adapter_config.json - kiem tra output kernel'
  exit 1
}

$stage = 'phase13-gui/lora_v22_dataset'
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item 'phase13-gui/out_sft_v22/gui_lora/*' -Destination $stage -Force -Recurse
@'
{"title": "Ornith GUI LoRA v22 (v21 + synth targeted)", "id": "khoadangnguye/ornith-gui-lora-v22", "licenses": [{"name": "other"}]}
'@ | Set-Content -Path "$stage/dataset-metadata.json" -Encoding ascii
Write-Output '=== file staged ==='
Get-ChildItem $stage | Select-Object Name, Length

Write-Output ("=== upload dataset lora-v22 $(Get-Date -Format 'HH:mm:ss') ===")
New-Item -ItemType Directory -Force -Path "$env:TEMP\.kaggle\uploads" | Out-Null
kaggle datasets create -p $stage
$code = $LASTEXITCODE
if ($code -ne 0) {
  kaggle datasets version -p $stage -m "lora v22 $(Get-Date -Format 'HH:mm')"
  $code = $LASTEXITCODE
}
Write-Output ("UPLOAD-EXIT " + $code + " $(Get-Date -Format 'HH:mm:ss')")

Write-Output '=== wait dataset READY ==='
for ($i = 1; $i -le 60; $i++) {
  $st = (kaggle datasets status khoadangnguye/ornith-gui-lora-v22 2>&1 | Out-String)
  Write-Output ("  [$i] " + ($st -replace "`r?`n", ' '))
  if ($st -match 'active|ready' -and $st -notmatch 'processing|in_progress') {
    Write-Output ("READY " + (Get-Date -Format 'HH:mm:ss'))
    exit 0
  }
  Start-Sleep -Seconds 15
}
Write-Output 'WARN: chua READY sau 15p'
exit 2
