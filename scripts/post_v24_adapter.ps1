# post_v24_adapter.ps1 - sau khi kernel SFT v24 COMPLETE (acc B):
#   1) tai adapter gui_lora/ + gui_result.json
#   2) stage + upload dataset `dieniw/ornith-gui-lora-v24` (cho acc B)
#   3) tao 3 kernel gate B15 / B15.5 / B16 (da san trong scripts/) va dua vao queue B
# KHONG push kernel gate (watchdog lo).
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'

Write-Output ("=== tai adapter v24 gui_lora/ $(Get-Date -Format 'HH:mm:ss') ===")
kaggle kernels output dieniw/ornith-gui-sft-v24 -p phase13-gui/out_sft_v24 --file-pattern "gui_lora/.*|gui_result\.json" --force
Write-Output ("DOWNLOAD-EXIT " + $LASTEXITCODE)

if (-not (Test-Path 'phase13-gui/out_sft_v24/gui_lora/adapter_config.json')) {
  Write-Output 'THIEU adapter_config.json - adapter khong train xong'
  exit 1
}

# 2) stage dataset adapter
$stage = 'phase13-gui/lora_v24_dataset'
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Get-ChildItem 'phase13-gui/out_sft_v24/gui_lora/*' | Copy-Item -Destination $stage -Force -Recurse
@'
{"title": "Ornith GUI LoRA v24 (dr0.75 + R2 + looprec)", "id": "dieniw/ornith-gui-lora-v24", "licenses": [{"name": "other"}]}
'@ | Set-Content -Path "$stage/dataset-metadata.json" -Encoding ascii

Write-Output '=== upload adapter v24 len acc B ==='
kaggle datasets create -p $stage
Write-Output ("CREATE-EXIT " + $LASTEXITCODE)
kaggle datasets version -p $stage -m "v24 adapter" 2>&1 | Select-Object -Last 2

# 2b) upload SAME adapter cho acc A (de chay tiep gate khi quota A reset 24/10)
$reg = Get-ItemProperty 'HKCU:\Environment'
if ($reg.KAGGLE_KEY_A) {
  Write-Output '=== upload adapter v24 len acc A (cho gate sau 24/10) ==='
  $env:KAGGLE_USERNAME = 'khoadangnguye'
  $env:KAGGLE_KEY = $reg.KAGGLE_KEY_A
  @'
{"title": "Ornith GUI LoRA v24 (dr0.75 + R2 + looprec)", "id": "khoadangnguye/ornith-gui-lora-v24", "licenses": [{"name": "other"}]}
'@ | Set-Content -Path "$stage/dataset-metadata.json" -Encoding ascii
  kaggle datasets create -p $stage
  kaggle datasets version -p $stage -m "v24 adapter" 2>&1 | Select-Object -Last 2
  $env:KAGGLE_USERNAME = 'dieniw'
  $env:KAGGLE_KEY = $reg.KAGGLE_KEY_B
}

# 3) tao kernel gate + dua vao queue B
Write-Output '=== tao 3 kernel gate cho v24 ==='
python scripts\make_v24_bench_kernels.py

Write-Output '=== xong post_v24 ==='
