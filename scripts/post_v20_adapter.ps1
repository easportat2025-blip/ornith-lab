# post_v20_adapter.ps1 - sau khi v20 COMPLETE: tai adapter gui_lora + upload dataset lora-v20.
# Chay: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\post_v20_adapter.ps1
# (Chi tai adapter + upload; JSON ket qua do poller v20 tai truoc do.)
$env:PYTHONIOENCODING = 'utf-8'
Set-Location 'C:\Users\Admin\Desktop\New folder'

Write-Output ("=== tai adapter gui_lora/ $(Get-Date -Format 'HH:mm:ss') ===")
kaggle kernels output khoadangnguye/ornith-gui-sft-v20 -p phase13-gui/out_v20 --file-pattern "gui_lora/.*" --force
Write-Output ("DOWNLOAD-EXIT " + $LASTEXITCODE)

if (-not (Test-Path 'phase13-gui/out_v20/gui_lora/adapter_config.json')) {
  Write-Output "THIEU adapter_config.json - kiem tra lai output kernel"
  exit 1
}

Write-Output ("=== upload dataset lora-v20 $(Get-Date -Format 'HH:mm:ss') ===")
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\upload_lora_v20.ps1
Write-Output ("UPLOAD-EXIT " + $LASTEXITCODE + " $(Get-Date -Format 'HH:mm:ss')")
