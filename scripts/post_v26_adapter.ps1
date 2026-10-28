# post_v26_adapter.ps1 - sau khi kernel SFT v26 COMPLETE (acc B):
#   1) tai adapter gui_lora/ + gui_result.json
#   2) publish dataset `dieniw/ornith-gui-lora-v26` (weights fingerprint)
#   3) register fingerprint
# Eval B17/B18 v26 da nam trong queue voi `after` = sft-v26 va
# `requires` = adapter v26, nen watchdog chi push sau khi script nay xong.
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'

Write-Output ("=== tai adapter v26 gui_lora/ $(Get-Date -Format 'HH:mm:ss') ===")
kaggle kernels output dieniw/ornith-gui-sft-v26 -p phase13-gui/out_sft_v26 --file-pattern "gui_lora/.*|gui_result\.json" --force
Write-Output ("DOWNLOAD-EXIT " + $LASTEXITCODE)

if (-not (Test-Path 'phase13-gui/out_sft_v26/gui_lora/adapter_config.json')) {
  Write-Output 'THIEU adapter_config.json - adapter khong train xong'
  exit 1
}

Write-Output '=== publish adapter v26 len acc B ==='
python scripts/publish_lora.py --src phase13-gui/out_sft_v26/gui_lora --slug dieniw/ornith-gui-lora-v26 --acc B --title "Ornith GUI LoRA v26"
Write-Output ("PUBLISH-EXIT " + $LASTEXITCODE)

Write-Output '=== register fingerprint v26 ==='
python scripts/lora_fingerprint.py --file phase13-gui/out_sft_v26/gui_lora/adapter_model.safetensors --slug dieniw/ornith-gui-lora-v26 --register --note "v26: v25b + THINK/ACTION + curated B15/B16 hard pack (28/10)"
Write-Output ("FINGERPRINT-EXIT " + $LASTEXITCODE)

Write-Output '=== xong post_v26 ==='
