# post_v25b_adapter.ps1 - sau khi kernel SFT v25b COMPLETE (acc B):
#   1) tai adapter gui_lora/ + gui_result.json
#   2) publish dataset `dieniw/ornith-gui-lora-v25b` (weights fingerprint)
#   3) register fingerprint
# Cac kernel gate B15/B15.5/B16/B17 da nam trong queue B voi `after` =
# sft-v25b, nen watchdog se tu push sau khi script nay xong.
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'

Write-Output ("=== tai adapter v25b gui_lora/ $(Get-Date -Format 'HH:mm:ss') ===")
kaggle kernels output dieniw/ornith-gui-sft-v25b -p phase13-gui/out_sft_v25b --file-pattern "gui_lora/.*|gui_result\.json" --force
Write-Output ("DOWNLOAD-EXIT " + $LASTEXITCODE)

if (-not (Test-Path 'phase13-gui/out_sft_v25b/gui_lora/adapter_config.json')) {
  Write-Output 'THIEU adapter_config.json - adapter khong train xong'
  exit 1
}

Write-Output '=== publish adapter v25b len acc B ==='
python scripts/publish_lora.py --src phase13-gui/out_sft_v25b/gui_lora --slug dieniw/ornith-gui-lora-v25b --acc B --title "Ornith GUI LoRA v25b"
Write-Output ("PUBLISH-EXIT " + $LASTEXITCODE)

Write-Output '=== register fingerprint v25b ==='
python scripts/lora_fingerprint.py --file phase13-gui/out_sft_v25b/gui_lora/adapter_model.safetensors --slug dieniw/ornith-gui-lora-v25b --register --note "v25b: v24 + desktop-replay + S11 (SCROLL/MOVE/DRAG) (24/10)"
Write-Output ("FINGERPRINT-EXIT " + $LASTEXITCODE)

Write-Output '=== xong post_v25b ==='
